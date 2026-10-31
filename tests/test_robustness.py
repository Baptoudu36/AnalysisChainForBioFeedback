from pathlib import Path
import sys, os, json, importlib.util, unittest, csv, contextlib, io, warnings
import tempfile
ROOT=Path(__file__).resolve().parents[1]
(ROOT/'outputs').mkdir(exist_ok=True)
TEMP=tempfile.TemporaryDirectory(prefix='biofeedback-tests-',dir=ROOT/'outputs')
RUN=Path(TEMP.name)
os.environ['MPLCONFIGDIR']=str(RUN/'mplconfig')
os.environ['PYTHONDONTWRITEBYTECODE']='1'
sys.path.insert(0,str(ROOT/'1stProject-SquatJump'))
import numpy as np
import detector
spec=importlib.util.spec_from_file_location('quality',ROOT/'2ndProject-ECGAnalyzer/analysis/ecg_signal_quality.py')
quality=importlib.util.module_from_spec(spec);spec.loader.exec_module(quality)
def strict(path):
    return json.loads(path.read_text(),parse_constant=lambda s:(_ for _ in ()).throw(ValueError(s)))
class Robustness(unittest.TestCase):
    def test_empty_rr(self):
        with warnings.catch_warnings(record=True) as caught:
            h=quality.hrv_time_domain(np.array([]))
        self.assertFalse(caught);self.assertEqual(h['n_rr'],0)
        for key in ['mean_rr_ms','mean_hr_bpm','min_hr_bpm','max_hr_bpm','sdnn_ms','rmssd_ms']:self.assertIsNone(h[key])
        json.dumps(h,allow_nan=False)
    def test_one_rr(self):
        h=quality.hrv_time_domain(np.array([.8]));self.assertEqual(h['mean_hr_bpm'],75)
        self.assertIsNone(h['sdnn_ms']);self.assertIsNone(h['rmssd_ms'])
    def test_two_rr(self):
        h=quality.hrv_time_domain(np.array([.8,.9]));self.assertAlmostEqual(h['sdnn_ms'],100/np.sqrt(2));self.assertAlmostEqual(h['rmssd_ms'],100)
    def test_invalid_rr(self):
        for bad in [0,-1,np.nan,np.inf]:
            h=quality.hrv_time_domain(np.array([.8,bad,.9]));self.assertIsNone(h['rmssd_ms']);self.assertIsNone(h['mean_hr_bpm']);json.dumps(h,allow_nan=False)
    def test_real_quality(self):
        for folder in (ROOT/'2ndProject-ECGAnalyzer/data').iterdir():
            dest=RUN/'quality'/folder.name
            with contextlib.redirect_stdout(io.StringIO()) as log:
                quality.main([str(folder),'--out',str(dest/'output'),'--fig-dir',str(dest/'figures')])
            (dest/'stdout.log').write_text(log.getvalue())
            result=strict(dest/'output/quality_metrics.json')
            if folder.name.startswith('20260916T101922'):
                self.assertEqual(result['hrv_time_domain']['n_rr'],0);self.assertIsNone(result['hrv_time_domain']['sdnn_ms'])
                self.assertGreater(result['spectrum']['band_power_fractions']['45-55 Hz'],.54)
            else:
                old=strict(ROOT/'2ndProject-ECGAnalyzer/analysis/output/quality_metrics.json')
                def compare(a,b):
                    for k,v in a.items():
                        if isinstance(v,dict):compare(v,b[k])
                        elif isinstance(v,(int,float)):self.assertAlmostEqual(v,b[k],delta=1e-9+abs(v)*1e-12,msg=k)
                compare(old,result)
    def test_short_signals(self):
        for n,fs in [(2,800),(10,800),(100,80),(100,800)]:
            dest=RUN/'fixtures'/f'short_{n}_{fs}';dest.mkdir(parents=True,exist_ok=True)
            np.savetxt(dest/'raw.csv',np.c_[np.arange(n)/fs,np.sin(np.arange(n)),np.full(n,500)],delimiter=',',header='time_s,raw_signal,raw_adc',comments='')
            (dest/'rr_intervals.csv').write_text('R_time_s,RR_s,in_configured_range\n')
            (dest/'metadata.json').write_text(json.dumps({'target_fs_hz':fs,'vref_v':3.3}))
            with contextlib.redirect_stdout(io.StringIO()):quality.main([str(dest),'--out',str(dest/'out'),'--fig-dir',str(dest/'figures')])
            data=strict(dest/'out/quality_metrics.json');self.assertEqual(data['timing']['samples'],n)
            if n<28 or fs<=80:self.assertIsNone(data['spectrum']['rms_bandpassed_v'])
    def test_zero_power(self):
        self.assertTrue(all(x is None for x in quality.band_power_fractions(np.array([0,50]),np.zeros(2)).values()))
    def test_invalid_raw(self):
        dest=RUN/'fixtures/invalid_raw';dest.mkdir(parents=True,exist_ok=True)
        (dest/'rr_intervals.csv').write_text('R_time_s,RR_s,in_configured_range\n')
        (dest/'metadata.json').write_text('{}')
        for content in ['0,1,500\n','0,1,500\n0,2,500\n','0,1,500\n1,nan,500\n']:
            (dest/'raw.csv').write_text('time_s,raw_signal,raw_adc\n'+content)
            with self.assertRaises(ValueError):quality.main([str(dest),'--out',str(dest/'out'),'--fig-dir',str(dest/'figures')])
    def sidecar(self,values):
        p=RUN/'fixtures/timestamps.csv';p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text('sensor_timestamp_ns\n'+'\n'.join(map(str,values))+'\n');return p
    def test_timestamp_sources(self):
        cases=[([], 'timestamps_missing_or_empty'),([0,1], 'timestamp_frame_count_mismatch'),([0,'nan',2,3], 'timestamp_invalid_or_nonfinite'),([0,'inf',2,3],'timestamp_invalid_or_nonfinite'),([0,2,1,4], 'timestamps_not_strictly_increasing'),([0,1,1,4],'timestamps_not_strictly_increasing')]
        for values,reason in cases:
            r=detector._event_timing(0,3,4,self.sidecar(values),{'expected_fps':60})
            self.assertEqual(r['timestamp_fallback_reason'],reason);self.assertEqual(r['timestamp_source'],'nominal_frame_rate_fallback');self.assertEqual(r['flight_time_s'],.05)
        r=detector._event_timing(0,3,4,self.sidecar([0,10000000,20000000,30000000]),{'expected_fps':60})
        self.assertEqual(r['flight_time_s'],.03);self.assertIsNone(r['timestamp_fallback_reason']);self.assertEqual(r['timestamp_alignment'],'unverified_physical_alignment')
    def test_invalid_indices_fps(self):
        p=self.sidecar([0,1,2,3])
        for a,b,n in [(-1,2,4),(0,4,4),(3,2,4),(0.5,2,4),(0,1,0)]:self.assertIsNone(detector._event_timing(a,b,n,p,{'expected_fps':60}))
        for fps in [0,-1,np.inf,np.nan,'bad']:self.assertIsNone(detector._event_timing(0,2,4,p,{'expected_fps':fps}))
    def test_review_decisions(self):
        p=RUN/'fixtures/absent.csv';cfg={'expected_fps':60}
        proposal={'ok':True,'takeoff_frame_index':227,'landing_frame_index':267,'frames_decoded':291,'event_score_margin':.316256}
        for a,b,status in [(227,267,'confirmed'),(144,172,'corrected')]:
            result=detector.review_events('unused',str(p),cfg,proposal,reviewer=lambda *args,**kwargs:dict(ok=True,takeoff_frame_index=a,landing_frame_index=b,frames_decoded=291))
            self.assertEqual(result['review_status'],status);self.assertEqual(result['automatic_proposal'],proposal);self.assertEqual(result['confirmed_events']['takeoff_frame_index'],a)
        r=detector.review_events('unused',str(p),cfg,proposal,reviewer=lambda *a,**k:dict(ok=False,message='cancelled'))
        self.assertFalse(r['ok']);self.assertNotIn('jump_height_m',r);self.assertEqual(r['review_status'],'pending')
    def test_run_analysis_pending(self):
        from unittest.mock import patch
        import main
        dest=RUN/'fixtures/pending';dest.mkdir(exist_ok=True)
        p={'ok':True,'takeoff_frame_index':227,'landing_frame_index':267,'frames_decoded':291}
        with patch.object(main,'detect_events',return_value=p),patch.object(main,'review_events',return_value={'ok':False,'review_status':'pending','automatic_proposal':p}),patch.object(main,'calculate_metrics') as calc:
            main.run_analysis('unused','unused',dest,66,31,{'expected_fps':60});calc.assert_not_called()
        self.assertEqual(strict(dest/'results.json')['automatic_proposal'],p)
if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Robustness))
    (RUN/'python_test_results.json').write_text(json.dumps({'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'successful':result.wasSuccessful()},indent=2))
    sys.exit(not result.wasSuccessful())
