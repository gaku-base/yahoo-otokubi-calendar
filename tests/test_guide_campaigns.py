import importlib.util,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];SCRIPTS=ROOT/'scripts'
if str(SCRIPTS) not in sys.path:sys.path.insert(0,str(SCRIPTS))
spec=importlib.util.spec_from_file_location('guide_campaigns',SCRIPTS/'guide_campaigns.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

SAMPLE='''
ボーナスストアPlusでさらに+2％【対象ストア限定】
開催期間：2026/8/8 0:00 ～ 2026/8/8 23:59
2026/8/12 0:00 ～ 2026/8/12 23:59
2026/8/14 0:00 ～ 2026/8/14 23:59
2026/8/18 0:00 ～ 2026/8/18 23:59
2026/8/21 0:00 ～ 2026/8/21 23:59
2026/8/31 0:00 ～ 2026/8/31 23:59
対象者：全員
条件：エントリーと同一のYahoo! JAPAN IDでログインの上、開催期間中に対象ストアで決済していること
3,000円以上で決済していること
付与率：2％
付与上限：5,000円相当
対象ストア：指定あり
※日程・内容は変更になる場合があります。
ボーナスストアPlus限定 優良ストアでの購入でさらに+3％【対象ストア限定】
開催期間：2026/8/8 0:00 ～ 2026/8/8 23:59
2026/8/12 0:00 ～ 2026/8/12 23:59
2026/8/14 0:00 ～ 2026/8/14 23:59
2026/8/18 0:00 ～ 2026/8/18 23:59
2026/8/21 0:00 ～ 2026/8/21 23:59
2026/8/31 0:00 ～ 2026/8/31 23:59
対象者：全員
条件：エントリーと同一のYahoo! JAPAN IDでログインの上、開催期間中に対象ストアで決済していること
3,000円以上で決済していること
付与率：3％
付与上限：5,000円相当
対象ストア：指定あり
※日程・内容は変更になる場合があります。
ボーナスストアPlusでさらに+2％【対象ストア限定】
開催期間：2026/9/2 0:00 ～ 2026/9/2 23:59
2026/9/3 0:00 ～ 2026/9/3 23:59
2026/9/5 0:00 ～ 2026/9/5 23:59
2026/9/8 0:00 ～ 2026/9/8 23:59
条件：エントリーと同一のYahoo! JAPAN IDでログインの上、開催期間中に対象ストアで決済していること
3,000円以上で決済していること
付与率：2％
付与上限：5,000円相当
対象ストア：指定あり
※日程・内容は変更になる場合があります。
ボーナスストアPlus限定 優良ストアでの購入でさらに+3％【対象ストア限定】
開催期間：2026/9/2 0:00 ～ 2026/9/2 23:59
2026/9/3 0:00 ～ 2026/9/3 23:59
2026/9/8 0:00 ～ 2026/9/8 23:59
条件：エントリーと同一のYahoo! JAPAN IDでログインの上、開催期間中に対象ストアで決済していること
3,000円以上で決済していること
付与率：3％
付与上限：5,000円相当
対象ストア：指定あり
※日程・内容は変更になる場合があります。
'''

def row(rows,rate):return next(x for x in rows if x['rate']==rate)

def test_parse_target_guide_unions_repeated_month_sections():
    rows=m.parse_target_guide(SAMPLE);assert len(rows)==2,rows
    p2=row(rows,2);p3=row(rows,3)
    assert p2['dates']==['2026-08-08','2026-08-12','2026-08-14','2026-08-18','2026-08-21','2026-08-31','2026-09-02','2026-09-03','2026-09-05','2026-09-08']
    assert p3['dates']==['2026-08-08','2026-08-12','2026-08-14','2026-08-18','2026-08-21','2026-08-31','2026-09-02','2026-09-03','2026-09-08']
    assert p2['conditions']==['注文3,000円～','付与上限5,000円相当','要エントリー','対象ストア限定']
    assert p2['eligibility_rule']=='bonus_plus_member' and p3['eligibility_rule']=='preferred_bonus_store'
    assert p2['source_url']==m.BSPLUS_URL and p3['source_url']==m.BSPLUS_URL

def test_merge_target_guide_preserves_safe_eligibility_and_adds_dates():
    guide=m.parse_target_guide(SAMPLE)
    base=[{'title':'ボーナスストアPlusでさらに+2%','rate':2.0,'rate_label':'+2%','dates':['2026-08-21'],'conditions':['注文3,000円～'],'target_store_limited':True,'entry_required':True,'eligibility_rule':'bonus_plus_member','informational':False,'rankable':True}]
    merged=m.merge_target_guide(base,guide);p2=row(merged,2);p3=row(merged,3)
    assert '2026-08-18' in p2['dates'] and '2026-08-31' in p2['dates'] and '2026-09-08' in p2['dates']
    assert p2['eligibility_rule']=='bonus_plus_member';assert p3['eligibility_rule']=='preferred_bonus_store'
    assert p2['rankable'] is True and p3['rankable'] is True
    assert p2['schedule_source']==m.GUIDE_URL

def test_conflicting_rate_is_not_merged_into_existing_campaign():
    base=[{'title':'ボーナスストアPlusでさらに+2%','rate':2.0,'rate_label':'+2%','dates':['2026-08-21'],'conditions':[],'target_store_limited':True,'entry_required':True,'eligibility_rule':'bonus_plus_member','informational':False,'rankable':True}]
    conflicting=[{'title':'ボーナスストアPlusでさらに+2%','rate':3.0,'rate_label':'+3%','dates':['2026-08-31'],'conditions':[],'target_store_limited':True,'entry_required':True,'eligibility_rule':'bonus_plus_member'}]
    merged=m.merge_target_guide(base,conflicting);assert row(merged,2)['dates']==['2026-08-21']
