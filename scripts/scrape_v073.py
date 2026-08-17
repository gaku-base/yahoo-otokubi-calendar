from __future__ import annotations
import asyncio,json,time
from datetime import datetime,timedelta,timezone
from pathlib import Path
from playwright.async_api import async_playwright
import scrape as legacy
import scrape_v066 as base
from calendar_campaigns import collect_calendar,merge_safe_guide

ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data';DATA.mkdir(exist_ok=True)
JST=timezone(timedelta(hours=9));VERSION='0.7.3';SCHEMA=5;CONCURRENCY=6
_LAST_ACCEPTED={}

def fast_accept(expected:int|None,captured:int,current_sig,previous_sig,attempt:int)->bool:
    if expected is None or captured<=0:return False
    if abs(captured-expected)>base.count_tolerance(expected):return False
    # If a newly selected category has exactly the same visible store set as the
    # previous category, require a second observation before accepting it. This
    # prevents a same-size stale DOM from being mistaken for the new category.
    if previous_sig is not None and current_sig==previous_sig and attempt==0:return False
    return True

async def safe_fast_category_rows(page,select_index,opt,rate,max_attempts=4):
    expected=base.parse_count(opt.get('text',''));prev_state=_LAST_ACCEPTED.get(id(page));previous_sig=prev_state[1] if prev_state else None
    previous_observation=None;got=[];counts=[]
    for attempt in range(max_attempts):
        await base.choose_option(page,select_index,opt)
        rows=[r for r in await base.dom_store_rows(page) if float(r['rate'])==float(rate)]
        got=base.dedupe(rows);counts.append(len(got))
        sig=tuple(sorted((r.get('slug') or base.clean(r.get('name')).lower(),float(r['rate'])) for r in got))
        if fast_accept(expected,len(got),sig,previous_sig,attempt):
            _LAST_ACCEPTED[id(page)]=(opt.get('value') or opt.get('index'),sig)
            return got,attempt>0,counts
        if previous_observation is not None and sig==previous_observation:
            _LAST_ACCEPTED[id(page)]=(opt.get('value') or opt.get('index'),sig)
            return got,True,counts
        previous_observation=sig
        await page.wait_for_timeout(300*(attempt+1))
    if got:_LAST_ACCEPTED[id(page)]=(opt.get('value') or opt.get('index'),previous_observation)
    return got,False,counts

base.stable_category_rows=safe_fast_category_rows

async def collect_event(page,date,href,label):
    rec=await base.collect_event(page,date,href,label)
    warnings=rec.get('diagnostics',{}).get('count_warnings',[])
    if rec.get('status')=='ok' and warnings:
        rec['status']='partial';rec['error']='category store-count mismatch detected; refusing hard not-found decisions'
    return rec

async def collect_bonus(page):
    out={'schema':SCHEMA,'version':VERSION,'source':base.LIST_URL,'updated_at':datetime.now(JST).isoformat(),'days':[],'errors':[],'list_diagnostics':{}}
    try:
        resp=await page.goto(base.LIST_URL,wait_until='domcontentloaded',timeout=60000)
        if resp and resp.status>=400:raise RuntimeError(f'HTTP {resp.status}')
        await base.settle(page,450)
        anchors=await page.locator('a').evaluate_all("els=>els.map(a=>({text:(a.innerText||'').trim(),href:a.href||''}))")
    except Exception as e:
        out['errors'].append({'stage':'list','message':base.clean(repr(e))[:500]});return out
    events=[];seen=set()
    for a in anchors:
        href=a.get('href','');label=base.clean(a.get('text',''))
        if '/promotion/campaign/bsplus/list/event/' not in href or href in seen:continue
        day=legacy.parse_date_from_anchor(label)
        if day:seen.add(href);events.append((day,href,label))
    events.sort(key=lambda x:x[0]);out['list_diagnostics'].update({'event_links':len(events),'concurrency':CONCURRENCY,'strict_count_warning_gate':True})
    sem=asyncio.Semaphore(CONCURRENCY)
    async def one(item):
        async with sem:
            p=await page.context.new_page()
            try:return await collect_event(p,*item)
            finally:_LAST_ACCEPTED.pop(id(p),None);await p.close()
    out['days']=await asyncio.gather(*(one(e) for e in events));out['days'].sort(key=lambda x:x['date']);return out

def validate_campaigns(campaigns):
    issues=[];rows=campaigns.get('campaigns',[])
    if not rows:issues.append('Official bonus calendar produced no point campaigns')
    if any(any(x in c.get('title','') for x in ('クーポン','くじ','抽選','対象商品購入')) for c in rows):issues.append('Noisy campaign leaked into calendar')
    if not any(c.get('dates') for c in rows):issues.append('Campaign calendar has no dates')
    return issues

async def main():
    started=time.monotonic()
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
        ctx=await browser.new_context(locale='ja-JP',timezone_id='Asia/Tokyo',user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/139 Safari/537.36')
        page=await ctx.new_page();bonus=await collect_bonus(page)
        cal_page=await ctx.new_page();calendar=await collect_calendar(cal_page);await cal_page.close()
        raw_guide=await legacy.collect_guide(browser);await browser.close()
    rows=merge_safe_guide(calendar.get('campaigns',[]),raw_guide)
    campaigns={'schema':SCHEMA,'version':VERSION,'source':calendar.get('source'),'fallback_source':raw_guide.get('source'),'updated_at':datetime.now(JST).isoformat(),'campaigns':rows,'errors':calendar.get('errors',[])}
    base_validation=base.validate(bonus,campaigns);issues=list(base_validation.get('issues',[]))+validate_campaigns(campaigns)
    counts=dict(base_validation.get('counts',{}));counts.update({'campaigns':len(rows),'campaign_dates':len({d for c in rows for d in c.get('dates',[])}),'elapsed_seconds':round(time.monotonic()-started,1),'concurrency':CONCURRENCY})
    validation={'ok':not issues,'issues':issues[:50],'counts':counts};bonus['validation']=validation;campaigns['validation']=validation
    (DATA/'bonus.json').write_text(json.dumps(bonus,ensure_ascii=False,indent=2),encoding='utf-8');(DATA/'campaigns.json').write_text(json.dumps(campaigns,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(validation,ensure_ascii=False))
    if not validation['ok']:raise SystemExit(2)

if __name__=='__main__':asyncio.run(main())
