"""Turn the captured tty screens (frames.json from capture.py) into tile images, PNG screenshots, an MP4 and a GIF.

Every map cell is drawn from the character the real game printed at that screen position (DECgraphics symset),
looked up in NetHack's own tile files. Only the labels g / a / b, the captions and the cards are added here.

Usage (WSL venv): python render.py <frames.json> <win/share dir> <media dir>
"""
import json, os, sys, textwrap
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

import tiles as T
from scenes import SCENES, KEYNAME, board, cell_of

frames_path, share, media = sys.argv[1:4]
W, H = 1280, 720
FONTS = '/mnt/c/Windows/Fonts'
F_TITLE = ImageFont.truetype(f'{FONTS}/segoeuib.ttf', 40)
F_BIG = ImageFont.truetype(f'{FONTS}/segoeuib.ttf', 34)
F_TXT = ImageFont.truetype(f'{FONTS}/segoeui.ttf', 26)
F_SMALL = ImageFont.truetype(f'{FONTS}/segoeui.ttf', 18)
F_MONO = ImageFont.truetype(f'{FONTS}/consola.ttf', 24)
F_MONO_S = ImageFont.truetype(f'{FONTS}/consola.ttf', 17)
BG, FG, DIM, GOLD, ACC = (18, 18, 24), (236, 236, 236), (150, 150, 165), (255, 200, 40), (120, 200, 255)
FOOT = ('Real NetHack 5.0.0 (16ff591) tty screens captured live, drawn with NetHack\'s own tiles. '
        'Hunger off, Sokoban flag, hero holds a cursed loadstone.')

TILES = T.load_all(share)
SCN = {s['id']: s for s in SCENES}
data = json.load(open(frames_path))


