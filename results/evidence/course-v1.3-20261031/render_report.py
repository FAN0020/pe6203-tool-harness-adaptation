"""Render the audited results and explicit limitations as a readable local report."""

import html
import json
from pathlib import Path

ROOT = Path.cwd()
OUT = ROOT / "results/evidence/course-v1.3-20261031"


def read(path):
    return json.loads(path.read_text())


def esc(value):
    return html.escape(str(value))


def num(value):
    return "—" if value is None else f"{value:.3f}".rstrip("0").rstrip(".")


def table(headers, rows):
    return (
        '<div class="scroll"><table><thead><tr>'
        + "".join(f'<th scope="col">{esc(h)}</th>' for h in headers)
        + "</tr></thead><tbody>"
        + "".join("<tr>" + "".join(f"<td>{esc(v)}</td>" for v in row) + "</tr>" for row in rows)
        + "</tbody></table></div>"
    )


def para(text):
    return f"<p>{esc(text)}</p>"


def link(target, title):
    return f'<a href="{esc(target)}">{esc(title)}</a>'


if __name__ == "__main__":
    summary = read(OUT / "summary.json")
    analysis = read(OUT / "analysis/summary.json")
    audit = read(OUT / "artifact-audit.json")
    costs = read(OUT / "cost-audit.json")
    replay = read(OUT / "reproduction.json")
    interpretation = read(OUT / "interpretation.json")
    diagnostic = read(OUT / "diagnostic-summary.json")
    acceptance = read(OUT / "acceptance.json")
    assert summary["scored"] == 27 and audit["judge_records"]["valid"] == 135
    css = (
        (ROOT / "reports/experiment-readiness.html")
        .read_text()
        .split("<style>")[1]
        .split("</style>")[0]
    )
    page = [
        f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"><title>PE6203 · v1.3 实验报告</title><style>{css}</style></head><body><main>'
    ]
    page += [
        '<div class="eyebrow">PE6203 · COURSE-V1.3 · 2026-10-31 · 实现 12d693c</div><h1>一轮完整实验：结果与验收</h1>',
        '<nav aria-label="目录"><a href="#results">主结果</a><a href="#cases">成功与失败</a><a href="#diagnostic">归因诊断</a><a href="#readiness">剩余要求</a><a href="#reproduce">复算</a></nav>',
        '<div class="notice"><strong>正式矩阵 27/27 条完整评分，135/135 个有效评分槽。</strong>',
        para(interpretation["headline"]),
        "</div>",
        para(
            "固定 133/283 变化任务、235 保持能力对照；Early/Middle/Late × 三种策略 × 1 次执行。每条轨迹五次 judge 是评分重复，不是五次独立 agent 实验。所有结果保留；不跨历史轮次补齐，不重跑低分。"
        ),
        para(
            "模型固定 deepseek/deepseek-v4.1-flash-1017，temperature 0；agent 每次输出上限 4096 tokens、最多 12 轮；judge 4096 tokens、reasoning 关闭。工具调用由 agent 自行选择，候选 servers 由原始任务固定。"
        ),
        table(
            ["知识更新方法", "实现"],
            [
                ["No Update", "保留 Early 工具知识"],
                ["Full Rewrite", "重建当前结构记录，LLM 重写全部描述；Early 共用 K0"],
                [
                    "Selective Patch",
                    "确定性元数据差异 + 依赖规则；只更新受影响记录，保留其他知识；无需 LLM 更新",
                ],
            ],
        ),
        para(
            "范围与生成机制同时不同，因此本比较不是纯更新范围消融。保持模型和原始 rubric 不变不能消除模型随机性、judge 分歧或上游工具缺陷。"
        ),
        '<section id="results"><h2>TF / PE / ECS</h2>',
        table(
            ["阶段", "方法", "TF ↑", "PE ↑", "匹配任务数"],
            [
                [r["stage"], r["strategy"], num(r["TF"]), num(r["PE"]), r["matched_tasks"]]
                for r in analysis["main_results"]
            ],
        ),
        table(
            ["方法", "ECS：发布代码口径 ↑", "ECS：论文样本标准差口径 ↑", "三阶段匹配任务数"],
            [
                [
                    r["strategy"],
                    num(r["upstream_population"]),
                    num(r["paper_sample"]),
                    r["matched_triplets"],
                ]
                for r in analysis["ecs"]
            ],
        ),
        para(
            "ECS 对每个任务计算三阶段 TF 均值减标准差，再在三个任务上取均值。主口径用 population 标准差；另列 sample 标准差敏感性结果。n=3 个任务、每方法每阶段一次，不报告统计显著性或普遍优越性。"
        ),
        "<h2>恢复与保持</h2>",
        table(
            [
                "阶段",
                "方法",
                "任务组",
                "相对同期 No Update 的 TF 差",
                "相对 Early No Update 的 TF 差",
                "任务数",
            ],
            [
                [
                    r["stage"],
                    r["strategy"],
                    r["subgroup"],
                    num(r["delta_vs_no_update_same_stage"]),
                    num(r["delta_vs_no_update_early"]),
                    r["matched_tasks"],
                ]
                for r in analysis["recovery_retention"]
                if r["strategy"] != "no_update"
            ],
        ),
        para(
            "changed 为 133/283；unaffected 为 235。差值描述本轮观测，不能单独证明重写或补丁造成某个结果。"
        ),
        "<h2>更新成本</h2>",
        table(
            ["方法", "更新 tokens", "累计更新时间（秒）", "更新 API USD"],
            [
                [
                    r["strategy"],
                    r["tokens_total"],
                    num(r["seconds_total"]),
                    f"{r['usd_total']:.6f}" if r["usd_total"] is not None else "未知",
                ]
                for r in analysis["update_cost"]
            ],
        ),
        para(
            "以上只统计知识更新，不包含 agent 执行、judge、开发预检与六条归因诊断。Selective Patch 零模型更新 tokens 仍有本地计算时间。费用取提供方 usage，不把未知账单当作零。"
        ),
        table(
            ["阶段", "tokens", "API USD"],
            [[k, v.get("total_tokens"), num(v.get("usd"))] for k, v in summary["cost"].items()],
        ),
        "<h2>测量完整性与执行状态</h2>",
        table(["执行终态", "轨迹数"], audit["execution_counts"].items()),
        para(
            f"评分尝试 {audit['judge_records']['attempted']} 次，选中有效评分 {audit['judge_records']['valid']} 个。每槽采用首次有效结果；语法错误、传输失败及恢复记录均保留。工具 error 数也包含任务要求的边界/安全性测试，不能直接当作任务失败率。"
        ),
        para(interpretation["measurement"]),
        '</section><section id="cases"><h2>本轮代表案例与全部记录</h2>',
    ]
    for case in interpretation["cases"]:
        page += [
            f"<article><h3>{esc(case['title'])}</h3>",
            para("观察：" + case["observation"]),
            para("归因与限制：" + case["limit"]),
        ]
        for cell in case["cells"]:
            page += [para(cell)]
        page += ["</article>"]
    page += [
        table(
            ["任务 / 阶段", "方法", "TF", "PE", "执行状态", "工具 errors"],
            [
                [
                    str(r["task_id"]) + " / " + r["version"],
                    r["strategy"],
                    num(r["TF"]),
                    num(r["PE"]),
                    r["execution_status"],
                    r["tool_errors"],
                ]
                for r in sorted(
                    summary["rows"],
                    key=lambda x: (
                        x["task_id"],
                        ["early", "middle", "late"].index(x["version"]),
                        x["strategy"],
                    ),
                )
            ],
        ),
        "<p>历史成功和失败均保留："
        + link("experiment-readiness.html#cases", "试跑 A/B 的案例和全部 54 条记录")
        + "。本轮未替换旧记录。</p></section>",
        '<section id="diagnostic"><h2>无关描述重写的六条诊断</h2>',
        para(
            "复用试跑 B 的 task235 Late Full Rewrite 知识，与仅把 28 个描述回退为 Early 的知识比较；其余结构、模型与预算一致。两臂各三次独立执行，预先固定顺序。诊断使用已暴露样本，单列记账；不计入上面的 27 条。"
        ),
        table(
            ["诊断臂", "重复", "TF", "PE", "工具调用", "地图调用", "终态"],
            [
                [
                    r["arm"],
                    r["repeat"],
                    num(r.get("TF")),
                    num(r.get("PE")),
                    r.get("tool_calls"),
                    len(r.get("map_calls", [])),
                    r.get("execution_status", r["status"]),
                ]
                for r in diagnostic["rows"]
            ],
        ),
        para(interpretation["diagnostic"]),
        '</section><section id="readiness"><h2>与作业要求的逐项对应</h2>',
        table(
            ["要求 / 计划", "当前状态"],
            [[r["requirement"], r["status"]] for r in interpretation["requirements"]],
        ),
        "<h2>Netlify 与工具选择</h2>",
        para(
            "Netlify 是 deploy_html / deploy_folder_or_zip 的执行后端。三种方法的 agent 自主决定何时抓取、筛选、生成 HTML、调用发布工具。账号、授权与专用站点由用户在准备阶段确定，随后冻结；不会让 agent 自主替用户选择账号。浏览器登录与 CLI 凭据不是同一份状态。"
        ),
        para(acceptance["separate_work"]["netlify"]),
        "<p><code>./experiment papers --prepare-only</code>：检查依赖 → 显示并确认/切换 CLI 账号 → 浏览器授权 → 选择专用站点 → 冻结论文来源与工具目录。然后 <code>./experiment run --output &lt;网页目录&gt; --limit 1</code>，检查后用 <code>--resume</code> 继续同一九条计划。</p>",
        para(
            "来源预检中，Hugging Face 按相关性排序，不能直接取前五条；arXiv 日期倒序检索已可抓取。正式网页实验必须冻结所用来源并核对五篇论文的日期、题名、链接与公开 draft 内容。task223 三阶段目录相同，只证明网页流程/保持能力，不能独自证明环境变化恢复。"
        ),
        "<h2>10 分钟讲述提纲（待小组审核）</h2>",
        table(
            ["时间", "内容"],
            [
                ["0:00–1:00", "问题：工具知识过时如何恢复，同时保留未变化能力"],
                ["1:00–2:30", "元数据差异与依赖补丁；两个基线；agent 自动选择工具"],
                ["2:30–4:00", "固定子集与公平协议；一次重复、五个 judge 的区别"],
                ["4:00–6:00", "三阶段 TF/PE/ECS，恢复/保持，更新成本"],
                ["6:00–7:30", "真实失败轨迹；区分 stale schema、预算、评分和上游缺陷"],
                ["7:30–8:30", "六条描述回退诊断；如实说明未证明的因果关系"],
                ["8:30–10:00", "适用范围、局限、尚缺的因果案例及后续扩展"],
            ],
        ),
        para(
            "5 分钟 Q&A 重点：为何只选三个任务；是否纯 scope 消融；为什么 TF 高而 execution 未完成；ECS 两种标准差；为什么登录不交给 agent；零更新 tokens 是否等于零总成本。此提纲不是已完成的课堂展示。"
        ),
        '</section><section id="reproduce"><h2>验证与复算</h2>',
        para(
            "299 项测试通过；原始 rubric 保留，所有工具派发可追溯到先前模型返回。对主结果独立复算；终态 resume 未增加模型调用或改变已有记录；归档内实现断网、去凭据运行后，两份汇总与原件逐字节一致。"
        ),
        "<p>"
        + link(
            "../results/evidence/course-v1.3-20261031/raw-trial.tar.gz",
            "正式轨迹、开发检查及冻结实现归档",
        )
        + " · "
        + link("../results/evidence/course-v1.3-20261031/diagnostic.tar.gz", "独立六条诊断归档")
        + " · "
        + link("../results/evidence/course-v1.3-20261031/acceptance.json", "逐项验收")
        + " · "
        + link("../results/evidence/course-v1.3-20261031/metrics-audit.json", "指标独立复算")
        + "</p>",
        para("主归档 SHA256：" + replay["sha256"]),
        "<p><code>./experiment report --output results/raw/course-v1.3-final-20261031</code>：本机复算，零模型调用。完整离线复算方法见 "
        + link("../results/evidence/course-v1.3-20261031/reproduction.json", "reproduction.json")
        + "。</p>",
        "<p>新实验：<code>./experiment prepare --suite experiments/benchmark-v1.3.json --repeats 1 --output results/raw/&lt;新ID&gt;</code>，再执行 <code>./experiment run --output results/raw/&lt;新ID&gt;</code>。改变模型、预算或协议须新建计划，不能覆盖本轮。</p>",
        "</section><footer>这是一轮课程子集实验，不宣称复现论文 leaderboard。历史失败、缺失和发展过程保留供复核。</footer></main></body></html>",
    ]
    source_url = "https://arxiv.org/search/?query=embodied+ai&searchtype=all&abstracts=show&order=-announced_date_first&size=50"
    page.insert(
        page.index("<h2>10 分钟讲述提纲（待小组审核）</h2>"),
        "<p>可选的日期倒序来源："
        + link(source_url, "arXiv 检索")
        + "</p><p><code>"
        + esc("./experiment papers --prepare-only --source-url '" + source_url + "'")
        + "</code></p>",
    )
    destination = ROOT / "reports/course-v1.3-experiment.html"
    cost_note = para(
        f"逐请求成本审计：agent 与 judge 的已知费用合计 USD {costs['known_execution_usd']:.6f}；"
        f"另有 {costs['unknown_execution_charges']} 次请求费用未知。更新费用另计 USD {costs['update_usd']:.6f}。"
        "这是已记录费用，不是完整账单；开发预检和独立诊断不含在内。"
    )
    page.insert(page.index("<h2>测量完整性与执行状态</h2>"), cost_note)
    destination.write_text("\n".join(page), encoding="utf-8")
    print(destination)
