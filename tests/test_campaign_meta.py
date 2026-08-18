import importlib.util,sys
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];SCRIPTS=ROOT/'scripts'
if str(SCRIPTS) not in sys.path:sys.path.insert(0,str(SCRIPTS))
spec=importlib.util.spec_from_file_location('campaign_meta',SCRIPTS/'campaign_meta.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

SAMPLE='''
期間開催の予定
18 (火)
〜
20 (木)
ボーナスストアPlusくじ
最大1万円相当
対象ストア限定 1注文1,000円～69,999円
※注意
24 (月)
〜
30 (日)
Brand Week
最大25%
要エントリー 対象ストア限定 付与上限あり
'''

def test_lottery_is_informational_only():
    rows=m.parse_informational_periods(SAMPLE,date(2026,8,18));assert len(rows)==1
    r=rows[0];assert r['title']=='ボーナスストアPlusくじ';assert r['dates']==['2026-08-18','2026-08-19','2026-08-20'];assert r['rate'] is None and r['rate_label']=='最大1万円相当';assert r['informational'] and r['calculation_mode']=='lottery' and r['target_store_limited']

def test_annotations_are_fail_closed_and_gold_aware():
    p2=m.annotate({'title':'ボーナスストアPlusでさらに+2%','rate':2,'target_store_limited':True});assert p2['eligibility_mode']=='bonus_store_day' and p2['detail_url'].endswith('/bsplus/')
    p3=m.annotate({'title':'ボーナスストアPlus 優良ストアでさらに+3%','rate':3,'target_store_limited':True});assert p3['eligibility_mode']=='excellent_store_unknown'
    sun=m.annotate({'title':'プレミアムな日曜日','rate':5,'target_store_limited':True});assert sun['eligibility_mode']=='bonus_badge_unknown'
    thanks=m.annotate({'title':'ヤフショ感謝デー','rate':5,'is_max':True,'conditions':['要エントリー シルバー+4%・ゴールド+5% 対象ストア限定'],'target_store_limited':True});assert thanks['rank_rates']=={'silver':4.0,'gold':5.0} and thanks['calculation_mode']=='rank_additive'
    five=m.annotate({'title':'5のつく日','rate':4,'target_store_limited':False});assert five['eligibility_mode']=='not_limited'

if __name__=='__main__':
    test_lottery_is_informational_only();test_annotations_are_fail_closed_and_gold_aware();print('campaign metadata tests: PASS')
