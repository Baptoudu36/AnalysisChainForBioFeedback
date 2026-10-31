"""File-only entry to the existing OpenCV selector; never loads a model or acquires data."""
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'1stProject-SquatJump'))
from detector import load_config,review_events
from mechanics import calculate_metrics
from report import write_report,make_annotated_video

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--session',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
 a=p.parse_args();source=a.session.resolve();dest=a.out.resolve()
 if dest.exists() or dest==source or dest.is_relative_to(source):p.error('Choose a new output directory outside the source session.')
 proposal=json.loads((source/'results.json').read_text());video=source/'recording.mp4';timestamps=source/'timestamps.csv'
 dest.mkdir(parents=True,exist_ok=False)
 pending={'ok':False,'review_status':'pending','analysis_status':'REVIEW_REQUIRED','automatic_proposal':proposal,'source_session':source.name,'source_kind':'historical export; method retained in proposal'}
 write_report(dest,pending,None)
 result=review_events(video,timestamps,load_config(ROOT/'1stProject-SquatJump/config.json'),proposal)
 result.update(body_mass_kg=proposal['body_mass_kg'],push_off_distance_cm=proposal['push_off_distance_cm'],source_session=source.name,source_kind='historical export; method retained in proposal')
 annotated=None
 if result.get('ok'):
  result.update(calculate_metrics(result['flight_time_s'],result['body_mass_kg'],result['push_off_distance_cm']/100))
  annotated=dest/'annotated_review.mp4';make_annotated_video(str(video),annotated,result)
 write_report(dest,result,annotated)
 print(json.dumps(result,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
