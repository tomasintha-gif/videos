"""Bundle film.js + fonts into one self-contained index.html.
Usage: python3 build.py <fonts_dir> [timings.json]"""
import base64, json, pathlib, sys

here = pathlib.Path(__file__).parent
fonts_dir = pathlib.Path(sys.argv[1])
timings = None
if len(sys.argv) > 2 and pathlib.Path(sys.argv[2]).exists():
    timings = json.loads(pathlib.Path(sys.argv[2]).read_text())

def b64(p):
    return base64.b64encode(p.read_bytes()).decode()

anton = next(fonts_dir.rglob('anton-latin-400-normal.woff2'))
oswald = next(fonts_dir.rglob('oswald-latin-600-normal.woff2'))
times = f"window.SHOT_TIMES = {json.dumps(timings)};" if timings else ""

html = f"""<!doctype html><html><head><meta charset="utf-8"><title>Hindenburg</title>
<style>html,body{{margin:0;background:#000}}canvas{{display:block;width:100vw;height:auto;max-width:1080px}}</style></head>
<body><canvas id="c"></canvas>
<script>
{times}
(async () => {{
  const f1 = new FontFace('Anton', 'url(data:font/woff2;base64,{b64(anton)})');
  const f2 = new FontFace('Oswald', 'url(data:font/woff2;base64,{b64(oswald)})');
  await Promise.all([f1.load(), f2.load()]); document.fonts.add(f1); document.fonts.add(f2);
  {(here / 'film.js').read_text()}
  window.seek(0); window.ready = true;
  if (!navigator.webdriver) {{ const t0 = performance.now(); const loop = () => {{ window.seek(((performance.now() - t0) / 1000) % window.DURATION); requestAnimationFrame(loop); }}; loop(); }}
}})();
</script></body></html>"""
out = here.parent / 'index.html'
out.write_text(html)
print('wrote', out, len(html) // 1024, 'KB')
