from __future__ import annotations
from datetime import date, datetime, timedelta, timezone
from calendar_campaigns import clean, event_value, looks_like_title, norm

DAILYBONUS_URL='https://shopping.yahoo.co.jp/promotion/campaign/dailybonus/'
HAPPYHOUR_URL='https://shopping.yahoo.co.jp/promotion/campaign/happyhour/'
JST=timezone(timedelta(hours=9))


def source_url_for_today(title:str)->str:
    if 'ハッピー24アワー' in title or 'ハッピーアワー' in title:return HAPPYHOUR_URL
    return DAILYBONUS_URL


def parse_today_campaigns(text:str,reference:date|None=None):
    ref=reference or datetime.now(JST).date();lines=[clean(x) for x in (text or '').splitlines() if clean(x)]
    try:start=next(i for i,x in enumerate(lines) if x=='本日開催')+1
    except StopIteration:return [],False
    end=len(lines)
    for i in range(start,len(lines)):
        if lines[i] in ('毎日開催','明日開催','明日からのおトク') or lines[i].startswith('毎日開催'):
            end=i;break
    section=lines[start:end];rows=[];seen=set()
    for i,line in enumerate(section):
        value=event_value(line)
        if not value or i==0:continue
        title=section[i-1]
        if not looks_like_title(title):continue
        details=[]
        for nxt in section[i+1:i+5]:
            if event_value(nxt):break
            if looks_like_title(nxt) and not any(k in nxt for k in ('注文','決済','付与上限','要エントリー','対象ストア','対象商品','指定支払い','条件')):break
            details.append(nxt)
        joined=' '.join(details)
        target_store_limited='対象ストア限定' in joined or '対象ストア・商品限定' in joined
        if 'ボーナスストアPlus' in title:rule='bonus_plus_member' if 'さらに+2%' in title else ('preferred_bonus_store' if '優良ストア' in title else 'campaign_target_store')
        else:rule='campaign_target_store' if target_store_limited else 'all'
        key=(norm(title),value.get('rate'),value.get('rate_label'))
        if key in seen:continue
        seen.add(key)
        rows.append({'title':title,'rate':value.get('rate'),'rate_label':value.get('rate_label'),'is_max':value.get('is_max',False),'is_total':value.get('is_total',False),'informational':value.get('informational',False),'dates':[ref.isoformat()],'conditions':details,'source':DAILYBONUS_URL,'source_url':source_url_for_today(title),'entry_required':'要エントリー' in joined,'target_store_limited':target_store_limited,'eligibility_rule':rule,'rankable':not value.get('informational') and not value.get('is_total'),'same_day_discovery':True})
    return rows,True


def merge_today_campaigns(existing:list[dict],today_rows:list[dict]):
    out=[dict(x) for x in existing];index={(norm(x.get('title','')),x.get('rate'),x.get('rate_label')):x for x in out}
    for incoming in today_rows:
        key=(norm(incoming.get('title','')),incoming.get('rate'),incoming.get('rate_label'));row=index.get(key)
        if row is None:
            row=dict(incoming);row['dates']=list(incoming.get('dates',[]));row['conditions']=list(incoming.get('conditions',[]));out.append(row);index[key]=row
        else:
            row['dates']=sorted(set((row.get('dates') or [])+(incoming.get('dates') or [])))
            row['conditions']=list(dict.fromkeys((row.get('conditions') or [])+(incoming.get('conditions') or [])))
            row['same_day_discovery']=True
    out=[x for x in out if x.get('dates')];out.sort(key=lambda x:(x['dates'][0],x.get('title','')));return out


async def collect_today_campaigns(page,reference:date|None=None):
    result={'source':DAILYBONUS_URL,'campaigns':[],'errors':[],'marker_found':False}
    try:
        resp=await page.goto(DAILYBONUS_URL,wait_until='domcontentloaded',timeout=45000)
        if resp and resp.status>=400:raise RuntimeError(f'HTTP {resp.status}')
        await page.wait_for_timeout(500);body=await page.locator('body').inner_text(timeout=15000)
        rows,marker=parse_today_campaigns(body,reference);result['campaigns']=rows;result['marker_found']=marker
        if not marker:raise RuntimeError('Official daily bonus page did not expose the 本日開催 section')
    except Exception as e:result['errors'].append({'message':clean(repr(e))[:500]})
    return result
