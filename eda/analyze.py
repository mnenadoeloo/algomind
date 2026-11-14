"""Summarize the pinned Codeforces test split; see README.md for reproduction."""

import argparse
import collections
import hashlib
import json
from pathlib import Path

import pyarrow.parquet as pq


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
