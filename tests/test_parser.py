import importlib.util
from pathlib import Path
from datetime import date
p=Path(__file__).resolve().parents[1]/'scripts'/'scrape.py';spec=importlib.util.spec_from_file_location('scrape',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def test_dynamic_rates():
    for s,want in [('+10%対象ストア',10),('+5% 対象ストア',5),('+15%対象ストア',15),('+9%対象ストア',9),('+4%対象ストア',4),('+4.5%対象ストア',4.5)]:
        assert m.parse_rate_heading(s)==want
    assert m.parse_rate_heading('対象ストア') is None

def test_period_expand():
    ds=m.expand_period('開催期間：2026/08/24 00:00 ～ 2026/08/30 23:59');assert len(ds)==7 and ds[0]=='2026-08-24' and ds[-1]=='2026-08-30'
    assert m.expand_period('開催期間：2026年8月30日 0:00～2026年8月30日 23:59')==['2026-08-30']

def test_slug():
    assert m.store_slug('https://store.shopping.yahoo.co.jp/tplink/4895252500622.html')=='tplink'
    assert m.store_slug('https://STORE.SHOPPING.YAHOO.CO.JP/tplink/')=='tplink'
    assert m.store_slug('https://shopping.yahoo.co.jp/')==''

def test_date_year_resolution():
    assert m.parse_date_from_anchor('8月17日開催分', date(2026,8,16))=='2026-08-17'
    assert m.parse_date_from_anchor('1月1日開催分', date(2026,12,31))=='2027-01-01'

def test_static_event_parser_scopes_rates():
    raw='''<h2>+10%対象ストア</h2><div><a href="https://store.shopping.yahoo.co.jp/a/">A店</a></div>
    <h2>+5%対象ストア</h2><div><a href="https://store.shopping.yahoo.co.jp/b/item.html">B店</a></div>'''
    stores,rates=m.parse_static_event_html(raw)
    assert rates==[10,5]
    assert {(x['slug'],x['rate']) for x in stores}=={('a',10),('b',5)}

def test_dedupe_prefers_store_slug_and_keeps_different_rates():
    rows=[{'name':' Test 店 ','url':'https://store.shopping.yahoo.co.jp/test/a','rate':5},{'name':'Test 店','url':'https://store.shopping.yahoo.co.jp/test/b','rate':5},{'name':'Test 店','url':'https://store.shopping.yahoo.co.jp/test/c','rate':10}]
    got=m.dedupe_stores(rows)
    assert len(got)==2

def test_quality_never_claims_complete_on_failed_categories():
    stores=[{'name':f's{i}','url':f'https://store.shopping.yahoo.co.jp/s{i}/','rate':5} for i in range(20)]
    assert m.quality_status(stores,[5],{'options_attempted':3,'options_failed':1})[0]=='partial'
    assert m.quality_status(stores,[5],{'options_attempted':3,'options_failed':0})[0]=='ok'
    assert m.quality_status(stores[:2],[5],{'options_attempted':0,'options_failed':0})[0]=='partial'

def test_major_campaign_filter():
    assert m.is_major_campaign('プレミアムな日曜日')
    assert m.is_major_campaign('爆買WEEK')
    assert not m.is_major_campaign('対象者限定　最大半額クーポン')
    assert not m.is_major_campaign('ebookjapan ヤフー店　対象者限定クーポン')

def test_campaign_parser_period_and_filter():
    text='''プレミアムな日曜日
開催期間：2026/08/30 0:00～2026/08/30 23:59
対象ストア：指定あり

対象者限定　最大半額クーポン
開催期間：2026/08/20 0:00～2026/08/31 23:59
対象者：対象者限定'''
    got=m.parse_campaigns_from_text(text)
    assert len(got)==1 and got[0]['title']=='プレミアムな日曜日' and got[0]['dates']==['2026-08-30']

def test_validation_rejects_empty_and_all_partial():
    v=m.validate_output({'days':[]},{'campaigns':[],'errors':[]}); assert not v['ok']
    days=[{'status':'partial'} for _ in range(5)]
    v=m.validate_output({'days':days},{'campaigns':[],'errors':[]}); assert not v['ok']

def test_campaign_parser_real_guide_style_august():
    text='''プレミアムな日曜日
開催期間：2026/8/30 0:00～2026/8/30 23:59
対象者：全員
条件：対象ストアで1注文あたり5,000円以上決済していること
付与率：5％
付与上限：2,000円相当
対象ストア：指定あり
ヤフショ Brand Weekポイントキャンペーン
開催期間：2026/8/24 12:00～2026/8/30 23:59
対象者：全ユーザー
条件：エントリー必須
付与率：各キャンペーン5％
対象ストア：指定あり
ヤフショ Brand Weekクーポン
開催期間：2026/8/24 12:00～2026/8/30 23:59
値引き額：500円OFF
ヤフショ感謝デー
開催期間：2026/8/22 0:00～2026/8/22 23:59
対象者：対象者限定
付与率：最大5％'''
    got=m.parse_campaigns_from_text(text)
    by={x['title']:x for x in got}
    assert 'プレミアムな日曜日' in by
    assert 'ヤフショ Brand Weekポイントキャンペーン' in by
    assert 'ヤフショ感謝デー' in by
    assert 'ヤフショ Brand Weekクーポン' not in by
    assert len(by['ヤフショ Brand Weekポイントキャンペーン']['dates'])==7

def test_known_regression_guard_detects_missing_and_accepts_hit():
    b={'days':[{'date':'2026-08-17','stores':[]}]}
    assert m.check_known_regressions(b)
    b={'days':[{'date':'2026-08-17','stores':[{'slug':'tplink','rate':5}]}]}
    assert m.check_known_regressions(b)==[]
