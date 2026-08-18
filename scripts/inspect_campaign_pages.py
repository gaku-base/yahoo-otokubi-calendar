from __future__ import annotations
import asyncio,json,re
from urllib.parse import urlparse
from playwright.async_api import async_playwright

PAGES={
  'buybuy':'https://shopping.yahoo.co.jp/promotion/campaign/buybuy/',
  'lypsunday':'https://shopping.yahoo.co.jp/promotion/campaign/lypsunday/',
  'pointrank':'https://shopping.yahoo.co.jp/promotion/campaign/pointrank/',
  'dailybonus':'https://shopping.yahoo.co.jp/promotion/campaign/dailybonus/',
}
KEYWORDS=['さらに+2','さらに＋2','優良ストア','対象ストア','プレミアムな日曜日','ヤフショ感謝デー']

def slug(url:str)->str:
  try:
    u=urlparse(url)
    if u.hostname=='store.shopping.yahoo.co.jp': return u.path.strip('/').split('/')[0].lower()
  except Exception: pass
  return ''

async def inspect(page,name,url):
  r=await page.goto(url,wait_until='domcontentloaded',timeout=45000)
  await page.wait_for_timeout(1200)
  data=await page.evaluate(r'''(keywords)=>{
    const norm=s=>(s||'').replace(/\s+/g,' ').trim();
    const headings=[...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].map((e,i)=>({i,tag:e.tagName,text:norm(e.innerText)})).filter(x=>x.text);
    const selects=[...document.querySelectorAll('select')].map((s,i)=>({i,aria:s.getAttribute('aria-label')||'',name:s.name||'',id:s.id||'',options:[...s.options].map((o,j)=>({j,text:norm(o.innerText||o.textContent),value:o.value||'',disabled:o.disabled})).slice(0,80)}));
    const anchors=[...document.querySelectorAll('a[href*="store.shopping.yahoo.co.jp/"]')].map(a=>({text:norm(a.innerText),href:a.href, parent:norm(a.parentElement?.innerText).slice(0,220)}));
    const keywordNodes=[];
    for(const kw of keywords){
      const els=[...document.querySelectorAll('body *')].filter(e=>e.children.length===0 && norm(e.textContent).includes(kw)).slice(0,8);
      for(const e of els){let p=e;const chain=[];for(let d=0;d<5&&p;d++,p=p.parentElement)chain.push({tag:p.tagName,id:p.id||'',cls:String(p.className||'').slice(0,120),text:norm(p.innerText).slice(0,500),storeLinks:[...(p.querySelectorAll?.('a[href*="store.shopping.yahoo.co.jp/"]')||[])].slice(0,20).map(a=>({text:norm(a.innerText),href:a.href}))});keywordNodes.push({kw,chain});}
    }
    return {title:document.title,headings,selects,anchors:anchors.slice(0,500),anchorCount:anchors.length,keywordNodes,body:norm(document.body.innerText).slice(0,6000)};
  }''',KEYWORDS)
  out={'name':name,'url':url,'status':r.status if r else None,**data}
  slugs=[]
  for a in out['anchors']:
    s=slug(a['href'])
    if s and s not in slugs:slugs.append(s)
  out['uniqueStoreSlugsSample']=slugs[:120]
  out['uniqueStoreSlugCountSample']=len(slugs)
  return out

async def main():
  async with async_playwright() as p:
    browser=await p.chromium.launch(headless=True,args=['--no-sandbox'])
    ctx=await browser.new_context(locale='ja-JP',timezone_id='Asia/Tokyo')
    results=[]
    for name,url in PAGES.items():
      page=await ctx.new_page()
      try: results.append(await inspect(page,name,url))
      finally: await page.close()
    await browser.close()
  print(json.dumps(results,ensure_ascii=False,indent=2))

if __name__=='__main__': asyncio.run(main())
