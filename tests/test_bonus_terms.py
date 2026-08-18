import importlib.util,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];SCRIPTS=ROOT/'scripts'
if str(SCRIPTS) not in sys.path:sys.path.insert(0,str(SCRIPTS))
spec=importlib.util.spec_from_file_location('bonus_terms',SCRIPTS/'bonus_terms.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

CURRENT='''
企画名
ボーナスストアPlus ＋10％【対象ストア限定】
開催期間
2026年08月18日 00:00～2026年08月18日 23:59
付与内容
対象金額の10％を付与
＜付与されるPayPayポイント（期間限定）について＞
【付与上限数】
お1人様あたり10,000円相当
企画名
ボーナスストアPlus ＋5％【対象ストア限定】
開催期間
2026年08月18日 00:00～2026年08月18日 23:59
付与内容
対象金額の5％を付与
【付与上限数】
お1人様あたり5,000円相当
'''

FUTURE='''
企画名 ボーナスストアPlus +9%【対象ストア限定】
付与上限 お1人様あたり9,000円相当
企画名
ボーナスストアPlus ＋4％【対象ストア限定】
付与上限数
お1人様あたり4,000円相当
'''

def test_parse_current_rate_caps():
    assert m.parse_rate_caps(CURRENT)=={'10':10000,'5':5000}

def test_parser_is_rate_agnostic_for_future_changes():
    assert m.parse_rate_caps(FUTURE)=={'9':9000,'4':4000}

def test_unrelated_numbers_do_not_become_caps():
    text='''最大25％\n付与上限50,000円相当\n企画名\n別のキャンペーン +8%\n付与上限8,000円相当'''
    assert m.parse_rate_caps(text)=={}
