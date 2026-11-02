"""Build a condition-level evaluation report from newly replayed evidence."""
import csv
import hashlib
import json
import statistics
import subprocess
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
E = ROOT/'results/evidence'
OLD = E/'unified-reaudit-20261102'
TOP5 = {'sufficiency_feedback', 'observed_contract', 'discovery_contract', 'budget_feedback', 'shared_contract_refs'}
SLUGS = ['evidence-dictionary', 'evidence-contrastive', 'capability-consolidation',
         'relational-probe-memory', 'pruned-episode-memory', 'capability-relation-matrix']

def read(p):
    return json.loads(p.read_text())

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def write(name, data):
    (HERE/name).write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')

def csv_write(name, rows):
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with (HERE/name).open('w') as f:
        w = csv.DictWriter(f, fieldnames=keys, lineterminator='\n')
        w.writeheader()
        w.writerows({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict,list)) else v
                    for k,v in r.items()} for r in rows)

def stats(rows):
    executed = [r for r in rows if r['execution_status'] != 'not_started']
    reviewed = [r for r in executed if r.get('core_pass') is not None]
    scored = [r for r in executed if r.get('TF') is not None and r.get('PE') is not None]
    cost = sum((Decimal(r.get(k, '0')) for r in rows
                for k in ('actor_known_usd', 'judge_known_usd')), Decimal(0))
    return {'planned':len(rows), 'executed':len(executed),
            'completed':sum(r['execution_status']=='completed' for r in executed),
            'core_pass':sum(r['core_pass'] for r in reviewed), 'product_reviewed':len(reviewed),
            'valid_rating_slots':sum(r['judge_slots'] for r in rows),
            'scored_cells':len(scored),
            'TF':statistics.mean(r['TF'] for r in scored) if len(scored)==len(rows) and rows else None,
            'PE':statistics.mean(r['PE'] for r in scored) if len(scored)==len(rows) and rows else None,
            'tool_outer_errors':sum(r.get('tool_outer_errors',0) for r in rows),
            'tool_calls':sum(r.get('tool_calls',0) for r in rows),
            'transport_events':(sum(r.get('transport_events',0) for r in rows) if all(r.get('transport_events',0) is not None for r in rows) else None),
            'actor_judge_known_usd':str(cost),
            'unknown_cost_cells':sum(r.get('result_unknown_cost',False) for r in rows)}

def pairs(rows):
    groups=defaultdict(lambda: defaultdict(list))
    for r in rows:
        groups[(r['cohort'], r['task_id'], r['stage'])][r['strategy']].append(r)
    output=[]
    for (cohort,task,stage),arms in sorted(groups.items()):
        if 'selective_patch' not in arms:
            continue
        for name,values in arms.items():
            if name in {'selective_patch','no_update','full_rewrite'}:
                continue
            providers=sorted({k for r in values+arms['selective_patch'] for k in r.get('actor_providers',{})})
            row={'cohort':cohort,'task_id':task,'stage':stage,'candidate':name,
                 'condition_class':values[0]['condition_class'],
                 'input_condition_eligible':task!=377,'actual_actor_providers':providers}
            for prefix,vs in [('SP', arms['selective_patch']), ('candidate',values)]:
                row.update({prefix+'_'+k:v for k,v in stats(vs).items()})
            row['paired_execution_coverage'] = ('complete' if all(row[a+'_executed']==row[a+'_planned'] for a in ('SP','candidate')) else 'incomplete')
            output.append(row)
    return output

