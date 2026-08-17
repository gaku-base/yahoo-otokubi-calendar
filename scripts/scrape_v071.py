from __future__ import annotations
import asyncio,json
from datetime import datetime,timedelta,timezone
from pathlib import Path
from playwright.async_api import async_playwright
import scrape as legacy
import scrape_v066 as bonusmod
from calendar_campaigns import collect_calendar,merge_safe_guide

ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data';DATA.mkdir(exist_ok=True)
JST=timezone(timedelta(hours=9));VERSION='0.7.1';SCHEMA=5

def validate_campaigns(campaigns:dict):
    issues=[];rows=campaigns.get('campaigns',[])
    if not rows:issues.append('Official bonus calendar produced no point campaigns')
    bad=('クーポン','くじ','抽選','対象商品購入')
    noisy=[c.get('title','') for c in rows if any(x in c.get('title','') for x in bad)]
    if noisy:issues.append(f'Non-point/noisy campaigns leaked into calendar: {noisy[:5]}')
    dates=[d for c in rows for d in c.get('dates',[])]
    if not dates:issues.append('Campaign calendar has no dates')
    for c in rows:
        rate=c.get('rate')
        if rate is not None and not (0<float(rate)<=30):issues.append(f"Invalid campaign rate: {c.get('title')} {rate}")
    return issues

async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
        ctx=await browser.new_context(locale='ja-JP',timezone_id='Asia/Tokyo',user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/139 Safari/537.36')
        page=await ctx.new_page();bonus=await bonusmod.collect_bonus(page)
        cal_page=await ctx.new_page();calendar=await collect_calendar(cal_page);await cal_page.close()
        raw_guide=await legacy.collect_guide(browser)
        await browser.close()
    rows=merge_safe_guide(calendar.get('campaigns',[]),raw_guide)
    campaigns={
        'schema':SCHEMA,'version':VERSION,
        'source':'https://shopping.yahoo.co.jp/promotion/campaign/dailybonus/calendar/',
        'fallback_source':raw_guide.get('source'),
        'updated_at':datetime.now(JST).isoformat(),'campaigns':rows,
        'errors':list(calendar.get('errors',[]))
    }
    if raw_guide.get('errors') and not rows:campaigns['errors'].extend(raw_guide['errors'])
    bonus['version']=VERSION;bonus['schema']=SCHEMA
    issues=bonusmod.validate(bonus,campaigns).get('issues',[])+validate_campaigns(campaigns)
    counts={
        'days':len(bonus.get('days',[])),
        'ok':sum(d.get('status')=='ok' for d in bonus.get('days',[])),
        'partial':sum(d.get('status')=='partial' for d in bonus.get('days',[])),
        'bad':sum(d.get('status') in ('parse_error','fetch_error') for d in bonus.get('days',[])),
        'stores':sum(len(d.get('stores',[])) for d in bonus.get('days',[])),
        'categories':sum(d.get('diagnostics',{}).get('categories_total',0) for d in bonus.get('days',[])),
        'count_warnings':sum(len(d.get('diagnostics',{}).get('count_warnings',[])) for d in bonus.get('days',[])),
        'campaigns':len(rows),'campaign_dates':len({d for c in rows for d in c.get('dates',[])})
    }
    validation={'ok':not issues,'issues':issues[:50],'counts':counts}
    bonus['validation']=validation;campaigns['validation']=validation
    (DATA/'bonus.json').write_text(json.dumps(bonus,ensure_ascii=False,indent=2),encoding='utf-8')
    (DATA/'campaigns.json').write_text(json.dumps(campaigns,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(validation,ensure_ascii=False))
    if not validation['ok']:raise SystemExit(2)

if __name__=='__main__':asyncio.run(main())
