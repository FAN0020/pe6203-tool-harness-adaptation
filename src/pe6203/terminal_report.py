"""Readable, terminal-safe presentation of saved benchmark observations."""

import json
import re
import unicodedata
from collections import Counter

MISSING = "未获得"


def safe_text(value):
    text = str(value)
    # Strip terminal escape sequences and control characters from model/tool content.
    text = re.sub(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)", "", text)
    text = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text)
    return "".join(c for c in text if c in "\n\t" or not unicodedata.category(c).startswith("C"))


def brief(value, limit=160):
    text = " ".join(safe_text(value).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def number(value, decimals=0):
    return MISSING if value is None else f"{value:,.{decimals}f}"


def argument_preview(arguments):
    if not isinstance(arguments, dict):
        return brief(arguments, 180)
    # Put the operation's subject before workspace paths and opaque identifiers.
    ordered = {key: arguments[key] for key in ("name", "title") if key in arguments}
    ordered.update({key: value for key, value in arguments.items() if key != "workingDirectory"})
    return brief(json.dumps(ordered, ensure_ascii=False), 180) if ordered else ""


def details(run):
    lines = ["", "Judge 明细（1–10 分；失败记录不补零）", "  #   TF     Grounding   PE     结果"]
    for index, judge in enumerate(run["judges"], 1):
        scores = judge["scores"] or {}
        values = [
            number(scores.get(key), 2)
            for key in ("task_fulfillment", "grounding", "planning_and_efficiency")
        ]
        state = "有效" if scores else f"失败 / {judge['finish_reason'] or MISSING}"
        lines.append(f"  {index}   {values[0]:<6} {values[1]:<10} {values[2]:<6} {state}")
        if judge["error"]:
            lines.append(f"      {brief(judge['error'], 240)}")
    if not run["judges"]:
        lines.append("  无已保存的评分明细")
    lines += ["", "工具轨迹（仅展示已保存的调用；完整输入/输出见原始 JSON）"]
    for index, call in enumerate(run["calls"], 1):
        seconds = f"+{call['seconds']:.1f}s" if call["seconds"] is not None else "时间未记录"
        state = "ERROR" if call["error"] else "OK"
        lines.append(
            f"  {index:02}  {seconds:>10}  round={call['round']}  {state:<5} {call['name']}"
        )
        arguments = call["arguments"]
        if arguments:
            preview = argument_preview(arguments)
            if preview:
                lines.append(f"      {preview}")
        if call["error"]:
            lines.append(f"      {brief(json.dumps(call['output'], ensure_ascii=False), 300)}")
    if not run["calls"]:
        lines.append("  无已保存的调用明细")
    lines += ["", "任务原文", run["question"] or MISSING, "", "最终回答", run["answer"] or MISSING]
    if run["audit_note"]:
        lines += ["", "证据核对备注", str(run["audit_note"])]
    return lines


def render_report(data, *, expanded=False):
    lines = ["PE6203 · Benchmark 运行报告", "=" * 64]
    if data["protocols_differ"]:
        lines += ["注意：运行配置不同，分数不能直接比较；以下分别展示，不计算跨运行均值。", ""]
    elif len(data["runs"]) > 1:
        lines += ["多条运行分别展示；可比性还需核对任务、seed 与冻结协议。", ""]
    for index, run in enumerate(data["runs"]):
        if index:
            lines += ["", "-" * 64]
        valid = sum(bool(j["scores"]) for j in run["judges"])
        expected = run["judge_expected"]
        observed = str(valid) if run["judge_records_available"] else "?"
        judge_count = f"{observed}/{expected}" if expected is not None else f"{observed}/?"
        complete = run["judge_status"] == "complete"
        scoring = "评分完整（任务表现见分数与产物）" if complete else "评分未完成 / 未获得"
        lines += [
            f"[{index + 1}] {run['label']}",
            f"任务       {run['task_id']}  |  {run['version']}  |  {run['strategy']}  |  seed={run['seed']}",
            f"状态       {run['status']}  ·  {scoring}",
            f"阶段       agent={run['execution_status'] or MISSING}  |  judge={run['judge_status'] or MISSING} ({judge_count} 有效)",
            f"模型       {run['model'] or MISSING}",
        ]
        if run.get("artifact_validation"):
            artifact = run["artifact_validation"]
            accepted = bool(artifact.get("accepted_artifact"))
            lines.append(
                f"产物验收   {artifact['status']} | accepted={accepted} | security_guarantee=False"
            )
            lines.append(
                f"生成/修复  initial={run.get('generation_status')} | final={run['execution_status']} | origin={run.get('completion_origin')} | repairs={len(artifact.get('repairs', []))}"
            )
        if run["judge_model"] and run["judge_model"] != run["model"]:
            lines.append(f"Judge 模型 {run['judge_model']}")
        if run.get("execution_backend"):
            lines.append(f"执行方式   {run['execution_backend']}")
        if run["execution_status"] == "max_rounds":
            lines.append(
                f"执行限制   达到 {run.get('max_rounds') or '配置的'} 轮数上限；请检查最终回答与实际产物。"
            )
        scores = run["scores"]
        lines.append(
            f"评分       TF {number(scores['TF'], 2)} / 10  |  PE {number(scores['PE'], 2)} / 10  |  ECS {number(scores['ECS'], 2)}"
        )
        lines.append("           TF=任务完成度；PE=规划与效率；ECS 需 Early/Middle/Late 三阶段 TF")
        if valid and not complete:
            lines.append("           当前分数仅来自部分有效 judge，不能当作完整评分。")
        total = run["tool_count"]
        errors = number(run["tool_errors"])
        if total is not None and not run["trace_complete"]:
            errors = f"至少 {errors}"
        lines += [
            f"工具       {number(total)} 次调用  |  {errors} 次错误  |  可见明细 {len(run['calls'])}/{number(total)}",
            f"耗时       {number(run['seconds'], 2)} 秒",
        ]
        counts = run["state_counts"]
        if counts:
            labels = [
                ("project_count", "项目"),
                ("task_count", "任务"),
                ("entity_count", "实体"),
                ("relation_count", "关系"),
            ]
            lines.append(
                "实际产物   "
                + "  |  ".join(f"{label} {number(counts.get(key))}" for key, label in labels)
            )
        project_names = [p.get("name", "") for p in run["projects"] if p.get("name")]
        if project_names:
            lines.append(f"项目名称   {brief(', '.join(project_names))}")
        cost = run["cost"]
        tokens = "  |  ".join(
            f"{key} {number((cost.get(key) or {}).get('total_tokens'))}"
            for key in ("agent", "judge", "update")
        )
        lines += [f"Tokens     {tokens}", f"费用       USD {number(cost.get('usd'), 4)}"]
        if cost.get("update"):
            update = cost["update"]
            lines.append(
                f"更新开销   {number(update.get('seconds'), 2)} 秒  |  USD {number(update.get('usd'), 4)}"
            )
        failures = Counter(
            j["finish_reason"] or "unknown" for j in run["judges"] if not j["scores"]
        )
        if failures:
            lines.append(
                "评分失败   "
                + "; ".join(f"finish_reason={reason} × {n}" for reason, n in failures.items())
            )
            first_error = next((j["error"] for j in run["judges"] if j["error"]), None)
            if first_error:
                lines.append(f"           {brief(first_error, 240)}")
        for error in run["errors"]:
            lines.append(
                f"运行错误   {brief(error.get('message', error) if isinstance(error, dict) else error, 300)}"
            )
        if run["question"]:
            lines.append(f"任务要求   {brief(run['question'])}")
        if run["answer"]:
            lines.append(f"回答摘要   {brief(run['answer'])}")
        if run["audit_note"] and not expanded:
            lines.append("核对备注   已保存产物与回答/评分计数有核对备注，使用 --details 查看。")
        lines.append(f"来源       {run['source']}")
        if expanded:
            lines.extend(details(run))
    lines += ["", "未获得表示缺失数据，不代表 0。--details 查看每次评分、工具轨迹和最终回答。"]
    return safe_text("\n".join(lines)) + "\n"
