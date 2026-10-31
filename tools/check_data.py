"""Read-only submission checks using the Python standard library; no model loading."""
from pathlib import Path
import csv,json,hashlib,math,re
from urllib.parse import unquote
ROOT=Path(__file__).resolve().parents[1]
def main():
 checks=[]
 def check(name,ok):
  checks.append((name,bool(ok)))
  if not ok:print('FAIL:',name)
 for session in sorted((ROOT/'1stProject-SquatJump/jump_data').iterdir()):
  j=json.loads((session/'results.json').read_text());ts=list(csv.DictReader((session/'timestamps.csv').open()))
  vals=[int(x['sensor_timestamp_ns']) for x in ts];t=(j['landing_frame_index']-j['takeoff_frame_index'])/60
  check(session.name+' flight formula',math.isclose(t,j['flight_time_s'],abs_tol=1e-12))
  check(session.name+' height formula',math.isclose(9.81*t*t/8,j['jump_height_m'],abs_tol=1e-12))
  check(session.name+' increasing timestamps',all(y>x for x,y in zip(vals,vals[1:])))
  check(session.name+' recorded fallback',len(vals)!=j['frames_decoded'] and j['timestamp_source']=='nominal_frame_rate_fallback')
  c={x['metric']:x['value'] for x in csv.DictReader((session/'results.csv').open())}
  check(session.name+' CSV/JSON',all(str(j[k])==v for k,v in c.items()))
 check('7 recovered sessions',len(list((ROOT/'1stProject-SquatJump/jump_data').iterdir()))==7)
 check('20 training videos',len(list((ROOT/'1stProject-SquatJump/training_dataset').glob('*.mp4')))==20)
 for row in csv.DictReader((ROOT/'docs/jump_delivery_manifest.csv').open(encoding='utf-8')):
  f=ROOT/row['destination'];check('delivery '+row['member'],f.is_file() and hashlib.sha256(f.read_bytes()).hexdigest()==row['sha256'])
 for f in ROOT.rglob('*.md'):
  if any(x in f.parts for x in ['outputs','.venv','evidence']):continue
  for target in re.findall(r'\]\(([^)]+)\)',f.read_text(encoding='utf-8')):
   target=target.strip('<>').split('#')[0]
   if not target or re.match(r'[a-z]+:',target):continue
   check('link '+str(f.relative_to(ROOT))+' -> '+target,(f.parent/unquote(target)).exists())
 manifest=ROOT/'docs/SUBMISSION_MANIFEST.csv'
 if manifest.exists():
  for row in csv.DictReader(manifest.open(encoding='utf-8')):
   f=ROOT/row['path'];check('package '+row['path'],f.is_file() and hashlib.sha256(f.read_bytes()).hexdigest()==row['sha256'])
 print(json.dumps({'checks':len(checks),'passed':sum(x[1] for x in checks),'failed':sum(not x[1] for x in checks)}))
 return 0 if all(x[1] for x in checks) else 1
if __name__=='__main__':raise SystemExit(main())
