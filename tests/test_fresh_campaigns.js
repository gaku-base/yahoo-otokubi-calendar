const assert=require('assert');
const F=require('../docs/fresh_campaigns.js');

const oldData={updated_at:'2026-08-19T08:36:25+09:00',campaigns:[{title:'旧データ'}]};
const freshData={updated_at:'2026-08-19T08:44:22+09:00',campaigns:[{title:'ハッピー24アワー',rate:4,dates:['2026-08-19']}]};

let r=F.selectFresh(oldData,freshData);
assert.strictEqual(r.source,'main');assert.strictEqual(r.changed,true);assert.strictEqual(r.data.campaigns[0].title,'ハッピー24アワー');
r=F.selectFresh(freshData,oldData);assert.strictEqual(r.source,'local');assert.strictEqual(r.changed,false);
r=F.selectFresh(oldData,{bad:true});assert.strictEqual(r.source,'local');

(async()=>{
  let current=oldData,changed=0;
  const out=await F.refreshFromMain({
    hostname:'gaku-base.github.io',
    getCurrent:()=>current,
    setCurrent:v=>{current=v},
    onChanged:()=>{changed++},
    fetcher:async()=>({ok:true,json:async()=>freshData})
  });
  assert.strictEqual(out.source,'main');assert.strictEqual(changed,1);assert.strictEqual(current.campaigns[0].title,'ハッピー24アワー');
  const skipped=await F.refreshFromMain({hostname:'localhost',fetcher:async()=>{throw new Error('should not run')}});
  assert.strictEqual(skipped.skipped,true);
  console.log('fresh campaign fallback: PASS');
})().catch(e=>{console.error(e);process.exit(1)});
