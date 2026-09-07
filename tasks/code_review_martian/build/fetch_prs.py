"""抓取那 50 个 PR 的 diff —— 内联 question 的原料。

**为什么优先用 fork 里的那个 URL。** 黄金意见里 37 条只有 `url`(就是上游 PR),
13 条另有 `original_url`(此时 `url` 指向 `ai-code-review-evaluation` 组织下的 fork)。
Martian 之所以 fork,是为了**冻结被审阅的那个 commit** —— 上游 PR 会继续被 push、
被 squash、被删。所以 `url` 永远是权威来源,`original_url` 只用于出处标注。

黄金意见里还带着 5 条质量注记(`az_comment`),照原样传下去,不做判断:
  · 4 条「reviewed commit is not in the repo」
  · 1 条「there is no such PR, it is a mix of many PRs」—— 这一条**不是真实 PR**
两者都可能让某个 case 不适合入题,但那是渲染阶段的决定,不是抓取阶段的。

抓到的东西写进 `_cache/`(不入库,可重建)。尺寸分布是副产品 —— 它决定
questions.yaml 能装几题,因为 traplite 的编排 agent 要把整个 yaml 读进上下文。
"""
from __future__ import annotations

import json
import pathlib
import statistics
import sys
import time
import urllib.error
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
CACHE = HERE.parent / "_cache"
GOLD = (pathlib.Path.home() / "Documents/Projects/trapstreet-tasks-private"
        / "tasks/code_review_martian/golden_comments")


def cases() -> list[dict]:
    out = []
    for f in sorted(GOLD.glob("*.json")):
        for pr in json.load(f.open()):
            url = pr["url"]                      # 冻结态优先
            owner, repo, _, num = url.removeprefix("https://github.com/").split("/")
            out.append({"group": f.stem, "owner": owner, "repo": repo, "number": int(num),
                        "url": url, "upstream_url": pr.get("original_url") or url,
                        "title": pr.get("pr_title"), "note": pr.get("az_comment"),
                        "n_golden": len(pr.get("comments") or [])})
    return out


def fetch(c: dict) -> tuple[str | None, str | None]:
    """-> (diff, error)。不认证 —— GitHub 的 .diff 端点公开可读,但有速率限制。"""
    req = urllib.request.Request(
        f"https://github.com/{c['owner']}/{c['repo']}/pull/{c['number']}.diff",
        headers={"User-Agent": "trapstreet-task-build"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read().decode("utf-8", "replace"), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except Exception as e:                                     # noqa: BLE001
        return None, f"{e.__class__.__name__}: {e}"


def main() -> int:
    CACHE.mkdir(exist_ok=True)
    rows, sizes = [], []
    for i, c in enumerate(cases(), 1):
        key = f"{c['group']}_{c['number']}"
        path = CACHE / f"{key}.diff"
        if path.exists():
            diff, err = path.read_text(), None
        else:
            diff, err = fetch(c)
            if diff is not None:
                path.write_text(diff)
            time.sleep(1.0)                     # 对未认证端点客气一点
        n = len(diff) if diff else 0
        if diff:
            sizes.append(n)
        rows.append({**c, "bytes": n, "error": err,
                     "files": diff.count("\ndiff --git ") + (1 if diff.startswith("diff --git ") else 0)
                              if diff else 0})
        flag = f"  ⚠ {c['note']}" if c.get("note") else ""
        print(f"  {i:2}/{len(cases())} {key:26} {n:>9,}B  {rows[-1]['files']:>3} 文件"
              f"{'  ✗ ' + err if err else ''}{flag}", flush=True)
    (CACHE / "manifest.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False) + "\n")
    ok = [r for r in rows if r["bytes"]]
    print(f"\n抓到 {len(ok)}/{len(rows)}   失败 {len(rows)-len(ok)}")
    if sizes:
        sizes.sort()
        print(f"diff 尺寸: 中位 {statistics.median(sizes):,.0f}B  "
              f"p75 {sizes[int(len(sizes)*.75)]:,}B  最大 {max(sizes):,}B  "
              f"总计 {sum(sizes):,}B")
        for cap in (50_000, 100_000, 200_000):
            fit = [s for s in sizes if s <= cap]
            print(f"  单题上限 {cap:>7,}B -> 可入题 {len(fit):2} 个, 合计 {sum(fit):,}B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
