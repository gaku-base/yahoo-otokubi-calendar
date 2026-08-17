import importlib.util,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];S=ROOT/'scripts'
spec=importlib.util.spec_from_file_location('run_refresh_safe',S/'run_refresh_safe.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def test_success_status_uses_new_good_timestamp():
    new={'updated_at':'new','validation':{'ok':True,'counts':{'days':47},'issues':[]}};old={'updated_at':'old'}
    s=m.status_from_attempt(True,new,old,exit_code=0)
    assert s['last_attempt_ok'] is True and s['last_good_updated_at']=='new' and s['attempt_counts']['days']==47 and s['issues']==[]

def test_failure_status_keeps_previous_good_timestamp_and_attempt_diagnostics():
    bad={'updated_at':'bad','validation':{'ok':False,'counts':{'partial':1},'issues':['Incomplete BONUS+ days: 1']}};old={'updated_at':'good'}
    s=m.status_from_attempt(False,bad,old,message='failed',exit_code=2)
    assert s['last_attempt_ok'] is False and s['last_good_updated_at']=='good' and s['attempt_source_updated_at']=='bad'
    assert s['attempt_counts']['partial']==1 and s['issues']==['Incomplete BONUS+ days: 1'] and s['last_attempt_exit_code']==2

def test_restore_bytes_round_trip(tmp_path):
    p=tmp_path/'x.json';p.write_bytes(b'old');old=m.backup_bytes(p);p.write_bytes(b'bad');m.restore_bytes(p,old);assert p.read_bytes()==b'old'
    m.restore_bytes(p,None);assert not p.exists()

def test_wrapper_source_restores_good_data_before_failure_status():
    src=(S/'run_refresh_safe.py').read_text(encoding='utf-8')
    assert 'restore_bytes(bonus_path,old_bonus_bytes)' in src
    assert 'restore_bytes(campaign_path,old_campaign_bytes)' in src
    assert "DIAG/f'{stamp}_failed_bonus.json'" in src
