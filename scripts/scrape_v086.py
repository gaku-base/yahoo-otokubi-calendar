from __future__ import annotations
import asyncio
import scrape_v066 as base

# Yahoo's category selector can leave previously rendered store links in the DOM.
# They are not part of the currently displayed category, but the old parser read
# every store.shopping.yahoo.co.jp anchor and could therefore carry a shop into
# dates/categories where it was not actually listed. Only visible headings and
# visible store links are authoritative for the selected category.
async def visible_dom_store_rows(page):
    rows=await page.evaluate(r'''() => {
      function visible(el){
        if(!el)return false;
        const s=getComputedStyle(el);
        return s.display!=='none' && s.visibility!=='hidden' && s.opacity!=='0' && el.getClientRects().length>0;
      }
      const nodes=[...document.querySelectorAll('h1,h2,h3,h4,h5,h6,a')];
      let rate=null; const out=[];
      for(const el of nodes){
        if(!visible(el)) continue;
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
    return base.dedupe([dict(x,slug=base.slug(x.get('url',''))) for x in rows])

base.dom_store_rows=visible_dom_store_rows

import scrape_v075 as previous
previous.VERSION='0.7.6'

if __name__=='__main__':
    asyncio.run(previous.main())
