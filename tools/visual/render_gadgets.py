"""Render the EXPTIME gadget status sheet (found / failed / missing) with NetHack tiles -> media/exptime/gadgets.png"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'exptime'))
from PIL import Image, ImageDraw, ImageFont
from tiles import load_all
import A_library as L
T = load_all(os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'win', 'share'))
S = 32
def font(n):
    for f in ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"):
        try: return ImageFont.truetype(f, n)
        except OSError: pass
    return ImageFont.load_default()
F1, F2, F3 = font(20), font(14), font(13)
def board(rows):
    H, W = len(rows), max(map(len, rows))
    im = Image.new('RGB', (W*S, H*S), (0, 0, 0)); d = ImageDraw.Draw(im)
    def solid(x, y): return not (0 <= y < H and 0 <= x < len(rows[y])) or rows[y][x] == '#'
    for y in range(H):
        for x in range(W):
            ch = rows[y][x] if x < len(rows[y]) else '#'
            if ch == '#':
                near = any(not solid(x+i, y+j) for i in (-1,0,1) for j in (-1,0,1) if i or j)
                t = ('main walls vertical' if (not solid(x-1,y) or not solid(x+1,y)) and solid(x,y-1) is not None and (not solid(x-1,y) or not solid(x+1,y)) and not (not solid(x,y-1) or not solid(x,y+1)) else 'main walls horizontal') if near else 'stone'
                im.paste(T[t].resize((S, S), Image.NEAREST), (x*S, y*S)); continue
            im.paste(T['floor of a room'].resize((S, S), Image.NEAREST), (x*S, y*S))
            if ch == '0': im.paste(T['boulder'].resize((S, S), Image.NEAREST), (x*S, y*S))
            if ch.isalpha():
                col = (255, 210, 60) if ch.isupper() else (150, 200, 255)
                d.rectangle([x*S+1, y*S+1, x*S+S-2, y*S+S-2], outline=col, width=2)
                d.text((x*S+S//2, y*S+S//2), ch, fill=col, font=font(18), anchor='mm')
    return im
cards = [
 ("FOUND: one-way corridor (checkable)", "Ani et al. protodiode, ports A B C D. Machine-checked.\nWorks if used as intended; misuse jams it for good.", (35,112,74), L.PROTODIODE),
 ("FOUND (NP proof): single-use door G_D", "Enter at E, push the boulder into the pocket, exit Q.\nOne use only, so not enough for EXPTIME.", (36,88,154), L.GD_ROWS),
 ("FAILED: one-boulder slot", "Overshoot: the return push sends the boulder too far\nand opens B to A.", (176,40,31), L.SLOT1),
 ("FAILED: two-boulder U-turn", "Lets you through, but also lets you sneak back.\nComplete but unsound.", (176,40,31), L.UTURN2),
 ("MISSING: self-closing door", "Opens when you visit 'open', closes behind you when you\npass. Published design (Ani et al. Fig. 37) being copied.\nNo unbreakable version in ~1.4M layouts searched.", (138,91,0), None),
 ("MISSING: reusable crossover", "Two paths crossing, each usable any number of times.\nBuildable from two self-closing doors, but not flat;\nthe flat version needs a working door first.", (138,91,0), None),
]
CW, CH = 560, 400
sheet = Image.new('RGB', (CW*2+30, (CH+20)*3+70), (233, 237, 238)); d = ImageDraw.Draw(sheet)
d.text((20, 18), "EXPTIME attempt: gadget status (29 Oct 2026)", fill=(25,34,39), font=font(24))
for i, (title, desc, col, rows) in enumerate(cards):
    x0, y0 = 10 + (i % 2)*(CW+10), 60 + (i//2)*(CH+20)
    d.rectangle([x0, y0, x0+CW, y0+CH], fill=(246,248,248), outline=col, width=3)
    d.text((x0+14, y0+12), title, fill=col, font=F1)
    d.multiline_text((x0+14, y0+44), desc, fill=(60,70,76), font=F2, spacing=4)
    if rows:
        b = board(rows); sc = min((CW-40)/b.width, (CH-140)/b.height, 1.6)
        b = b.resize((int(b.width*sc), int(b.height*sc)), Image.NEAREST)
        sheet.paste(b, (x0 + (CW-b.width)//2, y0 + 120 + (CH-130-b.height)//2))
    else:
        d.rectangle([x0+40, y0+130, x0+CW-40, y0+CH-30], outline=col, width=2)
        d.text((x0+CW//2, y0+(CH+100)//2), "?", fill=col, font=font(90), anchor='mm')
out = os.path.join(os.path.dirname(__file__), '..', '..', 'media', 'exptime', 'gadgets.png')
sheet.save(out); print(out, sheet.size)
