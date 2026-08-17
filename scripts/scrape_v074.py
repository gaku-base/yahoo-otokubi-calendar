from __future__ import annotations
import asyncio,json,time,re
from datetime import datetime,timedelta,timezone
from pathlib import Path
from playwright.async_api import async_playwright
import scrape as legacy
import scrape_v066 as base
import scrape_v073 as prev
from calendar_campaigns import collect_calendar,merge_safe_guide

ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data';DATA.mkdir(exist_ok=True)
JST=timezone(timedelta(hours=9));VERSION='0.7.4';SCHEMA=5;CONCURRENCY=6
_AUDIT={}
_ORIGINAL_SELECT_META=base.select_meta
PLACEHOLDER_RE=re.compile(r'^(すべて|全て|全カテゴリ|すべてのカテゴリ|カテゴリーを選択|カテゴリを選択|選択してください)$')

def meaningful_unparsed_option(opt):
    text=base.clean(opt.get('text',''))
    if not text or opt.get('disabled'):return False
    if base.parse_count(text) is not None:return False
    bare=re.sub(r'[：:>*＞\-–—\s]+','',text)
    return not PLACEHOLDER_RE.fullmatch(bare)

def multi_rate_conflicts(stores):
    rates={};names={}
    for s in stores or []:
        name=base.clean(s.get('name',''));slug=(s.get('slug') or '').strip().lower();rate=s.get('rate')
        if not name or rate is None:continue
        key=('s:'+slug) if slug else ('n:'+name.lower());rates.setdefault(key,set()).add(float(rate));names[key]=(name,slug)
    return [{'name':names[k][0],'slug':names[k][1],'rates':sorted(v)} for k,v in rates.items() if len(v)>1]

async def audited_select_meta(page):
    metas=await _ORIGINAL_SELECT_META(page);issues=[];rate_sections=0
    for m in metas:
        if m.get('rate') is None:continue
        rate_sections+=1;opts=m.get('options') or []
        parsed=[o for o in opts if not o.get('disabled') and base.parse_count(o.get('text','')) is not None]
        unparsed=[o for o in opts if meaningful_unparsed_option(o)]
        if unparsed:issues.append({'select_index':m.get('index'),'rate':m.get('rate'),'kind':'unparsed_category_options','options':[base.clean(o.get('text',''))[:120] for o in unparsed[:20]]})
        if len(opts)>1 and not parsed:issues.append({'select_index':m.get('index'),'rate':m.get('rate'),'kind':'no_parseable_category_counts','options':[base.clean(o.get('text',''))[:120] for o in opts[:20]]})
    _AUDIT[id(page)]={'rate_sections':rate_sections,'issues':issues};return metas

base.select_meta=audited_select_meta

async def collect_event(page,date,href,label):
    rec=await prev.collect_event(page,date,href,label);audit=_AUDIT.get(id(page),{'rate_sections':0,'issues':[]});diag=rec.setdefault('diagnostics',{})
    diag['category_option_audit']={'rate_sections':audit.get('rate_sections',0),'issues':audit.get('issues',[])}
    conflicts=multi_rate_conflicts(rec.get('stores',[]));diag['multi_rate_conflicts']=conflicts[:100]
    if audit.get('issues'):
        rec['status']='partial';rec['error']='one or more category options could not be audited; refusing hard not-found decisions'
    if conflicts:
        rec['status']='partial';rec['error']='one or more stores appeared at conflicting BONUS+ rates; refusing to choose a higher rate automatically'
    return rec

async def collect_bonus(page):
    out={'schema':SCHEMA,'version':VERSION,'source':base.LIST_URL,'updated_at':datetime.now(JST).isoformat(),'days':[],'errors':[],'list_diagnostics':{}}
    try:
        resp=await page.goto(base.LIST_URL,wait_until='domcontentloaded',timeout=60000)
        if resp and resp.status>=400:raise RuntimeError(f'HTTP {resp.status}')
        await base.settle(page,450);anchors=await page.locator('a').evaluate_all("els=>els.map(a=>({text:(a.innerText||'').trim(),href:a.href||''}))")
    except Exception as e:
        out['errors'].append({'stage':'list','message':base.clean(repr(e))[:500]});return out
    events=[];seen=set()
    for a in anchors:
        href=a.get('href','');label=base.clean(a.get('text',''))
        if '/promotion/campaign/bsplus/list/event/' not in href or href in seen:continue
        day=legacy.parse_date_from_anchor(label)
        if day:seen.add(href);events.append((day,href,label))
    events.sort(key=lambda x:x[0]);out['list_diagnostics'].update({'event_links':len(events),'concurrency':CONCURRENCY,'strict_count_warning_gate':True,'category_option_audit':True,'multi_rate_conflict_gate':True})
    sem=asyncio.Semaphore(CONCURRENCY)
    async def one(item):
        async with sem:
            p=await page.context.new_page()
            try:return await collect_event(p,*item)
            finally:_AUDIT.pop(id(p),None);prev._LAST_ACCEPTED.pop(id(p),None);await p.close()
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
        cal_page=await ctx.new_page();calendar=await collect_calendar(cal_page);await cal_page.close();raw_guide=await legacy.collect_guide(browser);await browser.close()
    rows=merge_safe_guide(calendar.get('campaigns',[]),raw_guide)
    campaigns={'schema':SCHEMA,'version':VERSION,'source':calendar.get('source'),'fallback_source':raw_guide.get('source'),'updated_at':datetime.now(JST).isoformat(),'campaigns':rows,'errors':calendar.get('errors',[])}
    base_validation=base.validate(bonus,campaigns);issues=list(base_validation.get('issues',[]))+validate_campaigns(campaigns)
    audit_issues=sum(len(d.get('diagnostics',{}).get('category_option_audit',{}).get('issues',[])) for d in bonus.get('days',[]))
    conflicts=sum(len(d.get('diagnostics',{}).get('multi_rate_conflicts',[])) for d in bonus.get('days',[]))
    if audit_issues:issues.append(f'Category option audit issues: {audit_issues}')
    if conflicts:issues.append(f'Multi-rate store conflicts: {conflicts}')
    counts=dict(base_validation.get('counts',{}));counts.update({'campaigns':len(rows),'campaign_dates':len({d for c in rows for d in c.get('dates',[])}),'elapsed_seconds':round(time.monotonic()-started,1),'concurrency':CONCURRENCY,'category_audit_issues':audit_issues,'multi_rate_conflicts':conflicts})
    validation={'ok':not issues,'issues':issues[:50],'counts':counts};bonus['validation']=validation;campaigns['validation']=validation
    (DATA/'bonus.json').write_text(json.dumps(bonus,ensure_ascii=False,indent=2),encoding='utf-8');(DATA/'campaigns.json').write_text(json.dumps(campaigns,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(validation,ensure_ascii=False))
    if not validation['ok']:raise SystemExit(2)

if __name__=='__main__':asyncio.run(main())
