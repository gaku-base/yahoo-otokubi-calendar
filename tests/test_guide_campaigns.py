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
'''

def test_parse_and_merge_current_day_schedule():
    rows=m.parse_target_guide(SAMPLE);assert len(rows)==2,rows
    p2=next(x for x in rows if x['rate']==2);p3=next(x for x in rows if x['rate']==3)
    expected=['2026-08-08','2026-08-12','2026-08-14','2026-08-18','2026-08-21','2026-08-31']
    assert p2['dates']==expected and p3['dates']==expected
    assert p2['conditions']==['注文3,000円～','付与上限5,000円相当','要エントリー','対象ストア限定']
    base=[{'title':'ボーナスストアPlusでさらに+2%','rate':2.0,'rate_label':'+2%','dates':['2026-08-21'],'conditions':['注文3,000円～'],'target_store_limited':True,'entry_required':True}]
    merged=m.merge_target_guide(base,rows);mp2=next(x for x in merged if x['rate']==2);assert mp2['dates']==expected and mp2['schedule_source']==m.GUIDE_URL

if __name__=='__main__':test_parse_and_merge_current_day_schedule();print('guide campaign tests: PASS')
