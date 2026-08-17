from pathlib import Path
import json,re
root=Path(__file__).resolve().parents[1]
required=['docs/index.html','docs/styles.css','docs/core.js','docs/app.js','docs/sw.js','docs/manifest.webmanifest','docs/icon.svg','scripts/scrape.py','scripts/scrape_v066.py','scripts/compact_client_data.py','.github/workflows/pages.yml','.github/workflows/refresh.yml','.github/workflows/smoke.yml','tests/smoke_pwa.py']
for f in required: assert (root/f).exists(),f
html=(root/'docs/index.html').read_text()
assert html.index('core.js') < html.index('app.js')
assert 'class="workspace"' in html and 'class="sidePane"' in html
css=(root/'docs/styles.css').read_text()
assert '@media(min-width:980px)' in css and 'grid-template-columns:minmax(0,1fr) 360px' in css
assert '.selected{' in css
manifest=json.loads((root/'docs/manifest.webmanifest').read_text())
assert manifest.get('display') in ('standalone','fullscreen','minimal-ui')
sw=(root/'docs/sw.js').read_text()
assert 'core.js' in sw and 'app.js' in sw
assert "DATA_CACHE='otokubi-data-v1'" in sw
assert "u.search=''" in sw and 'cache.put(key,res.clone())' in sw and 'cache.match(key)' in sw
assert "fetch(req,{cache:'no-store'})" in sw
assert 'self.skipWaiting()' in sw and 'self.clients.claim()' in sw
app=(root/'docs/app.js').read_text()
assert 'Promise.allSettled' in app
assert 'BONUS+更新失敗（前回データを表示）' in app
assert 'キャンペーン更新失敗（前回データを表示）' in app
print('package integrity: PASS')