def main():
    replay=read(HERE/'registry-replay.json')
    assert replay['integrity_pass'] and not replay['errors']
    assert read(HERE/'prior-five.json')['offline_integrity_pass']
    registry=read(HERE/'registry-cells.json')
    historical_pairs=pairs(registry)
    saved_pairs=read(OLD/'pairwise-comparison.json')
    lookup={(r['cohort'],r['task_id'],r['stage'],r['candidate']):r for r in historical_pairs}
    for saved in saved_pairs:
        fresh=lookup[(saved['cohort'],saved['task_id'],saved['stage'],saved['candidate'])]
        for k,v in fresh.items():
            if k in saved:
                assert v==saved[k], (k,v,saved[k],saved['cohort'])
    maturity=read(OLD/'candidate-maturity.json')
    for r in maturity:
        selected=[v for v in registry if v['strategy']==r['candidate'] and v['status']!='not_started']
        assert len(selected)==r['executed']
        assert sum(v['core_pass'] is not None for v in selected)==r['products_reviewed']
    csv_write('candidate-maturity-36.csv', maturity)
    csv_write('historical-pairs.csv', historical_pairs)
    top_pairs=[r for r in historical_pairs if r['candidate'] in TOP5]
    saved_keys={(r['cohort'],r['task_id'],r['stage'],r['candidate']) for r in saved_pairs}
    added=[r for k,r in lookup.items() if k not in saved_keys]
    assert len(added)==55 and all(min(r['SP_executed'],r['candidate_executed'])==0 for r in added)
    assert len(top_pairs)==80  # 64 historical paired conditions + 16 with an unexecuted arm.
    csv_write('top5-pairs.csv',top_pairs)
    rounds=[]
    sources=[]
    for slug in SLUGS:
        saved=E/(slug+'-20261102')/'trial-verification.json'
        p=HERE/(slug+'.json') if slug=='capability-relation-matrix' else saved
        d=read(p)
        assert d==read(saved) and d['integrity_verified'] and not d['development_pass']
        rounds.append(d)
        sources.append(saved)
    partial=read(HERE/'relation-witness-basis.json')
    saved=E/'relation-witness-basis-20261102/verification-at-stop.json'
    assert partial==read(saved) and partial['integrity_verified'] and not partial['development_complete']
    rounds.append(partial)
    sources.append(saved)
    updater_ledger=ROOT/'results/raw/relational-probe-memory-updater-costs-20261102/spend-ledger.json'
    updater=read(updater_ledger)
    assert len(updater['requests'])==3 and all(r['status']=='settled' for r in updater['requests'])
    updater_cost=sum((Decimal(r['actual_usd']) for r in updater['requests']),Decimal(0))
    assert updater_cost==Decimal('0.004804392')
    sources.append(updater_ledger)
    for d in rounds:
        d['evaluation_known_usd']=d['known_usd']
        d['updater_known_usd']=str(updater_cost if d['candidate']=='relational_probe_memory' else Decimal(0))
        d['whole_round_known_usd']=str(Decimal(d['known_usd'])+Decimal(d['updater_known_usd']))
    normalized=[]
    for d in rounds:
        for r in d['rows']:
            costs=r.get('cost_usd',{})
            normalized.append({**r, 'cohort':d['candidate']+'-20261102',
                'condition_class':'original_benchmark',
                'judge_slots':r.get('judge_slots',5 if r['TF'] is not None else 0),
                'tool_outer_errors':r.get('tool_errors',0), 'transport_events':None,
                'actor_known_usd':costs.get('agent') or '0', 'judge_known_usd':costs.get('judge') or '0',
                'result_unknown_cost': r.get('cohort_status')=='judge_incomplete',
                'actor_providers':r.get('providers',{}).get('agent',{})})
    csv_write('recent-cells.csv',normalized)
    recent_pairs=pairs(normalized)
    csv_write('recent-pairs.csv',recent_pairs)
    assert len(normalized)==70 and sum(r['execution_status']!='not_started' for r in normalized)==69
    assert sum(r['judge_slots'] for r in normalized)==340
    receipt_sources=[OLD/'cost-receipts.json', OLD/'new-cost-receipts.json',
                     E/'additional-rounds-20261102/receipts-at-stop.json']
    receipts={}
    for p in receipt_sources:
        for r in read(p):
            assert r['id'] not in receipts, 'duplicate receipt across audit cohorts'
            receipts[r['id']]=Decimal(r['known_usd'])
    known=sum(receipts.values(), Decimal(0))
    assert len(receipts)==6386 and known==Decimal('8.6984822585')
    prototype=read(E/'relation-impact-closure-20261102/offline-prototype-manifest.json')
    assert all(sha(ROOT/p)==h for p,h in prototype['files'].items())
    assert prototype['model_calls']==0 and not prototype['model_protocol_frozen']
    suites=ET.parse(HERE/'pytest.xml').getroot()
    suites=list(suites) if suites.tag=='testsuites' else [suites]
    tests={k:sum(int(s.attrib[k]) for s in suites) for k in ('tests','errors','failures','skipped')}
    tests['seconds']=sum(float(s.attrib['time']) for s in suites)
    assert tests['tests']==729 and not any(tests[k] for k in ('errors','failures','skipped'))
    revision=subprocess.check_output(['git','rev-parse','5b772ff'],cwd=ROOT,text=True).strip()
    decision={'pipeline_revision':revision, 'branch':'codex/completion-quality-study',
       'generated_at_utc':datetime.now(timezone.utc).isoformat(),
       'registry_replay':{k:replay[k] for k in ('registered_candidates','cohorts','planned_cells','executed_cells','judge_slots','reviewed_products')},
       'tests':tests, 'recent_planned_cells':70, 'recent_executed_cells':69,
       'recent_fully_scored_cells':68,'recent_valid_judge_slots':340,'recent_product_reviews':69,
       'completed_recent_rounds':6, 'interrupted_recent_rounds':1, 'offline_only_prototypes':1,
       'decision':'reject_completed_versions_and_do_not_promote_incomplete_version',
       'goal_complete':False, 'new_model_calls':0, 'new_model_cost_usd':'0',
       'historical_priced_receipts':len(receipts),'historical_known_lower_bound_usd':str(known),
       'unknowns':'Four unresolved ledger requests, including latest timeout; early failed requests without IDs also remain unknown.',
       'limits':['Reuses prior product judgments; not an independent semantic re-review.',
                 'No new actor executions, judge sampling, or validation blocks.',
                 'Full test suite includes real local MCP services with mock model protocols; passing tests are not benchmark success.',
                 'Historical 36: 445 of 517 executed cells have mapped reviews; all executed candidate arms reviewed, some baseline arms remain unreviewed.',
                 'Latest cell-009 has no valid official rating; cell-010 has not run. No imputation.'],
       'sources':{str(p.relative_to(ROOT)):sha(p) for p in sources+receipt_sources},
       'rounds':[{'candidate':d['candidate'],'development_pass':d['development_pass'],
                  'judge_slots':d['judge_slots'],'evaluation_known_usd':d['evaluation_known_usd'],
                  'updater_known_usd':d['updater_known_usd'],'whole_round_known_usd':d['whole_round_known_usd'],
                  'failed_gates':[k for k,v in d.get('gates',{}).items() if not v],
                  'interruption_bound':d.get('gate_bound')} for d in rounds]}
    write('evaluation.json',decision)
    lines=['# 当前分支 evaluation', '',
      f'评测代码版本：`{revision}`；分支 `codex/completion-quality-study`。本次复算已有真实实验，没有重新采样 actor/judge，也没有新增模型费用。', '',
      '**结论：证据完整性与全分支测试通过，但尚无候选达到研究晋级要求。** 这两种“通过”必须分开。旧结果和旧结论未改写。', '',
      f'- 全测试：{tests["tests"]} passed，0 failed / error / skipped，{tests["seconds"]:.2f} 秒；包含真实本地 MCP 与模拟模型协议的集成测试。',
      '- 历史 36 候选：复算 45 个 cohort、775 个计划格、517 个已执行格、2555 个有效评分槽、445 份已有产物审查；0 原评分差异、0 知识锁差异。33 个有 actor 记录的候选自身产物均已审查；尚有 72 个历史对照格没有映射产物审查。',
      '- 最近 7 轮：6 轮完整，1 轮中断；69 条真实轨迹、68 条完整评分、340 个评分槽、69 份产物审查。另 1 个原型只做代码测试，不计作 benchmark 实验。', '',
      '## 最近版本：同题配对结果', '',
      '每项为 SP → 候选。133/283 合并同题 Middle/Late，235 为 Late；不跨题平均、不按单分排名。正常完成与完整产物通过各自计算，后者要求全部必要属性通过，未知不算通过。', '',
      '| 版本 | 干预任务 | 正常完成 | 完整产物 | TF | PE | 本轮已知费用 USD | 决定 |',
      '|---|---:|---|---|---|---|---:|---|']
    def fmt(x):
        return '缺失' if x is None else f'{x:.4f}'.rstrip('0').rstrip('.')
    for d in rounds:
        treated=283 if d['candidate'] in {'relational_probe_memory','pruned_episode_memory'} else 133
        ns=[r for r in normalized if r['cohort']==d['candidate']+'-20261102' and r['task_id']==treated]
        b,c=(stats([r for r in ns if r['strategy']==arm]) for arm in ('selective_patch',d['candidate']))
        incomplete=d is partial
        normal=f"{b['completed']}/{b['planned']} → {c['completed']}/{c['executed']}已运行；1未运行" if incomplete else f"{b['completed']}/{b['planned']} → {c['completed']}/{c['planned']}"
        core=f"{b['core_pass']}/{b['product_reviewed']} → {c['core_pass']}/{c['product_reviewed']}已审查" if incomplete else f"{b['core_pass']}/{b['planned']} → {c['core_pass']}/{c['planned']}"
        lines.append(f"| {d['candidate']} | {treated} | {normal} | {core} | {fmt(b['TF'])} → {fmt(c['TF'])} | {fmt(b['PE'])} → {fmt(c['PE'])} | {d['whole_round_known_usd']}{' + 未知' if incomplete else ''} | {'中断，晋级已不可能' if incomplete else '开发淘汰'} |")
    lines += ['', '中断行分母不同，只描述完成度，不作为完整配对均值比较；逐阶段结果见 CSV。`relation_witness_basis` 即使剩余133 Middle正常完成，也最多1/2，不能严格超过SP的1/2；保持题235完整产物SP1/1、候选0/1，亦未通过保持要求。缺失TF/PE和未运行产物仍为空。', '',
      '这轮复算不改变原语义判断。`observed_dictionary` 的133产物局部通过出现在截断轨迹；`observed_contrastive` 的完成收益未伴随完整产物改善；较高PE、正确原生调用或较少调用均不能替代最终交付。283/235在最近数学干预中知识与SP相同，其波动不能归因于该干预。', '',
      '## 比较文件与适用边界', '',
      '- [36候选评测层级](candidate-maturity-36.csv)：3个无actor结果的候选为workflow_notes、semantic_contract_closure、active_contract_probing；生成或准入失败不等于整类机制失败。',
      '- [Top 5逐条件配对表](top5-pairs.csv)：80行（64个旧配对条件，加16个至少一臂未执行的计划条件），明确sufficiency_feedback、observed_contract、discovery_contract、budget_feedback、shared_contract_refs及各cohort/版本，不合并同名不同版本。',
      '- [全部历史逐条件表](historical-pairs.csv)：227行含55个至少一臂未执行的计划条件；未执行不补成失败评分。原benchmark、带固定fixture的原题、受控合成各自标注；377不纳入可执行比较。部分早期cohort实际provider混用，不能与固定DigitalOcean试验合并归因。',
      '- [最近逐条件表](recent-pairs.csv)及[逐格表](recent-cells.csv)：分别列完成、全部必要产物属性、TF/PE、工具错误和成本，未运行/未评分保留缺失。最近轮次核验器未输出输运事件总数，该列留空，不补0。费用列为actor/judge已知费用；共享updater/preflight成本在轮次总费用中，不重复摊算。',
      '- [机器结果](evaluation.json)：失败门槛、样本数、文件哈希和限制。开发样本已暴露，不是未见任务或独立验证；ECS需要匹配三阶段，本次不凭Middle/Late补算。', '',
      '已有盲审偏差继续保留：relational_probe_memory最后2份曾有聚合分数暴露；capability_relation_matrix最后1份可能暴露方法，其10份均在分数解盲前。最新中断轮9份审查均在方法与分数解盲前封存。本次仅复算这些判断，不把同一协调者的复查称为独立盲审。', '',
      '## 中断与费用', '',
      '最新第9格actor已结束，首个judge请求120秒超时，无generation ID；五槽没有有效分数。原协议将该失败标为不可恢复；第10格尚未执行。冻结的unknown_charge停止规则与尚未批准的A3例外仍有效，本次没有重采评分、跳过收费停止或改写失败。', '',
      f'本次新增模型费用 **USD0**。历史去重 **6386** 笔已定价回执，已知费用下界 **USD{known}**；4笔ledger未知及早期缺ID失败请求仍保留，预留金额不当作实际费用。没有新增总费用上限。', '',
      '## 复算命令', '', '在仓库根目录运行；均不调用付费模型。旧脚本closure会重写相同内容的旧核验JSON，其他输出写入本目录。', '', '```bash',
      'uv run pytest -q --junitxml=results/evaluation/current-branch-5b772ff-20261102/pytest.xml',
      'uv run python scripts/verify_reaudit_closure.py',
      'uv run python results/evidence/capability-relation-matrix-20261102/verify_trial.py',
      'uv run python results/evidence/relation-witness-basis-20261102/verify_at_stop.py',
      'uv run python results/evaluation/current-branch-5b772ff-20261102/replay_registry.py',
      'uv run python results/evaluation/current-branch-5b772ff-20261102/summarize.py', '```', '',
      '前三个归档核验的stdout分别保存在prior-five.json、capability-relation-matrix.json、relation-witness-basis.json；独立错误日志为空。所有历史原始记录和实验源码保持原样。']
    (HERE/'REPORT.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'tests':tests,'historical_pairs':len(historical_pairs),'top5_pairs':len(top_pairs),
                      'recent_pairs':len(recent_pairs),'known_lower_bound_usd':str(known),'goal_complete':False},ensure_ascii=False))

if __name__=='__main__':
    main()
