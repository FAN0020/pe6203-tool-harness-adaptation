"""Review six historical daily/card outputs against preserved native responses."""
import base64
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'results/evidence/unified-reaudit-20261102/historical-products/daily-migration-pilot-20261031'


def main():
 for f in sorted(P.glob('cell-*.json')):
  d=json.loads(f.read_text());a=d['answer'];calls=d['calls']
  card_call=next(c for c in calls if c['tool'].startswith('get_card_by_id'))
  card=json.loads(card_call['result']['content'][0]['text'])['result'][0]
  assert card['id']==89631139 and card['data']['atk']==3000 and card['data']['def']==2500 and card['data']['level']==8
  im=next(c for c in calls if c['tool'].startswith('get_card_image'))
  b=next(x for x in im['result']['content'] if x['type']=='image');image_bytes=base64.b64decode(b['data'],validate=True)
  digest=hashlib.sha256(image_bytes).hexdigest();assert digest=='1b4c4386204b94760fe2082ca5dd379230931bd2cdd1953723e9974ddec26cb0'
  assert json.loads(im['arguments'])['id'] in [89631139,'89631139'] and b['mimeType']=='image/jpeg'
  daily=next(c for c in calls if c['tool'].startswith(('get_problem','get_daily_challenge')))
  daily_json=json.loads(daily['result']['content'][0]['text']);question=daily_json['problem']['question']
  assert daily_json['date']=='2026-10-31' and question['questionFrontendId']=='3665' and question['title']=='Twisted Mirror Path Count'
  assert all(v in a for v in ['89631139','3000','2500','3665','Twisted Mirror Path Count'])
  props={'card_details':'fail' if f.stem=='cell-008' else 'pass','image_retrieval':'pass','daily_challenge':'fail' if f.stem=='cell-005' else 'pass'}
  evidence={'card_details':'Correct name,identity,type,level,ATK/DEF and lore match archived details.' if f.stem!='cell-008' else 'Mislabels setcode221 as card password; password is89631139. Other main card fields match.',
   'image_retrieval':'Correct-ID native response contains valid64036-byte JPEG; same SHA across6. Coordinator visually inspected card name,8stars,ATK3000/DEF2500. User-interface display itself not established.',
   'daily_challenge':'Archived daily date,title,number,difficulty and problem description match.' if f.stem!='cell-005' else 'Correct daily identity, but final adds initial heading-right restriction absent from statement; both initial right/down paths are allowed. Other summary/hints largely faithful.'}
  r={'cell_id':f.stem,'task_id':90,'input_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'trace_sha256':d['trace_sha256'],'properties':props,'core_pass':all(v=='pass' for v in props.values()),'evidence':evidence,'image_sha256':digest,'review_phase':'supplemental_posthoc_scores_exposed','review_source':'scripts/review_reaudit_daily.py','limits':['Same coordinator; original scores exposed.','Historical date assessed from contemporaneous archived native response, not todays live problem.','No requirement to write a presentation or solve daily problem added.','Image display in original UI not certified; successful retrieval is original requirement.']}
  (P/'reviews'/f.name).write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
 print('6 daily/card reviews')


if __name__=='__main__':main()
