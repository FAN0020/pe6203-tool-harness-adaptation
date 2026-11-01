"""Render the measured decision without relabeling any execution or review."""
import html
import json
from pathlib import Path
E=Path(__file__).resolve().parent
ROOT=E.parents[2]
esc=html.escape

def main():
 d=json.loads((E/'decision.json').read_text()); interp=json.loads((E/'interpretation.json').read_text())
 labels={'selective_patch':'原 SP','capability_warning':'警告诊断组','capability_withdrawal':'撤下工具（主候选）'}
 rows=[]
 for strategy,groups in d['metrics'].items():
  for group,m in groups.items():
   rows.append('<tr>'+''.join(f'<td>{esc(str(x))}</td>' for x in [labels[strategy],'283 Late' if group=='changed' else '235 Late',f"{m['completed']}/{m['n']}",f"{m['core_pass']}/{m['n']}",m['TF'],m['PE']])+'</tr>')
 links=[('冻结方案','experiments/capability-withdrawal-v1.json'),('机制与来源','results/evidence/capability-withdrawal-20261101/research-decision.json'),('原始指标与费用','results/evidence/capability-withdrawal-20261101/decision.json'),('产物审查及解释','results/evidence/capability-withdrawal-20261101/interpretation.json'),('离线复核脚本','results/evidence/capability-withdrawal-20261101/verify_archive.py'),('复现说明','results/evidence/capability-withdrawal-20261101/reproduction.txt')]
 body=''.join(f'<p>{esc(s)}</p>' for s in interp['conclusions'])
 doc=f'''<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>PE6203 失效能力撤下开发试验</title>
 <style>body{{font:16px/1.65 system-ui,sans-serif;max-width:1050px;margin:40px auto;padding:0 22px;color:#182338}}table{{border-collapse:collapse;width:100%;margin:24px 0}}td,th{{border:1px solid #ccd4df;padding:9px;text-align:left}}th{{background:#edf3fb}}a{{color:#1558b0}}.status{{background:#fff2d6;padding:16px}}code{{overflow-wrap:anywhere}}</style>
 <h1>PE6203：失效能力撤下 v1</h1><p class="status">{esc(d['decision'])}。完整双提升 Goal 尚未完成；独立验证未启动。</p>
 <p>固定原 benchmark 283 Late 与 235 Late，三组各运行一次，共六条。方法仅改变静态工具知识：撤下三个有源码及原生失败证据的工具，清除五处直接推荐。警告组保留工具但加入同一证据，并共享推荐清理；它仅作诊断，不能事后晋级。模型、供应商、解码、4096 输出预算、12 轮、原生工具、执行器及评分验收未变。</p>
 <table><thead><tr><th>方法</th><th>任务</th><th>正常完成</th><th>产物全项通过</th><th>TF</th><th>PE</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
 {body}<p>新增模型费用 USD {d['round_total_usd']}；未知及未结费用为零。确定性更新器没有模型调用；既有原生探针直接复用，未重复采集。本次 ECS 不适用于部分阶段日程。历史 NU/FR 和三阶段课程结果独立保留，不能充当同期对照。</p>
 <p>文献依据：<a href="https://arxiv.org/html/2308.10144v3">ExpeL v3</a> 与作者仓库 e41ec9a 的规则降权、删除机制。源码 REMOVE 先降计数，计数到零才删除。本研究借鉴知识撤回，扩展为源码证书驱动的工具记录撤下；没有移植其训练轨迹、成功经验检索或 LLM 反馈循环，不能称为完整复现。</p>
 <p>评审偏差：四份判断（含全部283）先写入，执行器随后自动打印分组均分，最后两份235判断再写入。不能声称六份严格盲审；同一协调者且行为可暗示方法，不是独立人工审查。相同暴露任务族，仅一次执行；工具数量和上下文同时变化，不能单独识别中介原因。保留全部失败、原评分及费用。课程最终综合报告、复现材料及展示仍需完成，不能代替严格双提升。</p>
 <ul>{''.join(f'<li><a href="../{path}">{label}</a></li>' for label,path in links)}</ul></html>'''
 (ROOT/'reports/capability-withdrawal-development.html').write_text(doc)
 print('reports/capability-withdrawal-development.html')
if __name__=='__main__':main()
