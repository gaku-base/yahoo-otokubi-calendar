import importlib.util,sys
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];SCRIPTS=ROOT/'scripts'
if str(SCRIPTS) not in sys.path:sys.path.insert(0,str(SCRIPTS))
spec=importlib.util.spec_from_file_location('calendar_campaigns',SCRIPTS/'calendar_campaigns.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

SAMPLE='''
おトクカレンダー お買い得日をチェック！
イベントをタップすると、詳細を確認できます。
まもなく開催
08/12~08/25
12
水
ボーナスストアPlusでさらに+2%
＋2%
注文3,000円～ 付与上限5,000円相当 要エントリー 対象ストア限定
ボーナスストアPlus 優良ストアでさらに+3%
＋3%
注文3,000円～ 付与上限5,000円相当 要エントリー 対象ストア限定
13
木
14
金
ボーナスストアPlusでさらに+2%
＋2%
注文3,000円～ 付与上限5,000円相当 要エントリー 対象ストア限定
15
土
5のつく日
+4%
要エントリー 指定支払い方法あり 付与上限1,000円相当
16
日
プレミアムな日曜日
＋5%
注文5,000円～ 付与上限2,000円相当 要エントリー 対象ストア限定
17
月
18
火
ボーナスストアPlusでさらに+2%
＋2%
注文3,000円～ 付与上限5,000円相当 要エントリー 対象ストア限定
22
土
ヤフショ感謝デー
最大+5%
要エントリー シルバー+4%・ゴールド+5% 対象ストア限定 付与上限1000円相当
25
火
5のつく日
+4%
要エントリー 指定支払い方法あり 付与上限1,000円相当
08/26~09/08
26
水
31
月
9/1
火
2
水
ボーナスストアPlusでさらに+2%
＋2%
注文3,000円～ 付与上限5,000円相当 要エントリー 対象ストア限定
ボーナスストアPlus 優良ストアでさらに+3%
＋3%
注文3,000円～ 付与上限5,000円相当 要エントリー 対象ストア限定
5
土
5のつく日
+4%
要エントリー 指定支払い方法あり 付与上限1,000円相当
8
火
期間開催の予定
18 (火)
〜
20 (木)
ボーナスストアPlusくじ
最大1万円相当
24 (月)
〜
30 (日)
Brand Week
最大25%
要エントリー 対象ストア限定 付与上限あり
※付与されるPayPayポイントは、期間限定です。
'''

LIVE_NO_RANGE='''
おトクカレンダー
お買い得日をチェック！
イベントをタップすると、詳細を確認できます。
まもなく開催
18
火
ボーナスストアPlusでさらに+2%
＋2%
注文3,000円～ 付与上限5,000円相当 要エントリー 対象ストア限定
ボーナスストアPlus 優良ストアでさらに+3%
＋3%
注文3,000円～ 付与上限5,000円相当 要エントリー 対象ストア限定
19
水
20
木
21
金
ボーナスストアPlusでさらに+2%
＋2%
注文3,000円～ 付与上限5,000円相当 要エントリー 対象ストア限定
22
土
ヤフショ感謝デー
最大+5%
要エントリー シルバー+4%・ゴールド+5% 対象ストア限定 付与上限1000円相当
23
日
プレミアムな日曜日
＋5%
注文5,000円～ 付与上限2,000円相当 要エントリー 対象ストア限定
24
月
期間開催の予定
24 (月)
〜
30 (日)
Brand Week
最大25%
要エントリー 対象ストア限定 付与上限あり
※付与されるPayPayポイントは、期間限定です。
'''

def by_title(rows,title):return next(x for x in rows if x['title']==title)

def test_parse_calendar_discrete_dates_rates_and_conditions():
    rows=m.parse_calendar_text(SAMPLE,date(2026,8,17))
    plus2=by_title(rows,'ボーナスストアPlusでさらに+2%')
    assert plus2['rate']==2 and plus2['dates']==['2026-08-12','2026-08-14','2026-08-18','2026-09-02']
    assert plus2['entry_required'] and plus2['target_store_limited']
    plus3=by_title(rows,'ボーナスストアPlus 優良ストアでさらに+3%')
    assert plus3['rate']==3 and plus3['dates']==['2026-08-12','2026-09-02']
    five=by_title(rows,'5のつく日');assert five['rate']==4 and five['dates']==['2026-08-15','2026-08-25','2026-09-05']
    sunday=by_title(rows,'プレミアムな日曜日');assert sunday['rate']==5 and sunday['dates']==['2026-08-16']
    thank=by_title(rows,'ヤフショ感謝デー');assert thank['rate']==5 and thank['is_max'] and thank['dates']==['2026-08-22']
    bw=by_title(rows,'Brand Week');assert bw['rate'] is None and bw['rate_label']=='最大25%' and len(bw['dates'])==7
    assert bw['dates'][0]=='2026-08-24' and bw['dates'][-1]=='2026-08-30'
    assert not any('くじ' in x['title'] for x in rows)

def test_live_shape_without_range_uses_reference_date():
    rows=m.parse_calendar_text(LIVE_NO_RANGE,date(2026,8,17))
    assert by_title(rows,'ボーナスストアPlusでさらに+2%')['dates']==['2026-08-18','2026-08-21']
    assert by_title(rows,'ボーナスストアPlus 優良ストアでさらに+3%')['dates']==['2026-08-18']
    assert by_title(rows,'ヤフショ感謝デー')['dates']==['2026-08-22']
    assert by_title(rows,'プレミアムな日曜日')['dates']==['2026-08-23']
    assert by_title(rows,'Brand Week')['dates']==['2026-08-24','2026-08-25','2026-08-26','2026-08-27','2026-08-28','2026-08-29','2026-08-30']

def test_rate_parser_does_not_treat_off_or_lottery_as_additive_points():
    assert m.parse_rate('最大+5%')['is_max']
    assert m.parse_rate('＋3％')['rate']==3
    assert m.parse_rate('10%OFF') is None
    assert m.parse_rate('最大25%') is None and m.parse_total_rate('最大25%')['is_total']
    assert m.parse_rate('最大1万円相当') is None

def test_merge_safe_guide_only_adds_safe_named_future_campaigns():
    cal=m.parse_calendar_text(SAMPLE,date(2026,8,17))
    guide={'source':'guide','campaigns':[
        {'title':'プレミアムな日曜日','dates':['2026-09-20'],'period':'p'},
        {'title':'ヤフショ感謝デー','dates':['2026-09-22'],'period':'p'},
        {'title':'チャンスタイム','dates':['2026-10-01'],'period':'p'},
        {'title':'キリンビバレッジ対象商品購入でPayPayポイント最大+15％！','dates':['2026-09-01'],'period':'p'},
    ]}
    rows=m.merge_safe_guide(cal,guide)
    assert '2026-09-20' in by_title(rows,'プレミアムな日曜日')['dates']
    assert '2026-09-22' in by_title(rows,'ヤフショ感謝デー')['dates']
    assert not any(x['title']=='チャンスタイム' for x in rows)
    assert not any('キリン' in x['title'] for x in rows)
