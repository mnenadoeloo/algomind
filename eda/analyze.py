"""Summarize the pinned Codeforces test split; see README.md for reproduction."""

import argparse
import collections
import hashlib
import itertools
import json
import statistics
from pathlib import Path

import pyarrow.parquet as pq


def box(values):
    """Quartiles plus 10th/90th percentiles (whiskers) for a boxplot."""
    deciles = statistics.quantiles(values, n=10, method="inclusive")
    q1, med, q3 = statistics.quantiles(values, n=4, method="inclusive")
    return {
        "n": len(values),
        "min": min(values),
        "p10": deciles[0],
        "q1": q1,
        "median": med,
        "q3": q3,
        "p90": deciles[8],
        "max": max(values),
    }


def analyze(path):
    parquet = pq.ParquetFile(path)
    fields = parquet.schema_arrow.names
    rows = [
        row
        for batch in parquet.iter_batches(
            batch_size=32,
            columns=[
                "id",
                "aliases",
                "contest_start_year",
                "description",
                "rating",
                "tags",
                "input_mode",
                "official_tests_complete",
                "executable",
            ],
        )
        for row in batch.to_pylist()
    ]
    assert len(rows) == 468 and len(fields) == 27
    missing = {
        key: sum(
            row[key] is None or row[key] == "" or row[key] == []
            for batch in parquet.iter_batches(batch_size=32, columns=[key])
            for row in batch.to_pylist()
        )
        for key in fields
    }
    ids = collections.Counter(row["id"] for row in rows)
    descriptions = collections.Counter(
        " ".join((row["description"] or "").split()) for row in rows if row["description"]
    )
    ratings = collections.Counter(
        str(row["rating"]) if row["rating"] is not None else "нет" for row in rows
    )
    tags = collections.Counter(tag for row in rows for tag in set(row["tags"] or []))
    top_tags = [tag for tag, _ in tags.most_common(10)]
    lengths = [len(row["description"]) for row in rows if row["description"]]
    pairs = collections.Counter(
        pair
        for row in rows
        for pair in itertools.combinations(sorted(set(row["tags"] or []) & set(top_tags)), 2)
    )
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return {
        "sha256": digest.hexdigest(),
        "rows": len(rows),
        "fields": fields,
        "missing": missing,
        "duplicate_id_rows": sum(count - 1 for count in ids.values()),
        "duplicate_normalized_description_rows": sum(count - 1 for count in descriptions.values()),
        "ratings": dict(
            sorted(ratings.items(), key=lambda item: int(item[0]) if item[0] != "нет" else 9999)
        ),
        "tags": dict(tags.most_common()),
        "tags_per_task": dict(
            sorted(collections.Counter(len(row["tags"] or []) for row in rows).items())
        ),
        "rating_by_top_tag": {
            tag: box([r["rating"] for r in rows if r["rating"] and tag in (r["tags"] or [])])
            for tag in top_tags[:5]
        },
        "top_tags_cooccurrence": {
            "tags": top_tags,
            "pairs": {f"{a} | {b}": n for (a, b), n in sorted(pairs.items())},
        },
        "description_length": {
            **box(lengths),
            "bins_1000": dict(
                sorted(collections.Counter(min(n // 1000, 3) for n in lengths).items())
            ),
        },
        "input_mode": dict(collections.Counter(str(row["input_mode"]) for row in rows)),
        "official_tests_complete": dict(
            collections.Counter(str(row["official_tests_complete"]) for row in rows)
        ),
        "executable": dict(collections.Counter(str(row["executable"]) for row in rows)),
        "years": dict(
            sorted(collections.Counter(str(row["contest_start_year"]) for row in rows).items())
        ),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("parquet")
    args = parser.parse_args()
    print(json.dumps(analyze(args.parquet), ensure_ascii=False, indent=2))
