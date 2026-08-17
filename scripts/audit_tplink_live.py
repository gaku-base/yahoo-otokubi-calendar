from __future__ import annotations
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import scrape as legacy
import scrape_v066 as base

TARGET_SLUG='tplink'
TARGET_DATES=['2026-08-17','2026-08-18','2026-08-19','2026-08-20','2026-08-21','2026-08-22','2026-08-23']


def source_rates():
    data=json.loads((ROOT/'data/bonus.json').read_text(encoding='utf-8'))
    out={}
    for d in data.get('days',[]):
        if d.get('date') not in TARGET_DATES: continue
        hits=[]
        for s in d.get('stores',[]):
            if (s.get('slug') or '').lower()==TARGET_SLUG:
                hits.append({'rate':float(s.get('rate',0)),'name':s.get('name'),'categories':s.get('categories',[])})
        out[d.get('date')]=hits
    return out

async def event_links(page):
    await page.goto(base.LIST_URL,wait_until='domcontentloaded',timeout=60000)
    await page.wait_for_timeout(700)
    anchors=await page.locator('a').evaluate_all("els=>els.map(a=>({text:(a.innerText||'').trim(),href:a.href||''}))")
    out={}
    for a in anchors:
        href=a.get('href',''); label=base.clean(a.get('text',''))
        if '/promotion/campaign/bsplus/list/event/' not in href: continue
        date=legacy.parse_date_from_anchor(label)
        if date in TARGET_DATES: out[date]=(href,label)
    return out

async def exact_hits(page,rate):
    rows=await base.dom_store_rows(page)
    return [r for r in rows if (r.get('slug') or '').lower()==TARGET_SLUG and float(r.get('rate',-1))==float(rate)]

async def audit_event(context,date,href,label):
    page=await context.new_page()
    result={'date':date,'url':href,'label':label,'complete':True,'hits':[],'failures':[],'categories_checked':0}
    try:
        resp=await page.goto(href,wait_until='domcontentloaded',timeout=60000)
        if resp and resp.status>=400: raise RuntimeError(f'HTTP {resp.status}')
        await page.wait_for_timeout(700)
        metas=[m for m in await base.select_meta(page) if m.get('rate') is not None]
        if not metas: raise RuntimeError('no rate/category sections')
        for m in metas:
            rate=float(m['rate'])
            for opt in m.get('options',[]):
                if opt.get('disabled'): continue
                expected=base.parse_count(opt.get('text',''))
                if expected is None: continue
                result['categories_checked']+=1
                if expected==0: continue
                category=base.clean(opt.get('text',''))
                ok=False; last=[]; counts=[]
                for attempt in range(4):
                    await base.choose_option(page,m['index'],opt)
                    await page.wait_for_timeout(250*(attempt+1))
                    rows=[r for r in await base.dom_store_rows(page) if float(r.get('rate',-1))==rate]
                    rows=base.dedupe(rows); counts.append(len(rows)); last=rows
                    if abs(len(rows)-expected)<=base.count_tolerance(expected):
                        ok=True; break
                if not ok:
                    result['complete']=False
                    result['failures'].append({'rate':rate,'category':category,'expected':expected,'counts':counts})
                    continue
                for r in last:
                    if (r.get('slug') or '').lower()==TARGET_SLUG:
                        result['hits'].append({'rate':rate,'name':r.get('name'),'category':category,'url':r.get('url')})
        uniq={}
        for h in result['hits']:
            uniq[(h['rate'],h['category'])]=h
        result['hits']=list(uniq.values())
    except Exception as e:
        result['complete']=False;result['error']=repr(e)
    finally:
        await page.close()
    return result

async def main():
    src=source_rates()
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
        context=await browser.new_context(locale='ja-JP',timezone_id='Asia/Tokyo',user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/139 Safari/537.36')
        list_page=await context.new_page(); links=await event_links(list_page); await list_page.close()
        missing=[d for d in TARGET_DATES if d not in links]
        results=[]
        for date in TARGET_DATES:
            if date not in links:
                results.append({'date':date,'complete':False,'error':'event link missing','hits':[],'categories_checked':0});continue
            href,label=links[date]
            rec=await audit_event(context,date,href,label);results.append(rec)
            print('AUDIT_DAY '+json.dumps(rec,ensure_ascii=False),flush=True)
        await browser.close()
    comparisons=[]
    mismatch=False
    for rec in results:
        live=sorted({float(x['rate']) for x in rec.get('hits',[])}) if rec.get('complete') else None
        stored=sorted({float(x['rate']) for x in src.get(rec['date'],[])})
        same=(live is not None and live==stored)
        if not same:mismatch=True
        comparisons.append({'date':rec['date'],'stored_rates':stored,'live_rates':live,'complete':rec.get('complete',False),'same':same,'categories_checked':rec.get('categories_checked',0),'failures':len(rec.get('failures',[]))})
    report={'target':TARGET_SLUG,'source':src,'comparisons':comparisons,'missing_event_links':missing,'mismatch':mismatch}
    print('AUDIT_REPORT '+json.dumps(report,ensure_ascii=False),flush=True)
    (ROOT/'artifacts').mkdir(exist_ok=True)
    (ROOT/'artifacts/tplink-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    if any(not r.get('complete') for r in results):raise SystemExit(3)
    if mismatch:raise SystemExit(2)

if __name__=='__main__':asyncio.run(main())
