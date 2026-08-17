import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('compact_client_data',ROOT/'scripts'/'compact_client_data.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
compact,validate=mod.compact,mod.validate

def test_indexed_compaction_deduplicates_and_keeps_max_rate():
    src={
        'schema':'x','source':'u','updated_at':'2026-08-17T00:00:00+09:00','validation':{'ok':True},
        'days':[{
            'date':'2026-08-17','url':'u','label':'8/17','status':'ok','rates':[5,10],
            'diagnostics':{'categories_total':2,'categories_succeeded':2,'categories_failed':0,'stores_total':4},
            'stores':[
                {'name':'TP-Link公式ダイレクト','slug':'tplink','rate':5},
                {'name':'TP-Link公式ダイレクト','slug':'tplink','rate':10},
                {'name':'ABC 公式店','slug':'','rate':5},
                {'name':'ABC　公式店','slug':'','rate':5},
            ]
        }]
    }
    out=compact(src); validate(out)
    assert out['format']=='indexed-v1'
    assert out['version']=='0.6.4'
    assert len(out['store_catalog'])==2
    offers=dict(out['days'][0]['offers'])
    tplink_id=next(i for i,row in enumerate(out['store_catalog']) if row[1]=='tplink')
    assert offers[tplink_id]==10.0
    assert len(offers)==2

def test_catalog_ids_are_reused_across_days():
    src={'days':[
        {'date':'2026-08-17','status':'ok','stores':[{'name':'Shop','slug':'shop','rate':5}]},
        {'date':'2026-08-18','status':'ok','stores':[{'name':'Shop','slug':'shop','rate':10}]},
    ]}
    out=compact(src); validate(out)
    assert len(out['store_catalog'])==1
    assert out['days'][0]['offers'][0][0]==out['days'][1]['offers'][0][0]==0
