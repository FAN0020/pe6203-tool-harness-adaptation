import json,html,shutil
from pathlib import Path
S=Path(__file__).resolve().parents[1];R=S.parent
m=json.loads((S/'evidence/recomputed/metrics.json').read_text());p=json.loads((R/'experiments/course-completion-plan.json').read_text())
(S/'history-reports').mkdir(exist_ok=True)
for name in ['selective-strategy-search.html','experiment-readiness.html','course-v1.3-experiment.html']:
 shutil.copy2(R/'reports'/name,S/'history-reports'/name)
url='https://docs.google.com/presentation/d/1vcofhraTu_EJuhCm45WDVUMQzRFrY36T/edit'
style='<style>body{max-width:1100px;margin:30px auto;padding:24px;font:17px/1.65 system-ui;color:#172333}h1,h2{color:#245071}table{width:100%;border-collapse:collapse}td,th{border:1px solid #c5d3e0;padding:10px;text-align:left;vertical-align:top}th{background:#edf3f8}a{color:#15568c}small{color:#526579}</style>'
rows=''.join('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in [x['method'],f"{x['TF']:.4f}",f"{x['PE']:.4f}",f"{x['ECS_population']:.4f}",f"{x['ECS_sample']:.4f}",str(x['completion']['completed'])+'/9'])+'</tr>' for x in m['strategy_means'])
req=[]
for r in p['requirements']:
 status=r['status'];remaining=r.get('remaining','');evidence=r.get('evidence','')
 if '10分钟' in r['requirement']:
  status='内容已写入共享演示并逐页检查；待团队审阅/排练';remaining='正文1–13页规划10分钟，14–16页Q&A；重复模板页已按用户授权替换，保留团队开场与蓝白版式。';evidence='共享演示16页、讲稿和逐页检查记录；尚无组内排练证据'
 if '配置' in r['requirement']:
  status='独立复算与证据包已准备';remaining='以 package-verification.json 中的独立解包验证为准。'
 if 'GitHub' in r['requirement']:
  status='本地交付包已准备；待团队审核和正式提交'
 req.append('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in [r['ref'],r['requirement'],status,evidence,remaining])+'</tr>')
text=f'''<!doctype html><html lang="zh"><meta charset="utf-8"><title>PE6203 交付审阅</title>{style}<h1>PE6203 课程交付审阅</h1><p><strong>主实验复用完成；严格 under-update / over-update 案例缺口仍保留。未启动新实验，新增模型API费用 $0。</strong></p>
<h2>审阅材料</h2><ul><li><a href="PE6203-report.pdf">报告 PDF（13页）</a> / <a href="report.html">HTML 阅读版</a></li><li><a href="{url}">现有共享演示：已写入正文与Q&A</a> / <a href="speaker-notes.html">讲稿与时长</a></li><li><a href="PE6203-submission.zip">本地可复现包</a> / <a href="RUNBOOK.html">离线复算与未来获批复现命令</a></li><li><a href="evidence/recomputed/cells.csv">27格逐格结果</a> / <a href="evidence/recomputed/metrics.json">完整独立计算</a></li><li><a href="evidence/failure-cases.json">72个候选及9个详细案例</a> / <a href="evidence/trajectory-inventory.csv">317条原始轨迹索引</a></li><li><a href="diagnostic-options.html">最多4条的可选诊断方案（未批准、未执行）</a></li></ul>
<h2>已核验的主结果</h2><table><tr><th>Strategy</th><th>TF</th><th>PE</th><th>ECS总体</th><th>ECS样本</th><th>正常完成</th></tr>{rows}</table><p>Selective Patch九个PE按task133、235、283的Early/Middle/Late排列：<strong>10,8,7 / 10,10,10 / 9,9.4,8.6</strong>。总和82，均值82/9＝9.1111。20条正常完成、5条轮数耗尽、2条输出截断；全部27条保留评分。Full Rewrite更新177974 tokens、203.508秒、$0.049176082；Patch更新0 tokens、1.145秒、$0，与No Update的API成本并列。主实验已知总费用$0.40691929208，另有1次未知费用请求。</p>
<h2>逐项要求与缺口</h2><table><tr><th>Brief</th><th>要求</th><th>状态</th><th>已有证据</th><th>剩余事项</th></tr>{''.join(req)}</table>
<h2>已有证据如何复用</h2><p>27条主实验直接作为正文；108条历史确认（原三方法81条、各3次）保留为独立补充材料，不混算。60条开发、旧A/B、R2/R3部分结果、失败与未知账单全部保留。六条回退诊断为有效负结果；其中3个回答年度总额错误但judge仍给10/10，原评分不改。</p><ul><li><a href="history-reports/selective-strategy-search.html">历史研究：成功、失败与成本</a></li><li><a href="history-reports/experiment-readiness.html">旧A/B结果</a></li><li><a href="history-reports/course-v1.3-experiment.html">原主实验报告（保持原文）</a></li></ul><p>历史网页中的仓库相对链接可能需要解压对应归档后定位；证据身份以manifest和原始路径为准。</p>
<h2>最小剩余行动与停止条件</h2><p>P0已核验并冻结主结果。P1报告和复现包交付审阅。P2已有317条结构筛查、72候选分类及9个详细案例。P3仅提出具体两臂诊断，尚未授权；推荐先确认课程接受的案例范围。P4团队确认共享演示、贡献说明和10分钟排练，预计团队审阅/排练30–60分钟，API成本$0。可选4条诊断估计6–16分钟、$0.03–$0.10，需单独批准；若结果不支持假设也停止。任何新增模型调用、诊断、Netlify部署或扩展均不自动执行。</p><p>不要求Patch超过所有baseline，不把PE+0.5或历史统计晋升阈值当课程门槛。不声明严格失败分析已满足；最终提交需团队审阅及授权。</p></html>'''
(S/'index.html').write_text(text)
(S/'.context/delivery-status.json').write_text(json.dumps({'main_verified':True,'new_model_calls':0,'new_api_usd':0,'new_experiments_authorized':False,'diagnostics_proposed_max_trajectories':4,'natural_selective_under_update_confirmed':False,'natural_selective_over_update_confirmed':False,'presentation_url':url,'presentation_content_slides':16,'template_pages_pending_collaboration':0,'submission_performed':False},indent=2)+'\n')
# Include opening notes alongside imported content notes.
n=json.loads((S/'.context/speaker-notes.json').read_text())
opening=[(1,'Introduction',20,'Introduce the team, recovery and retention, and the fixed 27-trajectory comparison.'),(2,'Research problem',40,'Explain stale tool knowledge and the recovery/retention questions. A newly required parameter can invalidate an old call.'),(3,'Three adaptation strategies',30,'No Update retains Early knowledge. Full Rewrite rebuilds records and rewrites descriptions. Selective Patch updates affected records. Same execution agent; scope and generation mechanism both differ.')]
notes='<h2>Preserved team opening slides</h2>'+''.join(f'<h3>{i}. {t}: {sec} seconds</h3><p>{body}</p>' for i,t,sec,body in opening)
f=S/'speaker-notes.html';h=f.read_text()
if '<h2>Preserved team opening slides</h2>' not in h:
 h=h.replace('<h2>4.',notes+'<h2>4.');f.write_text(h)
