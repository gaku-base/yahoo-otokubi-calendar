import asyncio,importlib.util,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];S=ROOT/'scripts'
if str(S) not in sys.path:sys.path.insert(0,str(S))
spec=importlib.util.spec_from_file_location('scrape_v075',S/'scrape_v075.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def rec(status,failed=0,succeeded=50,stores=6000,audit=0,conf=0,warnings=0):
    return {'status':status,'diagnostics':{'categories_failed':failed,'categories_succeeded':succeeded,'stores_total':stores,'count_warnings':[{}]*warnings,'category_option_audit':{'issues':[{}]*audit},'multi_rate_conflicts':[{}]*conf}}

def test_only_non_ok_days_need_recovery():
    assert not m.needs_recovery(rec('ok'));assert m.needs_recovery(rec('partial'));assert m.needs_recovery(rec('fetch_error'))

def test_ok_retry_always_beats_partial_initial():
    assert m.choose_better(rec('partial',1,49,5999),rec('ok',0,50,6702))['status']=='ok'

def test_better_partial_prefers_fewer_failures_then_more_stores():
    a=rec('partial',2,48,5000);b=rec('partial',1,49,5900);assert m.choose_better(a,b) is b
    a=rec('partial',1,49,5000);b=rec('partial',1,49,5900);assert m.choose_better(a,b) is b

def test_audit_and_conflict_penalize_same_status():
    clean=rec('partial',1,49,5000,0,0);dirty=rec('partial',1,49,6000,1,0);assert m.choose_better(dirty,clean) is clean

def test_clean_confirmation_rejects_hidden_uncertainty():
    assert m.clean_confirmation(rec('ok'))
    assert not m.clean_confirmation(rec('ok',failed=1))
    assert not m.clean_confirmation(rec('ok',warnings=1))
    assert not m.clean_confirmation(rec('ok',audit=1))
    assert not m.clean_confirmation(rec('ok',conf=1))

def test_recovery_policy_requires_two_parallel_bounded_confirmations():
    assert m.RECOVERY_ATTEMPTS==2
    assert m.REQUIRED_CLEAN_CONFIRMATIONS==2
    assert m.RECOVERY_DAY_CONCURRENCY==1
    src=(S/'scrape_v075.py').read_text(encoding='utf-8')
    assert 'asyncio.gather(*(one_attempt(n)' in src
    assert "'parallel_attempts':True" in src
    assert 'fewer than two clean confirmations' in src

def test_retry_event_runs_two_independent_confirmations_concurrently(monkeypatch):
    active=0;peak=0;opened=0;closed=0
    class Page:
        async def close(self):
            nonlocal closed;closed+=1
    class Context:
        async def new_page(self):
            nonlocal opened;opened+=1;return Page()
    async def fake_collect(page,date,url,label):
        nonlocal active,peak
        active+=1;peak=max(peak,active)
        await asyncio.sleep(.02)
        active-=1
        return rec('ok')
    monkeypatch.setattr(m.strict,'collect_event',fake_collect)
    original=rec('partial',failed=1,succeeded=49,stores=5900)
    original.update({'date':'2026-08-18','url':'https://example.invalid/event','label':'test'})
    result=asyncio.run(m.retry_event(Context(),original))
    recovery=result['diagnostics']['recovery']
    assert peak==2
    assert opened==2 and closed==2
    assert recovery['parallel_attempts'] is True
    assert recovery['clean_confirmations']==2
    assert recovery['recovered'] is True
    assert result['status']=='ok'
