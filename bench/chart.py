import csv
from collections import defaultdict

import matplotlib.pyplot as plt

rows = list(csv.DictReader(open("bench/results.csv", encoding="utf-8")))
tests = list(dict.fromkeys(r["test"] for r in rows))
by_test = defaultdict(list)
for r in rows:
    by_test[r["test"]].append(r)

colors = {"mongo": "#3f8f4f", "pg": "#33658a", "pg 3 queries": "#33658a", "pg json_agg": "#86bbd8"}
fig, axes = plt.subplots(2, 3, figsize=(13, 7))
for ax, test in zip(axes.flat, tests):
    items = by_test[test]
    names = [i["engine"] for i in items]
    med = [float(i["median_ms"]) for i in items]
    p95 = [float(i["p95_ms"]) for i in items]
    x = range(len(items))
    ax.bar(x, med, color=[colors[n] for n in names], width=0.6)
    ax.scatter(x, p95, color="#222", marker="_", s=400, zorder=3, label="p95")
    for xi, v in zip(x, med):
        ax.text(xi, v, f"{v:.2f}", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(list(x), names, fontsize=9)
    ax.set_title(test, fontsize=11)
    ax.set_ylabel("ms (median)")
    ax.set_ylim(0, max(p95) * 1.2)
    ax.spines[["top", "right"]].set_visible(False)
axes.flat[0].legend(frameon=False, fontsize=8)
fig.suptitle("MongoDB vs PostgreSQL, 20 000 сторінок курсів", fontsize=13)
fig.tight_layout()
fig.savefig("скріни/06_бенчмарк_графік.png", dpi=120)
