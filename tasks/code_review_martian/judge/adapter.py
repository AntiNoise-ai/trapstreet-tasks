"""traplite 报告 ↔ Martian 判分管线。**这是本目录里唯一属于我们的代码。**

`extract.py` / `dedup.py` / `match.py` / `score_profiles.py` 是 Martian 的,逐字未改
(见 ../NOTICE)。改动它们会让我们的数和他们发布的成绩失去参照,而那是引入这套东西
的理由本身。

两端的形状:

  traplite            {case_id, answer, exit_code, duration, cost}
  Martian 判分管线    {pr_url: {tool: [{text, path, line, source}, ...]}}

**为什么跳过他们的 step2(extract)。** 那一步是把工具贴在 GitHub 上的散文评审拆成
一条条候选 —— 因为他们的被测对象是装在仓库上的 bot,输出是散文。我们的契约直接要求
结构化 JSON,没有散文可拆。跳过它少一次 LLM 调用,而且不改变语义:step2 的产物就是
我们直接拿到的东西。候选的 `source` 因此记 `"structured"` 而不是 `"extracted"`。

**dedup 保留。** 提交者仍可能把同一个问题列两遍,而「同一问题的重复不算假阳性」是
他们判分语义的一部分,不是散文特有的。

**判官只看 `text`。** `get_candidates()` 返回 `[c["text"] for c in ...]` ——
`path` / `line` 记录下来但不参与判分,所以这套离线集**不计定位**
(Qodo 的那套计;两者不是同一个指标,别混着引用)。
"""
from __future__ import annotations

import json
import re

SEVERITIES = ("Low", "Medium", "High", "Critical")


def parse_answer(answer: str) -> tuple[list[dict] | None, str | None]:
    """一个 case 的答案字符串 -> (findings, 错误说明)。

    宽进:允许围栏、允许前后有散文。但**不做语义抢救** —— 解析不出来就是格式失败,
    按 0 分记进那一个 case,不是把整份提交判掉。
    """
    if not isinstance(answer, str) or not answer.strip():
        return None, "empty answer"
    t = answer.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\n", "", t)
        t = re.sub(r"\n```\s*$", "", t)
    obj = None
    try:
        obj = json.loads(t)
    except Exception:                                          # noqa: BLE001
        i, j = t.find("{"), t.rfind("}")
        if i >= 0 and j > i:
            try:
                obj = json.loads(t[i:j + 1])
            except Exception:                                  # noqa: BLE001
                obj = None
    if obj is None:
        return None, "answer was not JSON"
    if not isinstance(obj, dict) or not isinstance(obj.get("findings"), list):
        return None, "missing 'findings' list"
    out = []
    for k, f in enumerate(obj["findings"]):
        if not isinstance(f, dict):
            return None, f"findings[{k}] is not an object"
        desc = f.get("description")
        if not isinstance(desc, str) or not desc.strip():
            return None, f"findings[{k}].description must be a non-empty string"
        out.append({"text": desc.strip(),
                    "path": f.get("file") if isinstance(f.get("file"), str) else None,
                    "line": f.get("line") if isinstance(f.get("line"), int) else None,
                    "severity": f.get("severity") if f.get("severity") in SEVERITIES else None,
                    "source": "structured"})
    return out, None


def report_to_candidates(report: dict, case_to_pr: dict[str, str],
                         tool: str) -> tuple[dict, list[dict]]:
    """-> (Martian 形状的 candidates, 逐 case 的问题清单)。

    `tool` 是提交的身份 —— traplite 的 solution_id 是 (agent, prompt, skills, mcps,
    config) 的内容寻址哈希,所以「一条流水线」= 判分管线里的「一个工具」。
    """
    cands: dict[str, dict[str, list]] = {}
    problems: list[dict] = []
    seen = set()
    for r in report.get("cases_results") or []:
        cid = r.get("case_id")
        seen.add(cid)
        url = case_to_pr.get(cid)
        if url is None:
            problems.append({"case_id": cid, "issue": "unknown case_id"})
            continue
        if r.get("exit_code") not in (0, None):
            # 解答方自己报了失败。**空候选不等于「说这个 PR 干净」** ——
            # 它是一次没跑成的运行,由上层决定要不要剔出分母。
            problems.append({"case_id": cid, "issue": f"exit_code={r.get('exit_code')}"})
            cands.setdefault(url, {})[tool] = []
            continue
        found, err = parse_answer(r.get("answer") or "")
        if err:
            problems.append({"case_id": cid, "issue": err})
            cands.setdefault(url, {})[tool] = []
            continue
        cands.setdefault(url, {})[tool] = found
    for cid in case_to_pr:
        if cid not in seen:
            # 漏答按「一个字没说」记 —— 只答有把握的那几题不该刷高精确率。
            problems.append({"case_id": cid, "issue": "missing from report"})
            cands.setdefault(case_to_pr[cid], {})[tool] = []
    return cands, problems
