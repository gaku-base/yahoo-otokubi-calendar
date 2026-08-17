from __future__ import annotations
import asyncio, json, math, re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse
from playwright.async_api import async_playwright
import scrape as legacy

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'; DATA.mkdir(exist_ok=True)
JST=timezone(timedelta(hours=9))
LIST_URL='https://shopping.yahoo.co.jp/promotion/campaign/bsplus/list/'
SCHEMA=4
VERSION='0.6.6'

BROAD_CAMPAIGN_KEYWORDS=(
    'プレミアムな日曜日','ヤフショ感謝デー','爆買','Brand Week','ブランドウィーク',
    '超PayPay祭','ファーストデイ','買う！買う！サンデー','チャンスタイム'
)
BROAD_CAMPAIGN_EXCLUDES=('クーポン','くじ','対象商品購入','対象商品購入で','ギフトで贈る','ebookjapan','ZOZOTOWN')

def clean(s): return re.sub(r'\s+',' ',s or '').strip()

def slug(url):
    try:
        u=urlparse(url)
        if u.netloc.lower().split(':')[0]=='store.shopping.yahoo.co.jp':
            return (u.path.strip('/').split('/') or [''])[0].lower()
    except Exception:
        pass
    return ''

def parse_count(label):
    m=re.search(r'[（(](\d+)[）)]\s*$',clean(label))
    return int(m.group(1)) if m else None

def count_tolerance(expected:int)->int:
    if expected<=20: return 0
    return max(1, math.ceil(expected*0.005))

def is_broad_campaign(title:str)->bool:
    t=clean(title)
    if not t or any(x.lower() in t.lower() for x in BROAD_CAMPAIGN_EXCLUDES): return False
    return any(x.lower() in t.lower() for x in BROAD_CAMPAIGN_KEYWORDS)

def filter_guide(guide:dict)->dict:
    guide=dict(guide)
    guide['campaigns']=[c for c in guide.get('campaigns',[]) if is_broad_campaign(c.get('title',''))]
    return guide

def dedupe(rows):
    out={}
    for r in rows:
        if not r.get('name') or not r.get('url') or r.get('rate') is None: continue
        r=dict(r); r['name']=clean(r['name']); r['slug']=r.get('slug') or slug(r['url']); r['rate']=float(r['rate'])
        cats=sorted(set(r.get('categories') or ([] if not r.get('category') else [r['category']])))
        r['categories']=cats; r.pop('category',None)
        key=(r['slug'] or r['name'].lower(),r['rate'])
        if key in out:
            out[key]['categories']=sorted(set(out[key].get('categories',[])+cats))
        else:
            out[key]=r
    return list(out.values())

async def settle(page,ms=450):
    await page.wait_for_timeout(ms)

async def dom_store_rows(page):
    rows=await page.evaluate(r'''() => {
      const nodes=[...document.querySelectorAll('h1,h2,h3,h4,h5,h6,a')];
      let rate=null; const out=[];
      for(const el of nodes){
        if(/^H[1-6]$/.test(el.tagName)){
          const m=(el.innerText||'').replace(/\s+/g,' ').match(/\+?\s*(\d{1,2}(?:\.\d+)?)\s*%\s*対象ストア/i);
          if(m) rate=Number(m[1]);
          continue;
        }
        if(rate===null) continue;
        const href=el.href||'';
        let host=''; try{host=new URL(href).hostname.toLowerCase()}catch(e){}
        if(host!=='store.shopping.yahoo.co.jp') continue;
        const name=(el.innerText||el.textContent||'').replace(/\s+/g,' ').trim();
        if(name) out.push({name,url:href,rate});
      }
      return out;
    }''')
    return dedupe([dict(x,slug=slug(x.get('url',''))) for x in rows])

async def select_meta(page):
    return await page.evaluate(r'''() => {
      const all=[...document.querySelectorAll('h1,h2,h3,h4,h5,h6,select')];
      let rate=null,si=0,out=[];
      for(const el of all){
        if(/^H[1-6]$/.test(el.tagName)){
          const m=(el.innerText||'').replace(/\s+/g,' ').match(/\+?\s*(\d{1,2}(?:\.\d+)?)\s*%\s*対象ストア/i);
          if(m) rate=Number(m[1]);
        }else{
          out.push({index:si++,rate,options:[...el.options].map((o,oi)=>({index:oi,value:o.value,text:(o.innerText||o.textContent||'').replace(/\s+/g,' ').trim(),disabled:o.disabled}))});
        }
      }
      return out;
    }''')