def map_image(frame, sc, tile):
    rows = board(sc['level'])
    bw, bh = max(len(r) for r in rows), len(rows)
    img = Image.new('RGB', (bw * tile, bh * tile))
    unknown = set()
    for my in range(bh):
        line = frame['rows'][my + 1]
        for mx in range(bw):
            ch = line[mx] if mx < len(line) else ' '
            name = T.DEC_TO_TILE.get(ch)
            if name is None:
                unknown.add(ch); name = 'stone'
            img.paste(TILES[name].resize((tile, tile), Image.NEAREST), (mx * tile, my * tile))
    if unknown:
        print('unmapped screen chars', unknown, sc['id'])
    d = ImageDraw.Draw(img)
    lf = ImageFont.truetype(f'{FONTS}/segoeuib.ttf', max(14, tile // 3))
    for ch in sc.get('goal', '') + sc.get('labels', ''):
        c = cell_of(sc['level'], ch)
        x0, y0 = c[0] * tile, c[1] * tile
        d.rectangle([x0 + 1, y0 + 1, x0 + tile - 2, y0 + tile - 2], outline=GOLD, width=max(2, tile // 16))
        d.text((x0 + 4, y0 + 1), ch, font=lf, fill=GOLD, stroke_width=2, stroke_fill=(0, 0, 0))
    p = cell_of(sc['level'], 'P')
    if p:
        sf = ImageFont.truetype(f'{FONTS}/segoeuib.ttf', max(11, tile // 5))
        x0, y0 = p[0] * tile, p[1] * tile
        d.text((x0 + tile // 2, y0 + tile - 2), 'sealed pit', font=sf, fill=(255, 255, 255), anchor='md',
               stroke_width=2, stroke_fill=(0, 0, 0))
    return img


def wrap(d, text, font, width):
    out = []
    for para in text.split('\n'):
        words, line = para.split(), ''
        for w in words:
            t = (line + ' ' + w).strip()
            if d.textlength(t, font=font) > width and line:
                out.append(line); line = w
            else:
                line = t
        out.append(line)
    return out


def scene_frame(frame, sc, step_no, nsteps):
    img = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((40, 22), sc['title'], font=F_TITLE, fill=FG)
    d.text((W - 40, 34), f'step {step_no}/{nsteps}', font=F_SMALL, fill=DIM, anchor='ra')
    rows = board(sc['level'])
    bw, bh = max(len(r) for r in rows), len(rows)
    tile = min(72, (W - 160) // bw, 300 // bh)
    m = map_image(frame, sc, tile)
    mx0, my0 = (W - m.width) // 2, 95 + (300 - m.height) // 2
    d.rectangle([mx0 - 6, my0 - 6, mx0 + m.width + 5, my0 + m.height + 5], outline=(70, 70, 85), width=2)
    img.paste(m, (mx0, my0))
    # the game's own message line (screen row 0) and status lines (rows 22-23)
    y = 420
    d.rounded_rectangle([40, y, W - 40, y + 44], radius=6, fill=(0, 0, 0))
    msg = frame['rows'][0].rstrip() or ' '
    d.text((56, y + 9), msg, font=F_MONO, fill=(255, 255, 255))
    d.text((W - 56, y + 13), 'game message line', font=F_SMALL, fill=(110, 110, 120), anchor='ra')
    d.text((56, y + 50), frame['rows'][23].rstrip(), font=F_MONO_S, fill=DIM)
    # key typed + what it means
    y = 505
    if frame.get('key'):
        d.text((40, y), 'key typed:', font=F_TXT, fill=DIM)
        d.text((175, y - 4), KEYNAME.get(frame['key'], frame['key']), font=F_BIG, fill=ACC)
        d.text((175 + d.textlength(KEYNAME.get(frame['key'], frame['key']), font=F_BIG) + 24, y),
               '-  ' + frame['label'], font=F_TXT, fill=FG)
    else:
        d.text((40, y), 'start position' if frame['label'] == 'start' else 'result', font=F_TXT, fill=DIM)
    for i, line in enumerate(wrap(d, sc['caption'], F_TXT, W - 80)[:3]):
        d.text((40, 560 + i * 34), line, font=F_TXT, fill=(205, 205, 215))
    d.line([40, 672, W - 40, 672], fill=(55, 55, 65), width=1)
    d.text((40, 682), FOOT, font=F_SMALL, fill=(125, 125, 140))
    return img


def card(title, lines, small=None):
    img = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(img)
    y = 190
    for t in wrap(d, title, F_TITLE, W - 160):
        d.text((W // 2, y), t, font=F_TITLE, fill=FG, anchor='ma'); y += 56
    y += 20
    for ln in lines:
        for t in wrap(d, ln, F_TXT, W - 200):
            d.text((W // 2, y), t, font=F_TXT, fill=(205, 205, 215), anchor='ma'); y += 36
        y += 8
    if small:
        for t in wrap(d, small, F_SMALL, W - 200):
            d.text((W // 2, 640), t, font=F_SMALL, fill=DIM, anchor='ma')
    return img


TITLE = card('NetHack 5.0.0, hunger off: boulders = Push-1F (PSPACE-complete)',
             ['Push-1F: a robot walks on a grid and pushes one block at a time, never pulls; '
              'some cells are fixed walls. Deciding if it can reach a goal cell is PSPACE-complete '
              '(Ani, Chung, Demaine, Diomidov, Hendrickson, Lynch, FUN 2022).',
              'Our reduction builds each Push-1F board as a NetHack level: boulders = blocks, walls = fixed cells, '
              'the Sokoban flag forbids diagonal pushes and squeezes, a cursed loadstone keeps the hero too heavy '
              'to slip past a boulder, hunger is switched off.',
              'Everything below is the real game, played key by key.'],
             'Map squares are drawn from the characters NetHack printed, using NetHack\'s official 16x16 tiles.')
END = card('What this shows, and what it does not',
           ['The clips demonstrate the boulder rules the proof relies on (orthogonal push only, no diagonal '
            'push or squeeze, heavy hero cannot pass a boulder) and how push ORDER decides a level.',
            'The complexity result itself is the written proof in proofs/hu-off.md '
            '(simulation lemma, every command checked against the source), not this video. '
            'The proof also rests on the published Push-1F theorem.'],
           'Toy puzzle and door gadget were found and checked with our small Push-1F solver (tools/visual/push1f.py); '
           'the door is our own small example in the spirit of the self-closing doors used by Ani et al., '
           'not a gadget copied from the paper.')

# ---- build the timeline: (image, seconds) ----
timeline = [(TITLE, 8.0)]
by_scene = {}
for f in data['frames']:
    by_scene.setdefault(f['scene'], []).append(f)
shots = {}
for sc in SCENES:
    fr = [f for f in by_scene[sc['id']] if f['label'] != 'end']
    timeline.append((card(sc['title'], [sc['caption']]), 2.5))
    n = len(fr) - 1
    for i, f in enumerate(fr):
        im = scene_frame(f, sc, i, n)
        important = any(w in f['label'] for w in ('refused', 'blocked', 'stuck', 'solved', 'arrive', 'lands'))
        dur = 1.6 if i == 0 else (2.2 if important else 0.8)
        if i == len(fr) - 1:
            dur += 0.8
        timeline.append((im, dur))
        if i == 0 or important or i == len(fr) - 1:
            shots[f'{sc["id"]}_{i:02d}'] = im
timeline.append((END, 8.0))

os.makedirs(media, exist_ok=True)
shot_dir = os.path.join(media, 'screenshots')
os.makedirs(shot_dir, exist_ok=True)
for k, im in shots.items():
    im.save(os.path.join(shot_dir, k + '.png'))
TITLE.save(os.path.join(shot_dir, '00_title.png'))

FPS = 10
total = sum(d for _, d in timeline)
w = imageio_ffmpeg.write_frames(os.path.join(media, 'nethack_push1f_demo.mp4'), (W, H), fps=FPS,
                                codec='libx264', pix_fmt_out='yuv420p', quality=8,
                                output_params=['-movflags', '+faststart'])
w.send(None)
for im, dur in timeline:
    b = im.tobytes()
    for _ in range(max(1, round(dur * FPS))):
        w.send(b)
w.close()

gif = [im.resize((640, 360), Image.LANCZOS).convert('P', palette=Image.ADAPTIVE, colors=128) for im, _ in timeline]
gif[0].save(os.path.join(media, 'nethack_push1f_demo.gif'), save_all=True, append_images=gif[1:],
            duration=[int(d * 1000) for _, d in timeline], loop=0, optimize=True)
print(f'{len(timeline)} images, {total:.1f} s, {len(shots)} screenshots')
