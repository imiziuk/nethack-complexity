"""Render a gen_on_instance.py --ascii board (+ optional move string) to a PNG with the hero's path."""
import sys
from PIL import Image, ImageDraw
asc, moves, out = sys.argv[1], sys.argv[2] if len(sys.argv) > 3 else None, sys.argv[-1]
rows = open(asc).read().split('\n')
H, W, S = len(rows), max(map(len, rows)), 5
COL = {' ': (24, 24, 30), '.': (70, 92, 100), '0': (230, 120, 40), '^': (20, 20, 20),
       '@': (90, 200, 255), 'G': (90, 230, 90), 'p': (180, 60, 200), 'b': (200, 200, 60)}
img = Image.new('RGB', (W * S, H * S), COL[' '])
d = ImageDraw.Draw(img)
pos = {}
for y, r in enumerate(rows):
    for x, c in enumerate(r):
        d.rectangle([x*S, y*S, x*S+S-1, y*S+S-1], fill=COL.get(c, (255, 0, 0)))
        if c in '@G':
            pos[c] = (x, y)
if moves:
    V = dict(h=(-1,0), l=(1,0), k=(0,-1), j=(0,1), y=(-1,-1), u=(1,-1), b=(-1,1), n=(1,1))
    x, y = pos['@']; pts = [(x, y)]
    for ch in open(moves).read():
        if ch in V:
            x += V[ch][0]; y += V[ch][1]; pts.append((x, y))
    d.line([(px*S+S//2, py*S+S//2) for px, py in pts], fill=(255, 230, 80), width=2)
for c, (x, y) in pos.items():
    d.ellipse([x*S-4, y*S-4, x*S+S+3, y*S+S+3], outline=COL[c], width=2)
img.save(out)
print(out, img.size)
