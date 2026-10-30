#!/usr/bin/env python3
"""X_render.py -- PNG of the concrete crossover map (build/xover/crossover.png) with NetHack tiles
(tools/visual/tiles.py, wallification as in render_gadgets.py / animate_gadgets.wall_tile). The cells the hero visits
on the realised A1->B1 walk are tinted red, A2->B2 green (both: magenta); SCD tiles get a thin yellow frame, external
ports are labelled. Needs build/xover/routes.json from X_verify.py. Usage: python X_render.py [--px 10]
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'visual'))
from PIL import Image, ImageDraw, ImageFont
from tiles import load_all

OUT = os.path.join(ROOT, 'build', 'xover')


def wall_tile(rows, x, y):
    H = len(rows)

    def solid(x, y):
        return not (0 <= y < H and 0 <= x < len(rows[y])) or rows[y][x] == '#'
    if not any(not solid(x + i, y + j) for i in (-1, 0, 1) for j in (-1, 0, 1) if i or j):
        return 'stone'
    hf = not solid(x - 1, y) or not solid(x + 1, y)
    vf = not solid(x, y - 1) or not solid(x, y + 1)
    return 'main walls vertical' if hf and not vf else 'main walls horizontal'


def main():
    S = int(sys.argv[sys.argv.index('--px') + 1]) if '--px' in sys.argv else 10
    T = load_all(os.path.join(ROOT, 'src', 'win', 'share'))
    rows = open(os.path.join(OUT, 'crossover.txt')).read().split()
    J = json.load(open(os.path.join(OUT, 'crossover.json')))
    R = json.load(open(os.path.join(OUT, 'routes.json')))
    r1 = {tuple(c) for c in R['A1B1']}
    r2 = {tuple(c) for c in R['A2B2']}
    H, W = len(rows), len(rows[0])
    cache = {}

    def tile(n):
        if n not in cache:
            cache[n] = T[n].resize((S, S), Image.NEAREST).convert('RGBA')
        return cache[n]
    im = Image.new('RGBA', (W * S, H * S), (0, 0, 0, 255))
    for y in range(H):
        for x in range(W):
            ch = rows[y][x]
            if ch == '#':
                w = wall_tile(rows, x, y)
                if w != 'stone':
                    im.paste(tile(w), (x * S, y * S))
                continue
            im.paste(tile('floor of a room'), (x * S, y * S))
            if ch == '0':
                im.alpha_composite(tile('boulder'), (x * S, y * S))
    ov = Image.new('RGBA', im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for c in r1 | r2:
        col = (230, 40, 200, 150) if (c in r1 and c in r2) else ((235, 50, 40, 150) if c in r1 else (60, 230, 60, 160))
        d.rectangle([c[0] * S, c[1] * S, c[0] * S + S - 1, c[1] * S + S - 1], fill=col)
    for n, Tl in J['tiles'].items():
        if Tl['kind'] != 'scd':
            continue
        xs = [c[0] for c in Tl['cells']]
        ys = [c[1] for c in Tl['cells']]
        d.rectangle([min(xs) * S - S, min(ys) * S - S, max(xs) * S + 2 * S - 1, max(ys) * S + 2 * S - 1],
                    outline=(255, 210, 60, 255), width=max(1, S // 5))
    im.alpha_composite(ov)
    d = ImageDraw.Draw(im)
    try:
        f = ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf', S * 4)
    except OSError:
        f = ImageFont.load_default()
    for e, (x, y) in J['ext'].items():
        col = (255, 90, 80) if e in ('A1', 'B1') else (90, 240, 90)
        ax = 'lm' if x == 0 else 'rm' if x == W - 1 else 'mt' if y == 0 else 'mb'
        px = x * S + (S * 2 if x == 0 else -S if x == W - 1 else S * 2)
        py = y * S + (S * 3 if y == 0 else -S * 2 if y == H - 1 else 0)
        d.text((px, py), e, fill=col, font=f, anchor=ax if ax in ('lm', 'rm') else 'lt', stroke_width=3,
               stroke_fill=(0, 0, 0))
    d.text((S * 3, S * 2), 'Directed crossover (ABD+20 Fig. 12): 20 SCDs + 46 diodes, 166 boulders.  '
           'red = A1->B1 walk, green = A2->B2 walk, magenta = both;  yellow frames = SCD tiles',
           fill=(255, 255, 255), font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', S * 2) if S >= 6 else None)
    p = os.path.join(OUT, 'crossover.png')
    im.convert('RGB').save(p, optimize=True)
    small = im.convert('RGB').resize((W * 3, H * 3), Image.LANCZOS)
    small.save(os.path.join(OUT, 'crossover_small.png'))
    print(p, im.size, os.path.getsize(p))


if __name__ == '__main__':
    main()
