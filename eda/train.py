"""Summarize default/train metadata and its overlap with default/test; see README.md.

Reads only a few columns of the 11 train shards over HTTP (about 12 MB instead of 2.7 GB).
"""

import argparse
import collections
import json
import re

import pyarrow.parquet as pq
from analyze import PILOT_TAGS, band

REVISION = "fbe3f6e903ee854eec2e69e9d96d0306cde59baf"
SHARDS = 11
COLUMNS = [
    "id",
    "aliases",
    "contest_id",
    "contest_start_year",
    "title",
    "description",
    "tags",
    "rating",
]


def fetch_train():
    import fsspec

    fs = fsspec.filesystem("http")
    rows = []
    for i in range(SHARDS):
        url = (
            "https://huggingface.co/datasets/open-r1/codeforces/resolve/"
            f"{REVISION}/data/train-{i:05d}-of-{SHARDS:05d}.parquet"
        )
        with fs.open(url, "rb", block_size=2**20) as source:
            rows += pq.read_table(source, columns=COLUMNS).to_pylist()
    return rows


def normalize(text):
    return " ".join((text or "").lower().split())


def shingles(text, size=5):
    words = re.findall(r"\w+", text.lower())
    return {tuple(words[i : i + size]) for i in range(max(len(words) - size + 1, 1))}


def summarize(train, test):
    """Counts only, so the output is deterministic. `test` rows need the same columns."""
    rated = [r for r in train if r["rating"]]
    tag_counts = collections.Counter(t for r in train for t in set(r["tags"] or []))
    train_ids = {r["id"] for r in train}
    train_names = train_ids | {a for r in train for a in r["aliases"] or []}
    train_contests = {r["contest_id"] for r in train}
    train_titles = {normalize(r["title"]) for r in train}
    train_texts = {normalize(r["description"]) for r in train if r["description"]}

    index = collections.defaultdict(list)
    train_shingles = []
    for k, r in enumerate(train):
        train_shingles.append(shingles(r["description"] or ""))
        for sh in train_shingles[-1]:
            index[sh].append(k)
    similarity = []
    for r in test:
        mine = shingles(r["description"] or "")
        hits = collections.Counter(k for sh in mine for k in index.get(sh, ()))
        similarity.append(
            max((c / len(mine | train_shingles[k]) for k, c in hits.items()), default=0)
        )

    return {
        "rows": len(train),
        "rated": len(rated),
        "with_tags": sum(bool(r["tags"]) for r in train),
        "duplicate_id_rows": len(train) - len(train_ids),
        "tags": dict(tag_counts.most_common()),
        "years": dict(
            sorted(collections.Counter(str(r["contest_start_year"]) for r in train).items())
        ),
        "topic_rating_bands": {
            tag: dict(
                collections.Counter(band(r["rating"]) for r in rated if tag in (r["tags"] or []))
            )
            for tag in PILOT_TAGS
        },
        "overlap_with_test": {
            "test_rows": len(test),
            "same_id": sum(r["id"] in train_ids for r in test),
            "same_id_or_alias": sum(
                bool({r["id"], *(r["aliases"] or [])} & train_names) for r in test
            ),
            "same_contest": sum(r["contest_id"] in train_contests for r in test),
            "same_title": sum(normalize(r["title"]) in train_titles for r in test),
            "same_statement": sum(normalize(r["description"]) in train_texts for r in test),
            "statement_similarity_ge_0_5": sum(s >= 0.5 for s in similarity),
            "statement_similarity_max": round(max(similarity, default=0), 2),
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("test_parquet")
    args = parser.parse_args()
    test_rows = pq.read_table(args.test_parquet, columns=COLUMNS).to_pylist()
    print(json.dumps(summarize(fetch_train(), test_rows), ensure_ascii=False, indent=2))
