"""Render the frozen verification result without recomputing or changing scores."""
import html
import json
from pathlib import Path

FOLDER = Path(__file__).resolve().parent
ROOT = FOLDER.parents[2]


def esc(value):
    return html.escape(str(value))


def table(headers, rows):
    return '<div class="scroll"><table><thead><tr>' + ''.join(f'<th>{esc(x)}</th>' for x in headers) + '</tr></thead><tbody>' + ''.join(
        '<tr>' + ''.join(f'<td>{esc(x)}</td>' for x in row) + '</tr>' for row in rows
    ) + '</tbody></table></div>'


def main():
    data = json.loads((FOLDER / 'validation-verification.json').read_text())
    assert data['verified'] and len(data['cells']) == 36
    block_rows = []
    for block, result in data['blocks'].items():
        for arm, scopes in result['arms'].items():
            for scope, row in scopes.items():
                block_rows.append([block, arm, scope, f"{row['completed']}/{row['n']}",
                                   f"{row['core_pass']}/{row['n']}", f"{row['TF']:.4f}", f"{row['PE']:.4f}"])
    cell_rows, evidence = [], []
    for row in data['cells']:
        review = json.loads((FOLDER / 'blind-reviews' / (row['review_id'] + '.json')).read_text())
        cell_rows.append([row['cell_id'], row['block'], row['repeat_index'], f"{row['task_id']}/{row['stage']}",
                          row['strategy'], row['execution_status'], row['TF'], row['PE'],
                          '; '.join(f'{k}={v}' for k, v in row['properties'].items())])
        evidence.append(f'<li><a href="../results/evidence/{FOLDER.name}/blind-reviews/{row["review_id"]}.json">{esc(row["cell_id"])} / {esc(row["review_id"])}</a>: ' + esc(' '.join(review['evidence'])) + '</li>')
    conditions = [[key, f"{r['completed']}/{r['n']}", f"{r['core_pass']}/{r['n']}", f"{r['TF']:.4f}", f"{r['PE']:.4f}"]
                  for key, r in data['per_condition'].items()]
    updates = [[key, value['calls'], value['total_tokens'], value['usd'], f"{value['seconds']:.6f}", value['update_operations']]
               for key, value in data['distinct_update_costs'].items()]
    gates = [[block, name, '通过' if passed else '未通过'] for block, result in data['blocks'].items() for name, passed in result['gates'].items()]
    token_rows = []
    for arm in data['overall']:
        rows = [r for r in data['cells'] if r['strategy'] == arm]
        for role in ('agent', 'judge'):
            token_rows.append([arm, role, sum(r['tokens'][role]['prompt_tokens'] for r in rows),
                               sum(r['tokens'][role]['completion_tokens'] for r in rows),
                               sum(r['tokens'][role]['total_tokens'] for r in rows)])
    page = '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PE6203 · 观测契约独立验证</title><style>body{font:16px/1.7 system-ui;max-width:1200px;margin:32px auto;padding:20px;color:#182437}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:9px;border-bottom:1px solid #ccd3dd;text-align:left;vertical-align:top}th{background:#eef3f8}pre{white-space:pre-wrap}a{color:#1859a5}.scroll{overflow:auto}.decision{border-left:5px solid #a43729;padding:12px 20px;background:#fff4f1}li{margin-bottom:10px}</style></head><body>