async def choose_option(page,select_index,opt):
    sels=page.locator('select')
    if await sels.count()<=select_index: raise RuntimeError('select disappeared')
    sel=sels.nth(select_index)
    try:
        if opt.get('value'):
            await sel.select_option(value=opt['value'],timeout=5000)
        else:
            await sel.select_option(index=opt['index'],timeout=5000)
    except Exception:
        await sel.select_option(index=opt['index'],timeout=5000)
    await settle(page,500)

async def stable_category_rows(page,select_index,opt,rate,max_attempts=5):
    previous=None; got=[]; counts=[]
    for attempt in range(max_attempts):
        await choose_option(page,select_index,opt)
        rows=[r for r in await dom_store_rows(page) if float(r['rate'])==float(rate)]
        got=dedupe(rows)
        sig=tuple(sorted((r.get('slug') or clean(r.get('name')).lower(),float(r['rate'])) for r in got))
        counts.append(len(got))
        if previous is not None and sig==previous:
            return got,True,counts
        previous=sig
        await page.wait_for_timeout(350*(attempt+1))
    return got,False,counts

async def collect_event(page,date,href,label):
    rec={'date':date,'url':href,'label':label,'status':'ok','stores':[],'rates':[],'diagnostics':{'sections':[],'failures':[],'count_warnings':[]}}
    try:
        resp=await page.goto(href,wait_until='domcontentloaded',timeout=60000)
        if resp and resp.status>=400: raise RuntimeError(f'HTTP {resp.status}')
        await settle(page,500)
        metas=[m for m in await select_meta(page) if m.get('rate') is not None]
        initial=await dom_store_rows(page); allrows=list(initial)
        diag=rec['diagnostics']; diag['rate_sections']=len(metas)
        for m in metas:
            rate=float(m['rate'])
            sec={'rate':rate,'select_index':m['index'],'categories_total':0,'categories_succeeded':0,'categories_failed':0,'expected_stores':0,'captured_stores':0,'count_warnings':0}
            options=[]
            for o in m['options']:
                if o.get('disabled'): continue
                cnt=parse_count(o.get('text',''))
                if cnt is None: continue
                options.append((o,cnt))
            sec['categories_total']=len(options); sec['expected_stores']=sum(cnt for _,cnt in options)
            for opt,expected in options:
                category=clean(opt['text'])
                if expected==0:
                    sec['categories_succeeded']+=1; continue
                last_count=0
                try:
                    got,stable,counts=await stable_category_rows(page,m['index'],opt,rate)
                    last_count=len(got)
                    if not got: raise RuntimeError('category yielded zero store rows')
                    delta=last_count-expected; tol=count_tolerance(expected)
                    if abs(delta)>tol:
                        raise RuntimeError(f'expected {expected} stores, captured {last_count}; tolerance {tol}; attempts {counts}')
                    if delta!=0:
                        warning={'rate':rate,'select':m['index'],'category':category,'expected':expected,'captured':last_count,'delta':delta,'tolerance':tol,'stable':stable,'counts':counts}
                        if len(diag['count_warnings'])<100: diag['count_warnings'].append(warning)
                        sec['count_warnings']+=1
                    for r in got: r['categories']=[category]
                    allrows.extend(got); sec['categories_succeeded']+=1; sec['captured_stores']+=len(got)
                except Exception as e:
                    sec['categories_failed']+=1
                    if len(diag['failures'])<80:
                        diag['failures'].append({'rate':rate,'select':m['index'],'category':category,'expected':expected,'captured':last_count,'message':clean(repr(e))[:300]})
            diag['sections'].append(sec)
        stores=dedupe(allrows); rec['stores']=stores; rec['rates']=sorted({float(r['rate']) for r in stores},reverse=True)
        diag['categories_total']=sum(s['categories_total'] for s in diag['sections'])
        diag['categories_succeeded']=sum(s['categories_succeeded'] for s in diag['sections'])
        diag['categories_failed']=sum(s['categories_failed'] for s in diag['sections'])
        diag['stores_total']=len(stores)
        if not metas or not stores:
            rec['status']='parse_error'; rec['error']='rate sections or store links were not parsed'
        elif diag['categories_failed']:
            rec['status']='partial'; rec['error']='one or more categories could not be captured reliably'
        elif diag['categories_succeeded']!=diag['categories_total']:
            rec['status']='partial'; rec['error']='category completeness mismatch'
    except Exception as e:
        rec['status']='fetch_error'; rec['error']=clean(repr(e))[:500]
    return rec

