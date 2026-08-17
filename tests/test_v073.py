import importlib.util,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];S=ROOT/'scripts'
if str(S) not in sys.path:sys.path.insert(0,str(S))
spec=importlib.util.spec_from_file_location('scrape_v073',S/'scrape_v073.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def test_fast_accept_rejects_empty_and_large_count_mismatch():
    assert not m.fast_accept(10,0,('a',),None,0)
    assert not m.fast_accept(10,9,('a',),None,0)
    assert not m.fast_accept(100,98,('a',),None,0)

def test_fast_accept_allows_exact_or_tolerated_count_when_not_stale():
    assert m.fast_accept(10,10,('b',),('a',),0)
    assert m.fast_accept(134,133,('b',),('a',),0)

def test_same_signature_as_previous_category_needs_second_observation():
    sig=(('shop',5.0),)
    assert not m.fast_accept(10,10,sig,sig,0)
    assert m.fast_accept(10,10,sig,sig,1)

def test_count_warning_policy_is_fail_closed_in_collect_event_source():
    src=(S/'scrape_v073.py').read_text(encoding='utf-8')
    assert "rec['status']='partial'" in src
    assert 'refusing hard not-found decisions' in src
