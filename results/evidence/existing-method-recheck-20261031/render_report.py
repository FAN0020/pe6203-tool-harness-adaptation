"""Render the replication and cross-cohort interpretation; never alter historical scores."""
import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def main():
    v = json.loads((HERE/'trial-verification.json').read_text())
    q = json.loads((HERE/'quality-review.json').read_text())
    history = json.loads((HERE/'historical-reverification.json').read_text())
    css = (ROOT/'reports/budget-contract-results.html').read_text().split('<style>',1)[1].split('</style>',1)[0]
    parts = ['<!doctype html><html lang="zh-CN"><meta charset="utf-8">',
             '<meta name="viewport" content="width=device-width,initial-scale=1">',
             '<title>PE6203 · 既有方法复核与研究取舍</title>', f'<style>{css}</style><main>',
             '<h1>既有方法复核：保留收益，也保留反例</h1>',
             '<p class="note">'+html.escape(q['headline_zh'])+'</p>',
             '<p>2026-10-31 · 无新策略。预先固定task283 Middle（历史阳性）、133 Late（安全建议反例）、235 Late（不变任务），原Selective Patch与budget_feedback各一次，共6轨迹／30原协议评分。此处是独立研究附录，不替换27条课程主实验或共享Slides。</p>',
             '<h2>本轮原始结果</h2><table><tr><th>方法</th><th>正常结束</th><th>变化任务</th><th>不变任务</th><th>TF</th><th>PE</th><th>更新tokens / USD</th></tr>']
    for name,s in v['summary'].items():
        parts.append(f"<tr><td>{name}</td><td>{s['completed']}/3</td><td>{s['changed_completed']}/2</td><td>{s['retention_completed']}/1</td><td>{s['TF']:.4f}</td><td>{s['PE']:.4f}</td><td>0 / 0</td></tr>")
    parts += ['</table><p>不对这个不完整的两阶段子集计算ECS；正常结束、任务内容和judge分数分开。原始TF/PE未因发现评分错误而修改。</p>',
              '<table><tr><th>Cell</th><th>Task / stage</th><th>方法</th><th>终态 / 轮数</th><th>TF</th><th>PE</th></tr>']
    for r in v['cells']:
        parts.append(f"<tr><td>{r['cell_id']}</td><td>{r['task_id']} / {r['stage']}</td><td>{r['strategy']}</td><td>{r['execution_status']} / {r['rounds']}</td><td>{r['TF']}</td><td>{r['PE']}</td></tr>")
    parts += ['</table><h2>独立检查：分数不能代替事实</h2>']
    for c in q['cells']:
        r=next(x for x in v['cells'] if x['cell_id']==c['cell_id'])
        parts.append(f"<details open><summary>{c['cell_id']} · {r['task_id']} {r['stage']} · {r['strategy']}</summary><p>{html.escape(c['review_zh'])}</p><p>TF原评分：{[x['TF'] for x in r['judge_values']]}；PE原评分：{[x['PE'] for x in r['judge_values']]}</p></details>")
    parts += ['<h2>故障属于哪一层</h2>',
              '<table><tr><th>观察</th><th>支持的判断</th><th>不支持的判断</th></tr>',
              '<tr><td>两组规划耗尽12轮</td><td>本次完成收益未复现；已有实际产物</td><td>不能自动说工具更新失败或整个任务内容为空</td></tr>',
              '<tr><td>BF七个日志任务使用错误父UUID</td><td>参数抄写错误；改正后均成功创建</td><td>不是七次原参数重试；没有证明知识缺参</td></tr>',
              '<tr><td>层级列表55条，但只有30个不同ID</td><td>上游把子任务重复计数；后续另创建11条，最终41</td><td>不能把工具错误数字全归因于agent或judge凭空捏造</td></tr>',
              '<tr><td>Python示例拒绝Add节点；指数推论越界</td><td>回答代码/推理缺陷；已用静态证据定位</td><td>不是已确认under-update或over-update；不等于完整安全审计</td></tr>',
              '<tr><td>多份judge理由虚构最终回答、错误重试次数</td><td>计数/事实问题与1000字符观察截断需分别披露</td><td>不能自行修正历史分数或由TF差值断言补丁因果</td></tr></table>',
              '<h2>所有近期对照放在一起看</h2><p>以下按cohort分开。七组已从原始归档重新核算一致；不是把不同任务、供应商或复用轨迹混成一个统计样本。matched-existing已明确复用budget-contract的3条BF，禁止重复计入总量。早期策略搜索和网络中断记录仍在原研究报告中。</p>',
              '<table><tr><th>研究 / 方法</th><th>正常结束</th><th>TF</th><th>PE</th><th>主要限制</th></tr>']
    labels={
        'completion-quality-20261031':('初次完成/质量比较','供应商混用；两组完成4/6'),
        'budget-contract-20261031':('具体预算规则候选','候选未胜；三格不是三阶段'),
        'matched-existing-20261031':('已有方法补充比较','3条复用，两个批次；有实际产物收益也有反例'),
        'evidence-scope-pilot-20261031':('追加证据规则候选','候选完成更低；不晋级'),
        'tool-migration-pilot-20261031':('Swift工具迁移','四方法同一任务三阶段；单次且代码有附加错误'),
        'daily-migration-pilot-20261031':('每日题实时信息迁移','四方法均3/3；只NU缺当日内容，BF非PE最高')}
    for cohort in history['cohorts']:
        if cohort['cohort'] not in labels:
            continue
        label,limit=labels[cohort['cohort']]
        for method,s in cohort['summary'].items():
            n=s.get('cells',3)
            parts.append(f"<tr><td>{label}<br>{method}</td><td>{s['completed']}/{n}</td><td>{s['TF']:.4f}</td><td>{s['PE']:.4f}</td><td>{limit}</td></tr>")
    parts += ['</table><p>历史matched-existing中BF完成6/6、原SP2/6，task283 Middle的具体拆分和356h汇总真实改善，仍是有效的局部阳性。初次比较没有完成收益，本次复核两组2/3且BF分数较低，说明不能据那一批次宣称稳定胜者。迁移实验支持更新知识恢复工具/内容，但不足以证明额外预算规则普遍提高质量。Early及task235相同K0的差异不能归因于适应。</p>',
              '<h2>方法与课程交付的边界</h2><p>原Selective Patch：目录差异 → 显式依赖影响范围 → 仅复制受影响目标字段 → 验证schema/routing与不变记录。budget_feedback在变化/新增记录追加参数变化说明、固定公开探测反馈和必要工作/预算规则；本轮六份知识与历史对应版本相同，没有新增规则，也没有把任务、答案或judge反馈送入updater。</p>',
              '<p>No Update保留K0。Full Rewrite重建完整目标目录，LLM重新生成全部description；schema、output schema、routing和已有usage rules复制目标值。该实现解释已披露，是否满足教师对“全部知识再生成”的预期仍列入TA问题；不能改实现后沿用旧分数。四方法迁移研究有同一模型/供应商/预算的三阶段对照，但与原3任务课程主表保持独立。</p>',
              '<p>课程27条／135评分／10,959历史文件及4诊断再次离线复核通过。主实验费用仍为已知$0.40691929208加1笔未知，不能因本轮无未知费用而把旧未知项置零。原Patch九个PE仍是：133＝10/8/7；235＝10/10/10；283＝9/9.4/8.6；合计82，平均82/9＝9.1111。课程要求TF、PE、ECS、恢复、保持、更新成本和失败分析，不要求PE+0.5、胜过所有baseline或每个附加句子完美。当前方法可作为透明的研究交付；“稳定提高完成率与任务质量”的更强研究结论尚未成立。</p>',
              '<table><tr><th>必需内容</th><th>已有证据</th><th>仍需说明</th></tr>',
              '<tr><td>三方法 / 三阶段 / TF PE ECS</td><td>原课程27条；迁移附录四方法三阶段</td><td>不混合不同cohort；ECS总体SD与样本SD分别报告</td></tr>',
              '<tr><td>Tool / Parameter / Description</td><td>原覆盖表与430/90真实删除/迁移补充</td><td>环境存在、任务相关、实际触达三个层次不可混淆</td></tr>',
              '<tr><td>恢复 / 保持 / 成本</td><td>迁移工具和当日题恢复；235原数据保持；逐请求账本</td><td>代码/摘要反例保留；零updateAPI不等于零开发或探测成本</td></tr>',
              '<tr><td>under-update</td><td>受控缺allow_variables导致8次缺参拒绝</td><td>受控机制confirmed；不是原updater自然遗漏；TA适用性未确认</td></tr>',
              '<tr><td>over-update</td><td>无关Wikipedia路由readArticle→read_article导致两次读取失败；控制成功</td><td>受控局部损害confirmed；保护验证器会拒绝它；两条完整任务都结束；TA适用性未确认</td></tr>',
              '<tr><td>报告 / 复现 / 展示</td><td>课程PDF、源代码/原始包、13主讲+5Q&A Slides和讲稿已存在</td><td>研究附录未自动覆盖冻结交付；团队排练、TA答复及正式提交需团队完成</td></tr></table>',
              '<p>TA问题草稿（不发送）：明确披露的受控缺参与无关路由局部失败是否足以满足§4.2？若不足，需补哪种证据？FR完整记录重建但保护schema/routing、复制usage rules是否满足§§2/4.1？这些是要求解释问题，继续优化分数不能替代澄清。旧相关usage-rule对照仍仅suggestive，六条chart负诊断仍保留。</p>',
              '<h2>公平、费用与复现</h2><p>两方法实际均DigitalOcean，模型deepseek/deepseek-v4.1-flash-1017、temperature0、4096输出tokens、12轮、相同原始任务和五槽judge。固定单次执行条件用于公平比较；没有总费用/轨迹额度或provider价格门槛。日期、服务及隐藏后端版本仍会变化。此处一格一次是定点复核，不能称统计显著或独立保护测试。</p>',
              f"<p>{v['api_requests']}请求＝33 agent＋30 judge＋2预检。已知US${v['known_usd']}，未知{v['unknown_cost_items']}项；账本首尾{v['elapsed_seconds']:.2f}秒。更新模型调用／tokens／API费用均0；两方法更新时间分别见复算JSON。金额来自响应，不是独立账户账单。</p>",
              '<p>复核结论：不晋级budget_feedback，不低分重跑直到赢，不启动81/108矩阵。已找到局部收益，也已记录未复现和质量缺陷。任何后续改动应先找到具体缺失/错误的知识机制；目前UUID抄写、生成代码错误和上游计数问题不能自动成为追加通用规则的理由。</p>',
              '<pre>python3 results/evidence/existing-method-recheck-20261031/verify_trial.py\npython3 results/evidence/existing-method-recheck-20261031/check_artifacts.py\npython3 results/evidence/existing-method-recheck-20261031/check_math_examples.py\npython3 results/evidence/existing-method-recheck-20261031/check_observations.py</pre>',
              '<p>源码冻结e59c430；266文件原始归档SHA-256：'+v['archive_sha256']+'</p><h2>审阅入口</h2><p>']
    for name in ['trial-verification.json','quality-review.json','judge-audit.json','artifact-checks.json','math-example-checks.json','observation-checks.json','historical-reverification.json','course-reverification.json','postrun-freeze.json','raw-manifest.json','raw-trial.tar.gz','source-e59c430.tar.gz','source-manifest.json','upstream-source-manifest.json','upstream-source.tar.gz','reproduction.json']:
        parts.append(f'<a href="../results/evidence/existing-method-recheck-20261031/{name}">{name}</a> · ')
    for report in ['matched-existing-results.html','tool-migration-results.html','daily-migration-results.html','routing-fault-results.html','selective-strategy-search.html']:
        parts.append(f'<a href="{report}">{report}</a> · ')
    parts += ['<a href="../submission/report-final.html">冻结课程报告</a> · <a href="../HANDOVER.md">HANDOVER</a></p></main></html>']
    (ROOT/'reports/existing-method-recheck.html').write_text('\n'.join(x.rstrip() for x in parts)+'\n')


if __name__ == '__main__':
    main()
