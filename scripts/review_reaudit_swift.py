"""Static SwiftUI explanation review with recorded, non-executing type checks."""
import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'results/evidence/unified-reaudit-20261102/historical-products/tool-migration-pilot-20261031'
CHECK=ROOT/'results/evidence/unified-reaudit-20261102/swift-static-checks'


def main():
 assert 'opaque return type' in (CHECK/'CardView.log').read_text()
 assert "has no member 'onDelete'" in (CHECK/'ListDelete.log').read_text()
 assert not (CHECK/'CounterView.log').read_text()
 for f in sorted(P.glob('cell-*.json')):
  d=json.loads(f.read_text());a=d['answer'];blocks=re.findall(r'```(?:swift|Swift)\n(.*?)```',a,re.S)
  assert '@State private var count = 0' in a and 'count += 1' in a
  props={'declarative_explanation':'pass','swiftui_state_mapping':'pass','concrete_examples':'fail' if f.stem in ['cell-010','cell-012'] else 'pass'}
  note='Counter and state/binding/composition examples illustrate declared UI from state. Surrounding model types and app callbacks are illustrative placeholders; separate snippets are not one compilable app. Counter control typechecked successfully, others statically reviewed.'
  if f.stem=='cell-010':
   note='Exact generated CardView block plus import fails Swift6.3.3 typecheck: opaque stored closure property has no initializer for underlying type. The exact invalid declaration also occurs in native get_symbol_details response; source content defect propagated to output. Other counter/binding examples remain useful.'
   assert any('@ViewBuilder let content: () -> some View' in json.dumps(c['result']) for c in d['calls'])
  elif f.stem=='cell-012':note='Deletion example attaches onDelete directly to List; concrete minimal reproducer fails because List has no onDelete member. Modifier belongs on DynamicViewContent such as ForEach. Ellipsis/data placeholders expanded only in reproducer; not claimed exact full-answer compilation.'
  r={'cell_id':f.stem,'task_id':430,'input_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'trace_sha256':d['trace_sha256'],'properties':props,'core_pass':all(v=='pass' for v in props.values()),'evidence':{'declarative_explanation':'Explains desired result/relationships versus explicit control flow with non-UI examples; acknowledges imperative event handlers.','swiftui_state_mapping':'Maps View/body, State and bindings/collections to state-driven UI rather than manual widget mutation.','concrete_examples':note},'swift_blocks':len(blocks),'review_phase':'supplemental_posthoc_scores_exposed','review_source':'scripts/review_reaudit_swift.py','compiler':'Apple Swift6.3.3 swiftlang-6.3.3.1.3;arm64-apple-macosx26.0','primary_references':['https://developer.apple.com/documentation/SwiftUI/State','https://developer.apple.com/documentation/swiftui/dynamicviewcontent/ondelete(perform:)','https://docs.swift.org/compiler/documentation/diagnostics/opaque-type-inference'],'limitations':['Typecheck only; no generated program executed.','No full runnable app or deployment requirement added.','Same coordinator with historical scores exposed; not independent validation.','Teaching snippets may omit imports/model definitions; concrete type errors distinguished from placeholders.']}
  (P/'reviews'/f.name).write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
 statuses={'CardView':1,'CounterView':0,'ListDelete':1}
 (CHECK/'results.json').write_text(json.dumps({'compiler':'Apple Swift6.3.3 swiftlang-6.3.3.1.3; arm64-apple-macosx26.0','mode':'typecheck_only','statuses':statuses,'logs':{n:hashlib.sha256((CHECK/(n+'.log')).read_bytes()).hexdigest() for n in statuses},'generated_code_executed':False},indent=2)+'\n')
 print('6 SwiftUI reviews')


if __name__=='__main__':main()