async def collect_bonus(page):
    out={'schema':SCHEMA,'version':VERSION,'source':LIST_URL,'updated_at':datetime.now(JST).isoformat(),'days':[],'errors':[],'list_diagnostics':{}}
    try:
        resp=await page.goto(LIST_URL,wait_until='domcontentloaded',timeout=60000)
        if resp and resp.status>=400: raise RuntimeError(f'HTTP {resp.status}')
        await settle(page,450)
        anchors=await page.locator('a').evaluate_all("els=>els.map(a=>({text:(a.innerText||'').trim(),href:a.href||''}))")
    except Exception as e:
        out['errors'].append({'stage':'list','message':clean(repr(e))[:500]}); return out
    events=[]; seen=set()
    for a in anchors:
        href=a.get('href',''); label=clean(a.get('text',''))
        if '/promotion/campaign/bsplus/list/event/' not in href or href in seen: continue
        date=legacy.parse_date_from_anchor(label)
        if date: seen.add(href); events.append((date,href,label))
    events.sort(key=lambda x:x[0]); out['list_diagnostics']['event_links']=len(events)
    sem=asyncio.Semaphore(3)
    async def one(item):
        async with sem:
            p=await page.context.new_page()
            try: return await collect_event(p,*item)
            finally: await p.close()
    out['days']=await asyncio.gather(*(one(e) for e in events)); out['days'].sort(key=lambda x:x['date'])
    return out

def validate(bonus,guide):
    issues=[]; days=bonus.get('days',[])
    if not days: issues.append('BONUS+ day list is empty')
    incomplete=[d for d in days if d.get('status')!='ok']
    if incomplete: issues.append(f'Incomplete BONUS+ days: {len(incomplete)}')
    if len({d.get('date') for d in days})!=len(days): issues.append('Duplicate BONUS+ dates detected')
    for d in days:
        dg=d.get('diagnostics',{})
        if d.get('status')=='ok' and dg.get('categories_succeeded')!=dg.get('categories_total'):
            issues.append(f"Completeness invariant failed: {d.get('date')}")
    by={d.get('date'):d for d in days}; d=by.get('2026-08-17')
    if d:
        hit=[s for s in d.get('stores',[]) if s.get('slug')=='tplink' and float(s.get('rate',-1))==5]
        if not hit: issues.append('Regression failed: 2026-08-17 tplink expected +5%')
    if guide.get('errors'): issues.append('Guide fetch/parser reported errors')
    return {'ok':not issues,'issues':issues,'counts':{'days':len(days),'ok':sum(d.get('status')=='ok' for d in days),'partial':sum(d.get('status')=='partial' for d in days),'bad':sum(d.get('status') in ('parse_error','fetch_error') for d in days),'campaigns':len(guide.get('campaigns',[])),'stores':sum(len(d.get('stores',[])) for d in days),'categories':sum(d.get('diagnostics',{}).get('categories_total',0) for d in days),'count_warnings':sum(len(d.get('diagnostics',{}).get('count_warnings',[])) for d in days)}}

async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True,args=['--no-sandbox'])
        ctx=await browser.new_context(locale='ja-JP',timezone_id='Asia/Tokyo',user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/139 Safari/537.36')
        page=await ctx.new_page(); bonus=await collect_bonus(page)
        guide=filter_guide(await legacy.collect_guide(browser)); guide['version']=VERSION
        await browser.close()
    validation=validate(bonus,guide); bonus['validation']=validation; guide['validation']=validation
    (DATA/'bonus.json').write_text(json.dumps(bonus,ensure_ascii=False,indent=2),encoding='utf-8')
    (DATA/'campaigns.json').write_text(json.dumps(guide,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(validation,ensure_ascii=False))
    if not validation['ok']: raise SystemExit(2)

if __name__=='__main__': asyncio.run(main())
