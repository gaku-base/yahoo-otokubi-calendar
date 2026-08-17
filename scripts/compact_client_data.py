from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/'data'/'bonus.json'
MAX_BYTES=25*1024*1024

def compact(src):
    out={
        'schema':src.get('schema'),
        'version':'0.6.3',
        'source':src.get('source'),
        'updated_at':src.get('updated_at'),
        'errors':src.get('errors',[]),
        'validation':src.get('validation',{}),
        'days':[]
    }
    for d in src.get('days',[]):
        diag=d.get('diagnostics') or {}
        row={
            'date':d.get('date'),
            'url':d.get('url'),
            'label':d.get('label'),
            'status':d.get('status'),
            'rates':d.get('rates',[]),
            'stores':[],
            'diagnostics':{
                'categories_total':diag.get('categories_total',0),
                'categories_succeeded':diag.get('categories_succeeded',0),
                'categories_failed':diag.get('categories_failed',0),
                'stores_total':diag.get('stores_total',len(d.get('stores',[])))
            }
        }
        if d.get('error'): row['error']=d['error']
        seen=set()
        for s in d.get('stores',[]):
            name=(s.get('name') or '').strip(); slug=(s.get('slug') or '').strip().lower(); rate=s.get('rate')
            if not name or rate is None: continue
            key=(slug or name, float(rate))
            if key in seen: continue
            seen.add(key)
            row['stores'].append({'name':name,'slug':slug,'rate':float(rate)})
        out['days'].append(row)
    return out

def main():
    src=json.loads(PATH.read_text(encoding='utf-8'))
    out=compact(src)
    raw=json.dumps(out,ensure_ascii=False,separators=(',',':')).encode('utf-8')
    if len(raw)>MAX_BYTES:
        raise SystemExit(f'compact bonus.json still too large: {len(raw)} bytes > {MAX_BYTES}')
    PATH.write_bytes(raw)
    print(json.dumps({'compact_bytes':len(raw),'days':len(out['days']),'stores':sum(len(d['stores']) for d in out['days'])},ensure_ascii=False))

if __name__=='__main__': main()
