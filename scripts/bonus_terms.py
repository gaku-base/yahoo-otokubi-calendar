from __future__ import annotations
import re,unicodedata

URL='https://shopping.yahoo.co.jp/promotion/campaign/bsplus/'

def clean(s:str)->str:return re.sub(r'[ \t\r\f\v]+',' ',s or '').strip()

def rate_key(rate:float)->str:
    n=float(rate)
    return str(int(n)) if n.is_integer() else f'{n:g}'

def parse_rate_caps(text:str)->dict[str,int]:
    raw=unicodedata.normalize('NFKC',text or '')
    starts=list(re.finditer(r'企画名\s*\n?\s*ボーナスストアPlus\s*\+\s*(\d{1,2}(?:\.\d+)?)\s*%',raw,re.I))
    out={}
    for i,m in enumerate(starts):
        end=starts[i+1].start() if i+1<len(starts) else min(len(raw),m.end()+12000)
        block=raw[m.start():end]
        cap=re.search(r'付与上限(?:数)?[\s\S]{0,220}?([0-9][0-9,]*)\s*円相当',block)
        if not cap:continue
        value=int(cap.group(1).replace(',',''))
        if value<=0:continue
        out[rate_key(float(m.group(1)))]=value
    return out

async def collect_rate_caps(page):
    result={'source':URL,'rate_caps':{},'errors':[]}
    try:
        resp=await page.goto(URL,wait_until='domcontentloaded',timeout=45000)
        if resp and resp.status>=400:raise RuntimeError(f'HTTP {resp.status}')
        await page.wait_for_timeout(300)
        text=await page.locator('body').inner_text(timeout=15000)
        result['rate_caps']=parse_rate_caps(text)
        if not result['rate_caps']:raise RuntimeError('no BONUS+ rate caps parsed from official terms')
    except Exception as e:
        result['errors'].append({'message':clean(repr(e))[:500]})
    return result
