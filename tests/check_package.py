from pathlib import Path
import json,re
root=Path(__file__).resolve().parents[1]
required=['docs/index.html','docs/styles.css','docs/core.js','docs/app.js','docs/sw.js','docs/manifest.webmanifest','docs/icon.svg','scripts/scrape.py','.github/workflows/pages.yml','.github/workflows/refresh.yml']
for f in required: assert (root/f).exists(),f
html=(root/'docs/index.html').read_text()
assert html.index('core.js') < html.index('app.js')
assert 'class="workspace"' in html and 'class="sidePane"' in html
css=(root/'docs/styles.css').read_text()
assert '@media(min-width:980px)' in css and 'grid-template-columns:minmax(0,1fr) 360px' in css
assert '.selected{' in css
manifest=json.loads((root/'docs/manifest.webmanifest').read_text())
assert manifest.get('display') in ('standalone','fullscreen','minimal-ui')
sw=(root/'docs/sw.js').read_text();assert 'core.js' in sw and 'app.js' in sw
print('package integrity: PASS')
