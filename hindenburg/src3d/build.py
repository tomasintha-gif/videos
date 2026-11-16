"""Bundle three.js + chars.js + film3d.js + fonts into one self-contained HTML.
Usage: python3 build.py <fonts_dir> <three.cjs> [timings.json]
timings.json (optional): {"shots": [...], "words": [{"w","s","e"}]}"""
import base64, json, pathlib, sys

here = pathlib.Path(__file__).parent
fonts = pathlib.Path(sys.argv[1]); three = pathlib.Path(sys.argv[2]).read_text()
tim = json.loads(pathlib.Path(sys.argv[3]).read_text()) if len(sys.argv) > 3 and pathlib.Path(sys.argv[3]).exists() else {}
b64 = lambda p: base64.b64encode(p.read_bytes()).decode()
anton = next(fonts.rglob('anton-latin-400-normal.woff2'))
mont = next(fonts.rglob('montserrat-latin-900-normal.woff2'))
script = json.loads((here / 'script.json').read_text())
pre = f"window.SCRIPT_LINES = {json.dumps(script, ensure_ascii=False)};"
if tim.get('shots'): pre += f"window.SHOT_TIMES = {json.dumps(tim['shots'])};"
if tim.get('words'): pre += f"window.WORD_TIMES = {json.dumps(tim['words'], ensure_ascii=False)};"
html = f"""<!doctype html><html><head><meta charset="utf-8"><title>Hindenburg 3D</title>
<style>html,body{{margin:0;background:#000}}canvas{{display:block;width:100vw;max-width:1080px;height:auto}}</style></head>
<body><canvas id="c"></canvas>
<script>var module = {{ exports: {{}} }}, exports = module.exports;
{three}
window.THREE = module.exports;</script>
<script>{pre}</script>
<script>{(here / 'chars.js').read_text()}</script>
<script>
(async () => {{
  const f1 = new FontFace('Anton', 'url(data:font/woff2;base64,{b64(anton)})');
  const f2 = new FontFace('Montserrat', 'url(data:font/woff2;base64,{b64(mont)})', {{ weight: '900' }});
  await Promise.all([f1.load(), f2.load()]); document.fonts.add(f1); document.fonts.add(f2);
  {(here / 'film3d.js').read_text()}
  window.seek(0); window.ready = true;
}})();
</script></body></html>"""
out = here.parent / 'hindenburg-3d.html'
out.write_text(html)
print('wrote', out, len(html) // 1024, 'KB')
