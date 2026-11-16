"""Draw EDA figures from results.json (no dataset needed); see README.md."""

# ruff: noqa: RUF001

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
BLUE, GRAY = "#4c72b0", "#c44e52"


def save(fig, out, name):
    for ax in fig.axes:
        ax.margins(x=0.1, y=0.12)
    fig.tight_layout()
    fig.savefig(out / name, dpi=120)
    plt.close(fig)


def main(out):
    r = json.loads((HERE / "results.json").read_text())
    n = r["rows"]
    out.mkdir(parents=True, exist_ok=True)


    bins = {}
    for key, count in r["ratings"].items():
        label = "нет" if key == "нет" else f"{int(key) // 400 * 400}-{int(key) // 400 * 400 + 399}"
        bins[label] = bins.get(label, 0) + count
    fig, ax = plt.subplots(figsize=(8, 4))
    colors = [GRAY if k == "нет" else BLUE for k in bins]
    bars = ax.bar(list(bins), list(bins.values()), color=colors)
    ax.bar_label(bars)
    ax.set(title=f"Рейтинг задач (n={n})", xlabel="Рейтинг Codeforces", ylabel="Задач")
    ax.tick_params(axis="x", rotation=30)
    save(fig, out, "rating.png")


    tags = list(r["tags"].items())[:15][::-1]
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.barh([t for t, _ in tags], [c for _, c in tags], color=BLUE)
    ax.bar_label(bars)
    ax.set(
        title=f"Топ-15 тегов из {len(r['tags'])} (n={n}, теги пересекаются)",
        xlabel="Задач с тегом",
    )
    save(fig, out, "tags.png")


    miss = sorted(((k, v) for k, v in r["missing"].items() if v), key=lambda kv: kv[1])
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.barh([k for k, _ in miss], [v * 100 / n for _, v in miss], color=BLUE)
    ax.bar_label(bars, labels=[str(v) for _, v in miss])
    ax.set(
        title=f"Пропуски по полям (n={n}, подписи — число задач)",
        xlabel="% строк с пропуском",
    )
    save(fig, out, "missing.png")


    fig, axes = plt.subplots(1, 2, figsize=(9, 4))
    complete, execu = r["official_tests_complete"], r["executable"]
    groups = {
        "официальные тесты\nполные": complete["True"],
        "executable": execu["True"],
    }
    bars = axes[0].bar(list(groups), list(groups.values()), color=BLUE)
    axes[0].bar_label(bars)
    axes[0].set(title=f"Качество тестов (из {n})", ylabel="Задач")
    bars = axes[1].bar(list(r["years"]), list(r["years"].values()), color=BLUE)
    axes[1].bar_label(bars)
    axes[1].set(title="Год контеста", ylabel="Задач")
    save(fig, out, "tests_years.png")


    per = r["tags_per_task"]
    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar(list(per), list(per.values()), color=BLUE)
    ax.bar_label(bars)
    ax.set(title=f"Число тегов на задачу (n={n})", xlabel="Тегов у задачи", ylabel="Задач")
    save(fig, out, "tags_per_task.png")


    stats = [
        {
            "label": f"{tag}\n(n={b['n']})",
            "whislo": b["p10"],
            "q1": b["q1"],
            "med": b["median"],
            "q3": b["q3"],
            "whishi": b["p90"],
            "fliers": [],
        }
        for tag, b in r["rating_by_top_tag"].items()
    ]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bxp(stats, patch_artist=True, boxprops={"facecolor": BLUE, "alpha": 0.6})
    ax.set(
        title="Рейтинг по топ-5 тегам (квартили, усы — 10-й и 90-й процентили)", ylabel="Рейтинг"
    )
    save(fig, out, "rating_by_tag.png")


    co = r["top_tags_cooccurrence"]
    names = co["tags"]
    matrix = [[0] * len(names) for _ in names]
    for key, count in co["pairs"].items():
        a, b = key.split(" | ")
        i, j = names.index(a), names.index(b)

        matrix[i][j] = matrix[j][i] = count / (r["tags"][a] + r["tags"][b] - count)
    fig, ax = plt.subplots(figsize=(8, 7))
    ax.imshow(matrix, cmap="Blues")
    ax.set_xticks(range(len(names)), names, rotation=45, ha="right")
    ax.set_yticks(range(len(names)), names)
    for i, row in enumerate(matrix):
        for j, value in enumerate(row):
            if i != j:
                ax.text(j, i, f"{value:.2f}", ha="center", va="center", fontsize=8)
    ax.set_title("Пересечение топ-10 тегов (коэффициент Жаккара)")
    save(fig, out, "tags_cooccurrence.png")


    d = r["description_length"]
    labels = [f"{k}–{k + 1}k" for k in range(3)] + ["3k+"]
    values = [d["bins_1000"].get(str(k), 0) for k in range(4)]
    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar(labels, values, color=BLUE)
    ax.bar_label(bars)
    ax.set(
        title=f"Длина условия (n={d['n']}, медиана {d['median']:.0f} символов)",
        xlabel="Символов в description",
        ylabel="Задач",
    )
    save(fig, out, "description_length.png")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "figures")
