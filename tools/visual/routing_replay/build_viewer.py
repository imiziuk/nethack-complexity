"""Inline a recorded trace into the viewer: build/replay/replay_<tag>.html (self-contained, opens from disk)
and build/replay/replay_<tag>.json (for viewer.html's file picker).

    python tools/visual/routing_replay/build_viewer.py 011
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
CLOUD = 400                                # max haze cells per failed attempt
tag = sys.argv[1] if len(sys.argv) > 1 else '011'
d = os.path.join(ROOT, 'build', 'replay')
st = json.load(open(os.path.join(d, f'static_{tag}.json')))
ev, end = [], None
for line in open(os.path.join(d, f'trace_{tag}.jsonl')):
    try:
        e = json.loads(line)
    except ValueError:                      # last line cut by the time cap
        continue
    if e['e'] == 'look':
        continue
    if e.get('cloud') and len(e['cloud']) > 2 * CLOUD:      # thin the explored haze to keep the page small
        k = len(e['cloud']) // (2 * CLOUD) + 1
        e['cloud'] = [u for j in range(0, len(e['cloud']), 2 * k) for u in e['cloud'][j:j + 2]]
    if e['e'] == 'end':
        end = e['why'] + (f" ({e['errs']})" if e.get('errs') else '')
    ev.append(e)
# NetHack 16x16 sprites, read-only from the paper's engine (same set as site/paper/engine.js)
tj = json.load(open(os.path.join(ROOT, 'site', 'paper', 'engine', 'tiles.json')))
sprites = {k: tj[k] for k in ('h', 'v', 'tl', 'tr', 'bl', 'br', 'cross', 'tu', 'td', 'tlw', 'trw', 'floor', 'stone',
                              'boulder') if k in tj}
data = json.dumps(dict(static=st, events=ev, end=end, sprites=sprites), separators=(',', ':'))
open(os.path.join(d, f'replay_{tag}.json'), 'w').write(data)
html = open(os.path.join(HERE, 'viewer.html'), encoding='utf-8').read()
ph = '<script id="replay-data">window.REPLAY = null;</script>'
assert ph in html
html = html.replace(ph, '<script id="replay-data">window.REPLAY = ' + data.replace('</', '<\\/') + ';</script>')
out = os.path.join(d, f'replay_{tag}.html')
open(out, 'w', encoding='utf-8').write(html)
n = sum(e['e'] == 'try' for e in ev)
print(out, f'{len(html) / 1e6:.1f} MB,', n, 'attempts,', sum(e['e'] == 'try' and not e['ok'] for e in ev), 'failed,',
      sum(e['e'] == 'done' for e in ev), 'tile-done events; end:', end)
