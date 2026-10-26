"""Check current proposals against retained baseline scores; no model or GUI is loaded."""
from pathlib import Path
import sys,json,tempfile
from unittest.mock import patch
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'1stProject-SquatJump'))
import detector

class ScoredFrames:
    def __init__(self,n):self.n=n;self.i=0
    def isOpened(self):return True
    def read(self):
        self.i+=1
        return (True,np.zeros((10,10,3),dtype=np.uint8)) if self.i<=self.n else (False,None)
    def release(self):pass

class StoredScores:
    def __init__(self,scores):self.it=iter(scores)
    def decision_function(self,_):return np.array([next(self.it)])

data=json.loads((ROOT/'evidence/reproduction/jump/baseline/output/dashboard_data.json').read_text())
cfg=json.loads((ROOT/'1stProject-SquatJump/config.json').read_text())
cfg['model_path']=str(Path(__file__).resolve()) # Existing file; load is mocked below.
assert len(data['scores'])==20
(ROOT/'outputs').mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix='biofeedback-scores-',dir=ROOT/'outputs') as tmp:
    absent=str(Path(tmp)/'absent_timestamps.csv')
    for trial,scores in data['scores'].items():
        with patch('joblib.load',return_value=StoredScores(scores)),patch.object(detector.cv2,'VideoCapture',return_value=ScoredFrames(len(scores))):
            proposal=detector.detect_events('stored-score-fixture',absent,cfg)
        expected=next(r for r in data['lovo'] if r['trial']==trial)
        assert [proposal['takeoff_frame_index'],proposal['landing_frame_index']]==[expected['det_takeoff'],expected['det_landing']],trial
        assert proposal['review_status']=='required',trial
        pending=detector.review_events('unused',absent,cfg,proposal,reviewer=lambda *a,**k:dict(ok=False,message='No human review performed in this test'))
        assert not pending['ok'] and pending['review_status']=='pending' and 'jump_height_m' not in pending,trial
print('20/20 retained baseline event pairs preserved; 20/20 require review.')
