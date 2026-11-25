import analyze
import pyarrow as pa
import pyarrow.parquet as pq
import train

N = 468
LIST_FIELDS = {"aliases", "tags", "examples"}
INT_FIELDS = {"contest_id", "contest_start_year", "rating", "testset_size"}
BOOL_FIELDS = {"official_tests_complete", "executable", "generated_checker"}


def make_parquet(tmp_path):
    """Synthetic file with the real schema size: 468 rows, 27 fields."""
    names = [
        "id", "aliases", "contest_id", "contest_name", "contest_type", "contest_start",
        "contest_start_year", "index", "time_limit", "memory_limit", "title", "description",
        "input_format", "output_format", "interaction_format", "note", "examples", "editorial",
        "rating", "tags", "testset_size", "official_tests", "official_tests_complete",
        "input_mode", "generated_checker", "executable", "generated_tests",
    ]  # fmt: skip
    cols = {}
    for name in names:
        if name in LIST_FIELDS:
            cols[name] = pa.array([[] for _ in range(N)], pa.list_(pa.string()))
        elif name in INT_FIELDS:
            cols[name] = pa.array([800] * N, pa.int64())
        elif name in BOOL_FIELDS:
            cols[name] = pa.array([False] * N)
        else:
            cols[name] = pa.array(["x"] * N)
    cols["id"] = pa.array([f"t{i}" for i in range(N)])
    cols["description"] = pa.array([f"d{i}" * 10 for i in range(N)])
    cols["rating"] = pa.array([None, *[1000] * (N - 1)], pa.int64())
    cols["tags"] = pa.array(
        [["dp"], *[["dp", "math"]] * 2, *[["dp"]] * (N - 3)], pa.list_(pa.string())
    )
    cols["official_tests_complete"] = pa.array([True] + [False] * (N - 1))
    path = tmp_path / "cf.parquet"
    pq.write_table(pa.table(cols), path)
    return path


def test_box_quartiles():
    b = analyze.box([1, 2, 3, 4, 5])
    assert (b["min"], b["q1"], b["median"], b["q3"], b["max"], b["n"]) == (1, 2, 3, 4, 5, 5)
    assert b["p10"] == 1.4
    assert b["p90"] == 4.6


def test_analyze_counts(tmp_path):
    r = analyze.analyze(make_parquet(tmp_path))
    assert r["rows"] == N
    assert r["missing"]["rating"] == 1
    assert r["missing"]["aliases"] == N
    assert r["duplicate_id_rows"] == 0
    assert r["tags"] == {"dp": N, "math": 2}
    assert r["tags_per_task"] == {1: N - 2, 2: 2}
    assert r["topic_rating_bands"]["dp"] == {"<1200": N - 1}
    assert r["official_tests_complete"] == {"True": 1, "False": N - 1}
    assert sum(r["description_length"]["bins_1000"].values()) == N


def row(id_, contest, title, text, rating=1000, tags=("dp",), aliases=()):
    return {
        "id": id_, "contest_id": contest, "title": title, "description": text,
        "rating": rating, "tags": list(tags), "aliases": list(aliases),
        "contest_start_year": 2024,
    }  # fmt: skip


def test_train_overlap():
    text = "find the minimum number of moves needed to sort the array of n integers"
    trn = [row("1/A", 1, "Sort", text), row("2/B", 2, "Other", "a graph with n nodes " * 5)]
    tst = [
        row("9/A", 9, "Sort", text),
        row("2/B", 2, "New", "something else entirely different statement here " * 3),
    ]
    o = train.summarize(trn, tst)["overlap_with_test"]
    assert (o["same_id"], o["same_contest"], o["same_title"], o["same_statement"]) == (1, 1, 1, 1)
    assert o["statement_similarity_ge_0_5"] == 1
