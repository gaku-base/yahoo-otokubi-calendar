import importlib.util
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('compact_client_data',ROOT/'scripts'/'compact_client_data.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
compact,validate=mod.compact,mod.validate

def sample():
    return {'schema':'x','source':'u','updated_at':'2026-08-17T00:00:00+09:00','validation':{'ok':True},'days':[{'date':'2026-08-17','url':'u','label':'8/17','status':'ok','rates':[5,10],'diagnostics':{'categories_total':2,'categories_succeeded':2,'categories_failed':0,'stores_total':4,'count_warnings':[{'x':1}]},'stores':[{'name':'TP-Link公式ダイレクト','slug':'tplink','rate':5},{'name':'TP-Link公式ダイレクト','slug':'tplink','rate':10},{'name':'ABC 公式店','slug':'','rate':5},{'name':'ABC　公式店','slug':'','rate':5}]}]}

def test_indexed_compaction_deduplicates_and_keeps_max_rate():
    out=compact(sample()); validate(out)
    assert out['format']=='indexed-v1' and out['version']=='0.8.0' and len(out['store_catalog'])==2
    offers=dict(out['days'][0]['offers']); tplink_id=next(i for i,row in enumerate(out['store_catalog']) if row[1]=='tplink')
    assert offers[tplink_id]==10.0 and len(offers)==2
    assert out['days'][0]['diagnostics']['count_warnings']==1 and out['days'][0]['diagnostics']['stores_unique']==2

def test_catalog_ids_are_reused_across_days():
    src={'validation':{'ok':True},'days':[{'date':'2026-08-17','status':'ok','stores':[{'name':'Shop','slug':'shop','rate':5}]},{'date':'2026-08-18','status':'ok','stores':[{'name':'Shop','slug':'shop','rate':10}]}]}
    out=compact(src); validate(out); assert len(out['store_catalog'])==1; assert out['days'][0]['offers'][0][0]==out['days'][1]['offers'][0][0]==0

def test_compaction_is_idempotent():
    first=compact(sample()); second=compact(first); assert second==first

def test_validate_rejects_duplicate_date_and_invalid_rate():
    out=compact(sample()); out['days'].append(dict(out['days'][0]))
    with pytest.raises(ValueError): validate(out)
    out=compact(sample()); out['days'][0]['offers'][0][1]=float('nan')
    with pytest.raises(ValueError): validate(out)
