from __future__ import annotations
import asyncio,json,time
from datetime import datetime,timedelta,timezone
from pathlib import Path
from playwright.async_api import async_playwright
import scrape as legacy
import scrape_v066 as validator
import scrape_v073 as state073
import scrape_v074 as strict
from calendar_campaigns import collect_calendar,merge_safe_guide

ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data';DATA.mkdir(exist_ok=True)
JST=timezone(timedelta(hours=9));VERSION='0.7.5';SCHEMA=5;RECOVERY_ATTEMPTS=2;REQUIRED_CLEAN_CONFIRMATIONS=2

def needs_recovery(rec):return rec.get('status')!='ok'

def recovery_score(rec):
    dg=rec.get('diagnostics',{});failed=int(dg.get('categories_failed',0) or 0);audit=len(dg.get('category_option_audit',{}).get('issues',[]) or []);conf=len(dg.get('multi_rate_conflicts',[]) or [])
    status_rank={'ok':3,'partial':2,'parse_error':1,'fetch_error':0}.get(rec.get('status'),0)
    return (status_rank,-failed,-audit,-conf,int(dg.get('categories_succeeded',0) or 0),int(dg.get('stores_total',0) or 0))

def choose_better(a,b):return b if recovery_score(b)>recovery_score(a) else a

def clean_confirmation(rec):
    dg=rec.get('diagnostics',{})
    return rec.get('status')=='ok' and not dg.get('categories_failed',0) and not dg.get('count_warnings') and not dg.get('category_option_audit',{}).get('issues') and not dg.get('multi_rate_conflicts')

async def retry_event(context,original,attempts=RECOVERY_ATTEMPTS):
    best=original;history=[];clean=[]
    for n in range(1,attempts+1):
        p=await context.new_page()
        try:rec=await strict.collect_event(p,original.get('date'),original.get('url'),original.get('label'))
        finally:strict._AUDIT.pop(id(p),None);state073._LAST_ACCEPTED.pop(id(p),None);await p.close()
        ok=clean_confirmation(rec)
        history.append({'attempt':n,'status':rec.get('status'),'clean':ok,'error':rec.get('error'),'categories_failed':rec.get('diagnostics',{}).get('categories_failed',0),'stores_total':rec.get('diagnostics',{}).get('stores_total',0)})
        best=choose_better(best,rec)
        if ok:clean.append(rec)
    confirmed=len(clean)>=REQUIRED_CLEAN_CONFIRMATIONS
    if confirmed:
        best=clean[-1]
    else:
        if best.get('status')=='ok':
            best=dict(best);best['diagnostics']=dict(best.get('diagnostics',{}));best['status']='partial';best['error']='recovery produced fewer than two clean confirmations; refusing hard not-found decisions'
    dg=best.setdefault('diagnostics',{});dg['recovery']={'initial_status':original.get('status'),'attempts':history,'clean_confirmations':len(clean),'required_clean_confirmations':REQUIRED_CLEAN_CONFIRMATIONS,'recovered':confirmed}
    return best

async def collect_bonus_with_recovery(page):
    out=await strict.collect_bonus(page);bad=[d for d in out.get('days',[]) if needs_recovery(d)]
    out.setdefault('list_diagnostics',{})['recovery_candidates']=len(bad);out['list_diagnostics']['recovery_attempt_limit']=RECOVERY_ATTEMPTS;out['list_diagnostics']['required_clean_confirmations']=REQUIRED_CLEAN_CONFIRMATIONS
    if not bad:return out
    sem=asyncio.Semaphore(2);bydate={d.get('date'):d for d in out['days']}
    async def one(rec):
        async with sem:return await retry_event(page.context,rec)
    recovered=await asyncio.gather(*(one(r) for r in bad))
    for r in recovered:bydate[r.get('date')]=r
    out['days']=[bydate[d.get('date')] for d in out['days']]
    out['list_diagnostics']['recovered_days']=sum(bool(d.get('diagnostics',{}).get('recovery',{}).get('recovered')) for d in out['days']);out['list_diagnostics']['remaining_incomplete']=sum(d.get('status')!='ok' for d in out['days'])
    return out

def validate_campaigns(campaigns):
    issues=[];rows=campaigns.get('campaigns',[])
    if not rows:issues.append('Official bonus calendar produced no campaigns')
    if not any(c.get('dates') for c in rows):issues.append('Campaign calendar has no dates')
    for c in rows:
        if any(x in c.get('title','') for x in ('クーポン','くじ','抽選')) and not c.get('informational'):
            issues.append(f"Non-point event was not marked informational: {c.get('title')}")
        if c.get('eligibility_rule')=='bonus_plus_member' and not c.get('target_store_limited'):
            issues.append(f"BONUS+ membership campaign lost target-store flag: {c.get('title')}")
    return issues

async def main():
    started=time.monotonic()
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
        ctx=await browser.new_context(locale='ja-JP',timezone_id='Asia/Tokyo',user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/139 Safari/537.36')
        page=await ctx.new_page();bonus=await collect_bonus_with_recovery(page)
        cal_page=await ctx.new_page();calendar=await collect_calendar(cal_page);await cal_page.close();raw_guide=await legacy.collect_guide(browser);await browser.close()
    rows=merge_safe_guide(calendar.get('campaigns',[]),raw_guide)
    campaigns={'schema':SCHEMA,'version':VERSION,'source':calendar.get('source'),'fallback_source':raw_guide.get('source'),'updated_at':datetime.now(JST).isoformat(),'campaigns':rows,'errors':calendar.get('errors',[])}
    base_validation=validator.validate(bonus,campaigns);issues=list(base_validation.get('issues',[]))+validate_campaigns(campaigns)
    audit_issues=sum(len(d.get('diagnostics',{}).get('category_option_audit',{}).get('issues',[])) for d in bonus.get('days',[]));conflicts=sum(len(d.get('diagnostics',{}).get('multi_rate_conflicts',[])) for d in bonus.get('days',[]))
    if audit_issues:issues.append(f'Category option audit issues: {audit_issues}')
    if conflicts:issues.append(f'Multi-rate store conflicts: {conflicts}')
    recovered=sum(bool(d.get('diagnostics',{}).get('recovery',{}).get('recovered')) for d in bonus.get('days',[]));recovery_attempts=sum(len(d.get('diagnostics',{}).get('recovery',{}).get('attempts',[])) for d in bonus.get('days',[]))
    counts=dict(base_validation.get('counts',{}));counts.update({'campaigns':len(rows),'campaign_dates':len({d for c in rows for d in c.get('dates',[])}),'informational_campaigns':sum(bool(c.get('informational')) for c in rows),'elapsed_seconds':round(time.monotonic()-started,1),'concurrency':strict.CONCURRENCY,'category_audit_issues':audit_issues,'multi_rate_conflicts':conflicts,'recovered_days':recovered,'recovery_attempts':recovery_attempts})
    validation={'ok':not issues,'issues':issues[:50],'counts':counts};bonus['version']=VERSION;bonus['schema']=SCHEMA;bonus['validation']=validation;campaigns['validation']=validation
    (DATA/'bonus.json').write_text(json.dumps(bonus,ensure_ascii=False,indent=2),encoding='utf-8');(DATA/'campaigns.json').write_text(json.dumps(campaigns,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(validation,ensure_ascii=False))
    if not validation['ok']:raise SystemExit(2)

if __name__=='__main__':asyncio.run(main())
