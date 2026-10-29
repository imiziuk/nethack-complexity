"""Read NetHack's official tile text files (win/share/{monsters,objects,other}.txt, 16x16, per-file palette)."""
import re
from PIL import Image

TILE_RE = re.compile(r'^# tile (\d+) \((.*)\)\s*$')
PAL_RE = re.compile(r'^(\S) = \((\d+),\s*(\d+),\s*(\d+)\)\s*$')


def load(path):
    """-> {name: PIL.Image RGB 16x16}"""
    pal, tiles, name, rows = {}, {}, None, None
    for line in open(path, encoding='latin-1'):
        line = line.rstrip('\n')
        m = PAL_RE.match(line)
        if m and name is None:
            pal[m.group(1)] = tuple(int(m.group(i)) for i in (2, 3, 4))
            continue
        m = TILE_RE.match(line)
        if m:
            name, rows = m.group(2), []
            continue
        s = line.strip()
        if name is not None and s == '{':
            rows = []
        elif name is not None and s == '}':
            img = Image.new('RGB', (len(rows[0]), len(rows)))
            img.putdata([pal[c] for r in rows for c in r])
            tiles.setdefault(name, img)
            name = None
        elif name is not None and rows is not None and s and not s.startswith('#'):
            rows.append(s)
    return tiles


def load_all(share_dir):
    t = {}
    for f in ('other.txt', 'objects.txt', 'monsters.txt'):
        t.update(load(f'{share_dir}/{f}'))
    return t


# tty character (symset DECgraphics, boulder:0) -> tile name in the official files
DEC_TO_TILE = {
    'q': 'main walls horizontal', 'x': 'main walls vertical', 'l': 'main walls tlcorn',
    'k': 'main walls trcorn', 'm': 'main walls blcorn', 'j': 'main walls brcorn', 'n': 'main walls cross wall',
    'v': 'main walls tuwall', 'w': 'main walls tdwall', 'u': 'main walls tlwall', 't': 'main walls trwall',
    '~': 'floor of a room', ' ': 'stone', '0': 'boulder', '@': 'valkyrie,female', '^': 'pit',
    '<': 'branch staircase up', '#': 'corridor',
}