<h1>观测契约独立验证：未复现双重改善，候选淘汰</h1>
<p>2026-10-31 · 固定36次新执行 / 两个18次验证批次 / 180个原协议评分。开发与验证分开，候选知识没有调整。研究目标仍未完成。</p>
<div class="decision"><p>变化任务133：候选正常完成5/12（41.7%），原Selective Patch为8/12（66.7%）；必需产物全项通过均0/12。两个验证批次的完成率、产物全项通过率和TF门槛均未满足。候选不晋升，不重抽同一方案直到赢。</p>
<p>局部知识解释有所改善：候选validation属性通过9/12，原SP为2/12；但改善没有转化为正确的完整Python产物。原SP有1份实现一致性通过，仍因工具解释失败而未全项通过。不能拿局部属性替代原先冻结的完成目标。</p></div>
<h2>冻结机制与验收</h2><p>16次独立安全语法探测与源码核对发现：新增allow_variables、max_depth等参数未被handler落实，且语法错误可能返回isError=false；旧probe_note省略了成功响应的正文。候选只在已变化的validate_syntax追加有限长度的真实输入/响应；不加入通用预算、代码模板、任务答案或提前结束规则。两方法的结构字段相同，235保持任务逐字等于K0。</p>
<p>每个验证批次均须：变化任务正常完成数严格增加、产物全项通过数严格增加、原TF不下降；保持任务的完成数、全项通过数与TF不下降。未知不算通过，五个judge只是评分而非五次执行。日程使用CLI development字段承载，科学划分明确为independent_validation；不使用旧PE晋级阈值。</p>
<h2>两批结果（每方法：变化6次、保持3次）</h2>'''
    page += table(['批次','方法','任务范围','正常完成','产物全项通过','TF','PE'], block_rows)
    page += '<p>保持任务235三类图表全部保留正确输入/单位并成功返回；摘要算术或比较错误使候选全项通过2/6、SP3/6。因为两方法知识相同，这个差异不能归因于知识适应；它仍按事前验收规则计入保持结果。所有未正常完成项均为输出截断，无max_rounds。</p>'
    page += table(['批次','原先冻结的门槛','判定'], gates)
    page += '<h2>按条件与配对结果</h2>' + table(['条件','正常完成','全项通过','TF','PE'], conditions)
    page += '<p>同task/stage/repeat配对：变化任务完成状态中候选独有成功1对、原SP独有成功4对、共同成功4对、共同未完成3对；产物全项12对均未通过。A批候选独有完成0、原SP独有1；B批分别1和3。没有Early执行，因此不声称测得相对Early的恢复率。</p>'
    page += '<h2>公平性、盲化与复现</h2><p>模型deepseek/deepseek-v4.1-flash-1017，实际供应商DigitalOcean固定且禁止fallback；temperature0、4096输出tokens、12轮、900秒运行预算、原五槽judge与1000字符观察截断保持一致。6份知识与pilot哈希相同，52个冻结输入匹配，策略名未进入初始提示。36份属性判定在c30aec3提交冻结后才揭示方法/TF/PE。审阅者仍是同一协调者，答案内容可能泄露方法，不能称为独立人工盲审。</p>'
    page += '<p>离线复算逐项核对原始终态、五个原始评分、response ID、费用账本、知识差异、先冻结的属性审阅及两个门槛；没有重新调用模型或改写评分。1367个原始文件与42个源码/配置文件已归档。运行时二进制保留哈希，远端服务行为不能离线重演。重复数是已暴露任务上的描述性复核，不是新任务泛化或显著性结论。生成Python只做静态审阅，不执行，也不等于完整安全审计；图表渲染未知，没有事后追加为失败条款。</p>'
    page += '<h2>费用、更新与tokens</h2><p>验证280请求：98 agent + 180 judge + 2预检；总US$0.352885824（预检$0.00001296），未知费用0，运行约848.49秒。原SP agent+judge为$0.172118628，候选$0.180754236。加上开发试验$0.059853732，本机制的开发+验证模型费用$0.412739556；16个本地探测无模型调用，独立归档记录其时间。</p>'
    page += table(['方法','角色','输入tokens','输出tokens','total tokens'], token_rows)
    page += '<p>以下为实际生成的6份共享适应，不把重复cell中的引用当成36次更新。更新API/tokens/USD均0；候选增加的提示文本仍会体现在agent输入费用中。</p>'
    page += table(['适应','模型调用','tokens','USD','秒','操作数'], updates)
    page += '<h2>课程边界与下一轮研究约束</h2><p>这是局部Middle/Late研究验证，ECS未定义。No Update、Full Rewrite、完整三阶段ECS沿用独立冻结课程cohort，不与本组拼接，也不改原PDF/Slides。课程比较、报告/复现包/展示材料最终核对仍待成功策略出现后整合；本轮负结果不能作为用户Goal完成条件。</p><p>新候选必须先证明不同的选择性知识适应机制，再冻结新的知识差异、任务子集、产物属性和独立复核门槛。当前结果支持“响应语义遗漏被纠正”，不支持“已解决代码生成能力与输出截断”。下一步先离线检查还有哪些变化工具的可执行契约会直接影响任务必要产物；没有机制证据前不重跑旧候选或放宽验收。</p>'
    page += '<h2>完整36次结果</h2>' + table(['Cell','批次','重复','Task/Stage','方法','终态','TF','PE','属性判定'],cell_rows)
    page += '<h2>逐份产物判据与证据</h2><ol>' + ''.join(evidence) + '</ol>'
    page += '<h2>离线复核入口</h2><pre>python3 results/evidence/observed-contract-validation-20261031/verify_blind_reviews.py --require-complete\npython3 results/evidence/observed-contract-validation-20261031/verify_validation.py</pre><p>'
    links = [('冻结机制/门槛','../experiments/observed-contract-v1.json'),('验证日程','../experiments/observed-contract-validation-v1.json'),('独立复算JSON',f'../results/evidence/{FOLDER.name}/validation-verification.json'),('原始归档',f'../results/evidence/{FOLDER.name}/raw-trial.tar.gz'),('复现说明',f'../results/evidence/{FOLDER.name}/reproduction.json'),('开发试验','observed-contract-pilot.html'),('历史方法复核','existing-method-recheck.html'),('冻结课程报告','../submission/report-final.html')]
    page += ' · '.join(f'<a href="{href}">{label}</a>' for label,href in links) + '</p></body></html>\n'
    (ROOT / 'reports/observed-contract-validation.html').write_text(page)
    print('reports/observed-contract-validation.html')


if __name__ == '__main__':
    main()
