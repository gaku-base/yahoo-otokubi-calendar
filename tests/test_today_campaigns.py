import importlib.util,sys
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];SCRIPTS=ROOT/'scripts'
if str(SCRIPTS) not in sys.path:sys.path.insert(0,str(SCRIPTS))
spec=importlib.util.spec_from_file_location('today_campaigns',SCRIPTS/'today_campaigns.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

SAMPLE='''
ヤフーデイリーボーナス
開催中のボーナス
本日開催
ハッピー24アワー
+4%
要エントリー 注文3,000円～ 付与上限2,000円相当
毎日開催
毎日5%
+5%
決済条件あり 付与上限あり 対象者限定
ボーナスストアPlus
+5%or+10%
対象ストア限定 付与上限あり 要エントリー
'''


def test_parse_today_happy24hour():
    rows,marker=m.parse_today_campaigns(SAMPLE,date(2026,8,19))
    assert marker is True and len(rows)==1
    row=rows[0]
    assert row['title']=='ハッピー24アワー'
    assert row['rate']==4 and row['rate_label']=='+4%'
    assert row['dates']==['2026-08-19']
    assert row['entry_required'] is True
    assert row['target_store_limited'] is False and row['eligibility_rule']=='all'
    assert row['rankable'] is True and row['same_day_discovery'] is True
    assert row['source_url'].endswith('/happyhour/')
    assert any('注文3,000円～' in x for x in row['conditions'])
    assert any('付与上限2,000円相当' in x for x in row['conditions'])


def test_parse_stops_before_everyday_bonuses():
    rows,_=m.parse_today_campaigns(SAMPLE,date(2026,8,19))
    titles=[x['title'] for x in rows]
    assert '毎日5%' not in titles and 'ボーナスストアPlus' not in titles


def test_missing_today_marker_is_detectable():
    rows,marker=m.parse_today_campaigns('毎日開催\n毎日5%\n+5%',date(2026,8,19))
    assert rows==[] and marker is False


def test_merge_adds_today_without_losing_scheduled_rows():
    existing=[{'title':'5のつく日','rate':4.0,'rate_label':'+4%','dates':['2026-08-25'],'conditions':['要エントリー'],'informational':False,'is_total':False,'rankable':True}]
    today,_=m.parse_today_campaigns(SAMPLE,date(2026,8,19))
    rows=m.merge_today_campaigns(existing,today)
    assert any(x['title']=='5のつく日' and x['dates']==['2026-08-25'] for x in rows)
    happy=next(x for x in rows if x['title']=='ハッピー24アワー')
    assert happy['dates']==['2026-08-19'] and happy['rate']==4


def test_merge_deduplicates_same_day_campaign():
    existing=[{'title':'ハッピー24アワー','rate':4.0,'rate_label':'+4%','dates':['2026-08-19'],'conditions':['注文3,000円～'],'informational':False,'is_total':False,'rankable':True}]
    today,_=m.parse_today_campaigns(SAMPLE,date(2026,8,19))
    rows=m.merge_today_campaigns(existing,today)
    happy=[x for x in rows if x['title']=='ハッピー24アワー']
    assert len(happy)==1 and happy[0]['dates']==['2026-08-19']
    assert any('付与上限2,000円相当' in x for x in happy[0]['conditions'])
