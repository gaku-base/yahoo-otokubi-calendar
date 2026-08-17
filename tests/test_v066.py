import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('scrape_v066',ROOT/'scripts'/'scrape_v066.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def test_count_tolerance_is_strict_for_small_categories_and_allows_stale_large_counter():
    assert m.count_tolerance(1)==0
    assert m.count_tolerance(20)==0
    assert m.count_tolerance(21)==1
    assert m.count_tolerance(134)==1
    assert m.count_tolerance(302)==2

def test_broad_campaign_filter_excludes_product_and_lottery_noise():
    assert m.is_broad_campaign('プレミアムな日曜日')
    assert m.is_broad_campaign('ヤフショ Brand Weekポイントキャンペーン')
    assert m.is_broad_campaign('チャンスタイム')
    assert not m.is_broad_campaign('キリンビバレッジ対象商品購入でPayPayポイント最大+15％！')
    assert not m.is_broad_campaign('ボーナスストアPlusのお買い物で引けるくじ')
    assert not m.is_broad_campaign('ヤフショ Brand Weekクーポン')

def test_filter_guide_preserves_metadata():
    guide={'source':'u','errors':[],'campaigns':[{'title':'ヤフショ感謝デー'},{'title':'エリエール対象商品購入でPayPayポイント最大+10％！'}]}
    got=m.filter_guide(guide)
    assert got['source']=='u' and got['errors']==[]
    assert [x['title'] for x in got['campaigns']]==['ヤフショ感謝デー']
