"""_cache/ 里的 diff + 案例清单 -> questions.yaml(traplite 的 {{QUESTIONS_YAML_URL}} 指它)。

**question 必须自包含。** traplite 的模板只做两件事:取回 questions.yaml,然后把
每个 case 的 `question` 文本**原样**交给一个 subagent —— 没有任何一步让 agent 去取
别的文件(2026-09-07 逐行核对过模板;当天有人试过把材料放进那个仓库,七分钟后回滚了)。
所以 diff 只能内联。

**这套集里没有干净的 PR** —— 49 个 PR 每个至少 1 条黄金意见(分布 1–9,中位 3)。
所以题面不是「有没有缺陷」,是「把问题都列出来」:精确率来自**匹配不上黄金意见的
发现**,不是来自干净 PR。题面**不透露**条数,也不说「至少有一个」—— 那是真实评审者
拿不到的信息。

**选题参数化,不预先决定。** 编排 agent 一次能吃下多大的 yaml,第一次跑就知道;
在那之前 `--cases all` 是默认。要缩量时**分层**(跨项目、跨尺寸档),
**绝不能取最小的那些** —— 小 diff 系统性更容易,那是给自己注水。
"""
from __future__ import annotations

import argparse
import json
import pathlib
import statistics

import yaml

HERE = pathlib.Path(__file__).resolve().parent
TASK = HERE.parent
CACHE = TASK / "_cache"
GOLD = (pathlib.Path.home() / "Documents/Projects/trapstreet-tasks-private"
        / "tasks/code_review_martian/golden_comments")

# 上游各自的许可。逐 case 复述,连同 NOTICE 一起构成再分发的条件。
LICENCE = {
    "keycloak": "Apache-2.0",
    "grafana": "AGPL-3.0",
    "cal_dot_com": "AGPL-3.0 (the `ee/` enterprise tree is separately licensed)",
    "discourse": "GPL-2.0",
    "sentry": "FSL-1.1-Apache-2.0 (redistribution permitted with these terms; "
              "converts to Apache-2.0 two years after release)",
}

CONTRACT = """
## Your task

Review the change above and report every issue it introduces — a bug, a security
or concurrency hazard, a data or API problem, a performance regression, a gap in
tests, or a defect in the documentation it touches.

Reply with ONLY a JSON object, nothing else:

```json
{"findings": [
  {"file": "path/to/file.py", "line": 42,
   "description": "what is wrong, and under what conditions it goes wrong",
   "severity": "Low" | "Medium" | "High" | "Critical"}
]}
```

Write the `description` so it stands on its own: it is compared against a
reviewer's own wording of the same issue, and different phrasing is fine as long
as it is the same underlying problem. `file` and `line` are recorded but do not
affect scoring.

Reporting something that is not a real issue costs you as much as missing one.
"""


def load() -> list[dict]:
    """把抓到的 diff 和(剔除后的)案例清单对起来。清单是权威 —— 私有 gold 里剔掉的
    案例不会出现在这里,因为它按 gold 目录里现有的 PR 来。"""
    urls = {pr["url"] for f in GOLD.glob("*.json") for pr in json.loads(f.read_text())}
    rows = [r for r in json.loads((CACHE / "manifest.json").read_text())
            if r["url"] in urls and r["bytes"]]
    for r in rows:
        r["diff"] = (CACHE / f"{r['group']}_{r['number']}.diff").read_text()
    return rows


def question(r: dict) -> str:
    return (
        f"You are reviewing an open pull request against `{r['owner']}/{r['repo']}`.\n\n"
        f"## {r['title'] or '(no title)'}\n\n"
        f"## The change\n\n```diff\n{r['diff'].rstrip()}\n```\n"
        f"{CONTRACT}\n"
        f"## Source\n\n"
        f"Original pull request: {r['upstream_url']}\n"
        f"`{r['owner']}/{r['repo']}` is licensed {LICENCE.get(r['group'], 'see NOTICE')}; "
        f"the diff above is reproduced under that licence with its copyright notices intact.\n"
        f"Case selection and the reviewer comments it is scored against come from "
        f"Martian Code Review Bench (MIT) — see this task's NOTICE.\n")


def pick(rows: list[dict], n: int | None) -> list[dict]:
    """分层取 n 个:每个项目按 diff 尺寸排序后**等分位取**,不是取小的。

    两端交替取会得到「小、大、小」,抽样中位数明显低于全集(实测 9.1KB vs 22.4KB)。
    小 diff 系统性更容易,所以偏小就是给自己注水。等分位取让抽样的尺寸分布跟着
    全集走。
    """
    if n is None or n >= len(rows):
        return sorted(rows, key=lambda r: (r["group"], r["number"]))
    by_group: dict[str, list[dict]] = {}
    for r in rows:
        by_group.setdefault(r["group"], []).append(r)
    for g in by_group:
        by_group[g].sort(key=lambda r: r["bytes"])
    groups = sorted(by_group)
    # 名额按组的大小分,余数轮流给
    quota = {g: n * len(by_group[g]) // len(rows) for g in groups}
    for i in range(n - sum(quota.values())):
        quota[groups[i % len(groups)]] += 1
    out = []
    for g in groups:
        b, k = by_group[g], quota[g]
        if not k:
            continue
        # 等分位:第 i 个取排序后 (i+0.5)/k 处 —— 覆盖小/中/大,不堆在任何一端
        for i in range(k):
            out.append(b[min(len(b) - 1, int((i + 0.5) * len(b) / k))])
    return sorted(out, key=lambda r: (r["group"], r["number"]))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default="all", help="'all' 或一个数字")
    ap.add_argument("--out", default=str(TASK / "questions.yaml"))
    a = ap.parse_args()
    rows = load()
    n = None if a.cases == "all" else int(a.cases)
    chosen = pick(rows, n)
    doc = {"name": "code_review_martian",
           "cases": [{"id": f"{r['group']}_{r['number']}", "question": question(r)}
                     for r in chosen]}
    text = yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=100000)
    pathlib.Path(a.out).write_text(text)
    back = yaml.safe_load(text)
    assert [c["question"] for c in back["cases"]] == [c["question"] for c in doc["cases"]], \
        "YAML 往返不一致 —— diff 里有东西被转义吃掉了"
    sizes = [len(c["question"]) for c in doc["cases"]]
    print(f"{len(chosen)}/{len(rows)} 题 -> {a.out}")
    print(f"  yaml {len(text):,}B   单题 中位 {statistics.median(sizes):,.0f}B  "
          f"最大 {max(sizes):,}B")
    import collections
    print("  分布:", dict(collections.Counter(r["group"] for r in chosen)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
