from __future__ import annotations
import re
from datetime import date,datetime,timedelta,timezone

JST=timezone(timedelta(hours=9))
CALENDAR_URL='https://shopping.yahoo.co.jp/promotion/campaign/dailybonus/calendar/'
DETAIL_URLS={
    'bsplus':'https://shopping.yahoo.co.jp/promotion/campaign/bsplus/',
    'premium_sunday':'https://shopping.yahoo.co.jp/promotion/campaign/lypsunday/',
    'thanks':'https://shopping.yahoo.co.jp/promotion/campaign/pointrank/',
    'five_day':'https://shopping.yahoo.co.jp/promotion/campaign/5day/',
}

def clean(s:str)->str:return re.sub(r'\s+',' ',s or '').strip()

def next_day_number(n:int,base:date,max_days:int=40):
    for delta in range(max_days+1):
        d=base+timedelta(days=delta)
        if d.day==n:return d
    return None

def reward_label(s:str):
    s=clean(s).replace('万円','万円').replace('％','%')
    if re.fullmatch(r'最大\s*[0-9,.]+\s*(?:万)?円相当',s):return s.replace(' ','')
    return None

def parse_informational_periods(text:str,reference:date|None=None):
    ref=reference or datetime.now(JST).date();lines=[clean(x) for x in (text or '').splitlines() if clean(x)];out=[];base=ref
    for i in range(len(lines)-5):
        a=re.fullmatch(r'(\d{1,2})\s*[（(][月火水木金土日](?:曜)?[）)]',lines[i])
        if not a or lines[i+1] not in ('〜','～','~','-'):continue
        b=re.fullmatch(r'(\d{1,2})\s*[（(][月火水木金土日](?:曜)?[）)]',lines[i+2])
        if not b:continue
        title=lines[i+3];label=reward_label(lines[i+4])
        if not label or not any(k in title for k in ('くじ','抽選')):continue
        start=next_day_number(int(a.group(1)),base);end=next_day_number(int(b.group(1)),start or base)
        if not start or not end or end<start or (end-start).days>31:continue
        conditions=[]
        if i+5<len(lines) and not lines[i+5].startswith('※'):conditions.append(lines[i+5])
        dates=[];d=start
        while d<=end:dates.append(d.isoformat());d+=timedelta(days=1)
        out.append({'title':title,'rate':None,'rate_label':label,'is_max':True,'is_total':False,'dates':dates,'conditions':conditions,'source':CALENDAR_URL,'entry_required':False,'target_store_limited':'対象ストア限定' in ' '.join(conditions),'informational':True,'calculation_mode':'lottery','eligibility_mode':'unknown'})
        base=start
    return out

def annotate(row:dict):
    r=dict(row);title=str(r.get('title') or '');conds=' '.join(r.get('conditions') or [])
    r.setdefault('informational',False);r.setdefault('calculation_mode','additive' if r.get('rate') is not None and not r.get('is_total') else 'display_only')
    if 'ボーナスストアPlusでさらに+2' in title:
        r.update({'detail_url':DETAIL_URLS['bsplus'],'eligibility_mode':'bonus_store_day','calculation_mode':'additive'})
    elif '優良ストア' in title and ('+3' in title or '＋3' in title):
        r.update({'detail_url':DETAIL_URLS['bsplus'],'eligibility_mode':'excellent_store_unknown','calculation_mode':'additive'})
    elif 'プレミアムな日曜日' in title:
        r.update({'detail_url':DETAIL_URLS['premium_sunday'],'eligibility_mode':'bonus_badge_unknown','calculation_mode':'additive'})
    elif 'ヤフショ感謝デー' in title:
        r.update({'detail_url':DETAIL_URLS['thanks'],'eligibility_mode':'bonus_badge_unknown','calculation_mode':'rank_additive','rank_rates':{'silver':4.0,'gold':5.0}})
    elif '5のつく日' in title:
        r.update({'detail_url':DETAIL_URLS['five_day'],'eligibility_mode':'not_limited','calculation_mode':'additive'})
    elif 'Brand Week' in title or 'ブランドウィーク' in title:
        r.update({'eligibility_mode':'unknown','calculation_mode':'total_max','informational':True})
    elif r.get('target_store_limited'):
        r.setdefault('eligibility_mode','unknown')
    else:r.setdefault('eligibility_mode','not_limited')
    if any(k in title for k in ('くじ','抽選')):
        r['informational']=True;r['calculation_mode']='lottery';r.setdefault('eligibility_mode','unknown')
    if 'シルバー+4%' in conds and 'ゴールド+5%' in conds:
        r['rank_rates']={'silver':4.0,'gold':5.0};r['calculation_mode']='rank_additive'
    return r

def merge_rows(rows:list[dict],extras:list[dict]):
    out=[annotate(x) for x in rows]
    keys={(str(x.get('title')),str(x.get('rate_label')),tuple(x.get('dates') or [])) for x in out}
    for x in extras:
        a=annotate(x);key=(str(a.get('title')),str(a.get('rate_label')),tuple(a.get('dates') or []))
        if key not in keys:out.append(a);keys.add(key)
    out.sort(key=lambda x:((x.get('dates') or ['9999'])[0],str(x.get('title') or '')))
    return out

async def enrich_campaign_rows(page,rows:list[dict],reference:date|None=None):
    diagnostics={'source':CALENDAR_URL,'informational_found':0,'errors':[]}
    extras=[]
    try:
        resp=await page.goto(CALENDAR_URL,wait_until='domcontentloaded',timeout=45000)
        if resp and resp.status>=400:raise RuntimeError(f'HTTP {resp.status}')
        await page.wait_for_timeout(350);body=await page.locator('body').inner_text(timeout=15000);extras=parse_informational_periods(body,reference);diagnostics['informational_found']=len(extras)
    except Exception as e:diagnostics['errors'].append(clean(repr(e))[:500])
    return merge_rows(rows,extras),diagnostics
