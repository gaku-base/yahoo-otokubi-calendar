import importlib.util,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];S=ROOT/'scripts'
if str(S) not in sys.path:sys.path.insert(0,str(S))
spec=importlib.util.spec_from_file_location('scrape_v075',S/'scrape_v075.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def rec(status,failed=0,succeeded=50,stores=6000,audit=0,conf=0):
    return {'status':status,'diagnostics':{'categories_failed':failed,'categories_succeeded':succeeded,'stores_total':stores,'category_option_audit':{'issues':[{}]*audit},'multi_rate_conflicts':[{}]*conf}}

def test_only_non_ok_days_need_recovery():
    assert not m.needs_recovery(rec('ok'));assert m.needs_recovery(rec('partial'));assert m.needs_recovery(rec('fetch_error'))

def test_ok_retry_always_beats_partial_initial():
    assert m.choose_better(rec('partial',1,49,5999),rec('ok',0,50,6702))['status']=='ok'

def test_better_partial_prefers_fewer_failures_then_more_stores():
    a=rec('partial',2,48,5000);b=rec('partial',1,49,5900);assert m.choose_better(a,b) is b
    a=rec('partial',1,49,5000);b=rec('partial',1,49,5900);assert m.choose_better(a,b) is b

def test_audit_and_conflict_penalize_same_status():
    clean=rec('partial',1,49,5000,0,0);dirty=rec('partial',1,49,6000,1,0);assert m.choose_better(dirty,clean) is clean

def test_recovery_attempt_limit_is_bounded():assert m.RECOVERY_ATTEMPTS==2
