"""Verify narrow observation/call facts offline; no tool replay or model invocation."""
import hashlib
import json
import re
import tarfile
from collections import Counter
from decimal import Decimal
from pathlib import Path

from raw_cell_verifier import archive_files

HERE = Path(__file__).resolve().parent


def main():
    sources = json.loads((HERE / 'upstream-source-manifest.json').read_text())
    archive = HERE / 'upstream-source.tar.gz'
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == sources['archive_sha256']
    with tarfile.open(archive) as source_archive:
        for item in sources['files']:
            assert hashlib.sha256(source_archive.extractfile(item['file']).read()).hexdigest() == item['sha256']
    files, manifest = archive_files(HERE)
    prefix = manifest['prefix'] + '/'

    def trace(cid):
        return json.loads(files[prefix + f'cells/{cid}/run/raw_trace.json'])

    def calls(cid):
        return [e for e in trace(cid)['events'] if e['type'] == 'tool_result']

    def args(e):
        return json.loads(e['call']['function']['arguments'])

    def tool(e):
        return e['call']['function']['name']

    def text(e):
        return '\n'.join(c.get('text', '') for c in e['result'].get('content', []))

    sp = calls('cell-002')
    listing = next(e for e in sp if tool(e).startswith('list_tasks__'))
    ids = re.findall(r'ID: ([a-f0-9-]{36})', text(listing))
    assert len(ids) == 55 and len(set(ids)) == 30
    assert 'Total: 55 tasks' in text(listing)
    created_before = [e for e in sp if e['round'] <= listing['round']
                      and tool(e).startswith(('create_task__', 'create_subtask__'))
                      and not e['result'].get('isError')]
    assert len(created_before) == 30
    bf = calls('cell-005')
    failed = [e for e in bf if e['result'].get('isError')]
    assert len(failed) == 7
    repairs = []
    for f in failed:
        a = args(f)
        recovered = [e for e in bf if e['round'] > f['round']
                     and args(e).get('name') == a['name'] and not e['result'].get('isError')]
        assert len(recovered) == 1
        b = args(recovered[0])
        delta = {k: [a.get(k), b.get(k)] for k in set(a) | set(b) if a.get(k) != b.get(k)}
        assert a['parentId'] == 'fb1f061d-8a0e-411b-9051-fc9def02e2c6'
        assert b['parentId'] == 'fb1f061d-8a0e-441b-9051-fc9def02e2c6'
        repairs.append({'name': a['name'], 'failed_round': f['round'],
                        'recovered_round': recovered[0]['round'], 'argument_changes': delta})
    assert not trace('cell-002')['answer'] and not trace('cell-005')['answer']
    charts = []
    for cid in ('cell-001', 'cell-006'):
        events = calls(cid)
        assert len(events) == 3 and not any(e['result'].get('isError') for e in events)
        area = args(next(e for e in events if tool(e).startswith('generate_area_chart__')))
        values = [Decimal(str(x['value'])) for x in area['data']]
        expected = list(map(Decimal, ['1.2', '1.1', '1.4', '1.6', '1.8', '2.1',
                                      '2.3', '2.2', '2.5', '2.7', '3', '3.5']))
        assert values == expected and '百万元' in area['axisYTitle']
        districts = args(next(e for e in events if tool(e).startswith('generate_district_map__')))['data']
        assert districts['dataValueUnit'] == '百万元'
        assert [Decimal(x['dataValue']) for x in districts['subdistricts']] == list(map(Decimal, ['15.8','12.3','9.7','8.4','7.2']))
        columns = args(next(e for e in events if tool(e).startswith('generate_column_chart__')))
        assert [Decimal(str(x['value'])) for x in columns['data']] == list(map(Decimal, ['6.2','4.8','4.5','3.9','5.1','3.6']))
        assert columns['group'] and '百万元' in columns['axisYTitle']
        dips = [i+1 for i in range(1,len(values)) if values[i] < values[i-1]]
        assert sum(values) == Decimal('25.4') and dips == [2,8]
        charts.append({'cell_id':cid, 'all_original_values_and_units_retained':True,
                       'monthly_total':str(sum(values)), 'dip_months':dips})
    answer = trace('cell-006')['answer']
    assert '23.4' in answer and 'Only one dip' in answer
    math_events = calls('cell-004')
    code_analysis = [e for e in math_events if tool(e).startswith('code-analysis-prompt-builder__')]
    assert len(code_analysis) == 1 and not code_analysis[0]['result'].get('isError')
    print(json.dumps({'new_model_calls':0, 'generated_code_executed':False,
        'sp_hierarchy':{'round':listing['round'],'reported_total':55,'displayed_ID_instances':len(ids),
                        'distinct_IDs':len(set(ids)),'successful_creations_so_far':len(created_before),
                        'duplicate_ID_counts':dict(Counter(ids)),
                        'source_explanation':'getTasks without parentId returns every task; getTaskHierarchy recurses into children, repeating them. See archived iter3 file-storage.js and list-tasks.js.'},
        'bf_parent_id_recoveries':repairs,'planning_final_answers_empty':True,
        'charts':charts,'sp_chart_summary':{'claimed_total':'23.4','actual_total':'25.4',
                                          'claimed_one_dip':True,'actual_dip_months':[2,8]},
        'bf_math_code_analysis_tool':{'calls':1,'successful':True,'retried':False},
        'limits':'Static/data checks only; chart rendering and full security verification remain unknown.'},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
