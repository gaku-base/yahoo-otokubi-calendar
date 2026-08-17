from __future__ import annotations
import argparse, json, math, re, unicodedata
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_PATH=ROOT/'data'/'bonus.json'
VERSION='0.8.0'
FORMAT='indexed-v1'
MAX_BYTES=6*1024*1024

def norm_name(s:str)->str:
    s=unicodedata.normalize('NFKC',s or '').lower()
    return re.sub(r'[\s\-_・･/／]+','',s)

def validate(out):
    if out.get('format')!=FORMAT: raise ValueError('wrong compact format')
    catalog=out.get('store_catalog',[]); dates=set(); identities=set()
    for i,c in enumerate(catalog):
        if not isinstance(c,list) or len(c)<2: raise ValueError(f'invalid catalog row {i}')
        name=(c[0] or '').strip(); slug=(c[1] or '').strip().lower()
        if not name: raise ValueError(f'empty catalog name {i}')
        key=('s:'+slug) if slug else ('n:'+norm_name(name))
        if key in identities: raise ValueError(f'duplicate catalog identity {key}')
        identities.add(key)
    for d in out.get('days',[]):
        date=d.get('date')
        if not date or date in dates: raise ValueError(f'invalid/duplicate day {date}')
        dates.add(date); seen=set()
        for offer in d.get('offers',[]):
            if not isinstance(offer,list) or len(offer)!=2: raise ValueError('invalid offer row')
            sid,rate=offer
            if not isinstance(sid,int) or sid<0 or sid>=len(catalog): raise ValueError('invalid store id')
            if sid in seen: raise ValueError('duplicate store id in day')
            seen.add(sid)
            rate=float(rate)
            if not math.isfinite(rate) or rate<0 or rate>100: raise ValueError('invalid rate')
    return out

def compact_full(src):
    out={'schema':src.get('schema'),'version':VERSION,'format':FORMAT,'source':src.get('source'),'updated_at':src.get('updated_at'),'errors':src.get('errors',[]),'validation':src.get('validation',{}),'store_catalog':[],'days':[]}
    catalog_index={}
    def store_id(name,slug):
        key=('s:'+slug) if slug else ('n:'+norm_name(name))
        if key not in catalog_index:
            catalog_index[key]=len(out['store_catalog']); out['store_catalog'].append([name,slug])
        return catalog_index[key]
    for d in src.get('days',[]):
        diag=d.get('diagnostics') or {}
        row={'date':d.get('date'),'url':d.get('url'),'label':d.get('label'),'status':d.get('status'),'rates':d.get('rates',[]),'offers':[],'diagnostics':{'categories_total':diag.get('categories_total',0),'categories_succeeded':diag.get('categories_succeeded',0),'categories_failed':diag.get('categories_failed',0),'stores_total':diag.get('stores_total',len(d.get('stores',[]))),'count_warnings':len(diag.get('count_warnings',[]))}}
        if d.get('error'): row['error']=d['error']
        best={}
        for s in d.get('stores',[]):
            name=(s.get('name') or '').strip(); slug=(s.get('slug') or '').strip().lower(); rate=s.get('rate')
            if not name or rate is None: continue
            sid=store_id(name,slug); rate=float(rate)
            if sid not in best or rate>best[sid]: best[sid]=rate
        row['offers']=[[sid,rate] for sid,rate in best.items()]
        row['diagnostics']['stores_unique']=len(row['offers']); out['days'].append(row)
    return out

def compact(src):
    if src.get('format')==FORMAT and isinstance(src.get('store_catalog'),list):
        out=json.loads(json.dumps(src,ensure_ascii=False)); out['version']=VERSION
        return validate(out)
    return validate(compact_full(src))

def write_atomic(path:Path,raw:bytes):
    path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+'.tmp'); tmp.write_bytes(raw); tmp.replace(path)

def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,default=DEFAULT_PATH); ap.add_argument('--output',type=Path,default=None); args=ap.parse_args(argv)
    inp=args.input; outp=args.output or inp; src=json.loads(inp.read_text(encoding='utf-8')); out=compact(src)
    raw=json.dumps(out,ensure_ascii=False,separators=(',',':')).encode('utf-8')
    if len(raw)>MAX_BYTES: raise SystemExit(f'compact bonus.json still too large: {len(raw)} bytes > {MAX_BYTES}')
    if out.get('validation',{}).get('ok') is not True: raise SystemExit('refusing to publish client data whose source validation is not OK')
    write_atomic(outp,raw)
    print(json.dumps({'version':VERSION,'compact_bytes':len(raw),'days':len(out.get('days',[])),'catalog':len(out.get('store_catalog',[])),'offers':sum(len(d.get('offers',[])) for d in out.get('days',[]))},ensure_ascii=False))

if __name__=='__main__': main()
