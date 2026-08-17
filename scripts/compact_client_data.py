from __future__ import annotations
import json, re, unicodedata
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/'data'/'bonus.json'
MAX_BYTES=8*1024*1024

def norm_name(s: str) -> str:
    s=unicodedata.normalize('NFKC',s or '').lower()
    return re.sub(r'[\s\-_・･/／]+','',s)

def compact(src):
    out={
        'schema':src.get('schema'),
        'version':'0.6.4',
        'format':'indexed-v1',
        'source':src.get('source'),
        'updated_at':src.get('updated_at'),
        'errors':src.get('errors',[]),
        'validation':src.get('validation',{}),
        'store_catalog':[],
        'days':[]
    }
    catalog_index={}
    def store_id(name,slug):
        key=('s:'+slug) if slug else ('n:'+norm_name(name))
        if key not in catalog_index:
            catalog_index[key]=len(out['store_catalog'])
            out['store_catalog'].append([name,slug])
        return catalog_index[key]

    for d in src.get('days',[]):
        diag=d.get('diagnostics') or {}
        row={
            'date':d.get('date'),
            'url':d.get('url'),
            'label':d.get('label'),
            'status':d.get('status'),
            'rates':d.get('rates',[]),
            'offers':[],
            'diagnostics':{
                'categories_total':diag.get('categories_total',0),
                'categories_succeeded':diag.get('categories_succeeded',0),
                'categories_failed':diag.get('categories_failed',0),
                'stores_total':diag.get('stores_total',len(d.get('stores',[])))
            }
        }
        if d.get('error'): row['error']=d['error']
        best={}
        for s in d.get('stores',[]):
            name=(s.get('name') or '').strip(); slug=(s.get('slug') or '').strip().lower(); rate=s.get('rate')
            if not name or rate is None: continue
            sid=store_id(name,slug)
            rate=float(rate)
            if sid not in best or rate>best[sid]: best[sid]=rate
        row['offers']=[[sid,rate] for sid,rate in best.items()]
        out['days'].append(row)
    return out

def validate(out):
    if out.get('format')!='indexed-v1': raise SystemExit('wrong compact format')
    catalog=out.get('store_catalog',[])
    for d in out.get('days',[]):
        seen=set()
        for offer in d.get('offers',[]):
            if not isinstance(offer,list) or len(offer)!=2: raise SystemExit('invalid offer row')
            sid,rate=offer
            if not isinstance(sid,int) or sid<0 or sid>=len(catalog): raise SystemExit('invalid store id')
            if sid in seen: raise SystemExit('duplicate store id in day')
            seen.add(sid)
            float(rate)

def main():
    src=json.loads(PATH.read_text(encoding='utf-8'))
    out=compact(src); validate(out)
    raw=json.dumps(out,ensure_ascii=False,separators=(',',':')).encode('utf-8')
    if len(raw)>MAX_BYTES:
        raise SystemExit(f'compact bonus.json still too large: {len(raw)} bytes > {MAX_BYTES}')
    PATH.write_bytes(raw)
    print(json.dumps({'compact_bytes':len(raw),'days':len(out['days']),'catalog':len(out['store_catalog']),'offers':sum(len(d['offers']) for d in out['days'])},ensure_ascii=False))

if __name__=='__main__': main()
