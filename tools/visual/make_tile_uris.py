"""Emit NetHack tiles used by site/proof-explorer.html as base64 PNG data URIs (JSON)."""
import base64, io, json, sys
from tiles import load_all
T = load_all(sys.argv[1])
want = {'h': 'main walls horizontal', 'v': 'main walls vertical', 'tl': 'main walls tlcorn', 'tr': 'main walls trcorn',
        'bl': 'main walls blcorn', 'br': 'main walls brcorn', 'cross': 'main walls cross wall', 'tu': 'main walls tuwall',
        'td': 'main walls tdwall', 'tlw': 'main walls tlwall', 'trw': 'main walls trwall', 'floor': 'floor of a room',
        'stone': 'stone', 'boulder': 'boulder', 'hero': 'valkyrie,female', 'pit': 'pit', 'hole': 'hole', 'stairs': 'branch staircase up', 'goal': 'magic portal'}
out = {}
for k, n in want.items():
    b = io.BytesIO(); T[n].save(b, 'PNG', optimize=True)
    out[k] = 'data:image/png;base64,' + base64.b64encode(b.getvalue()).decode()
print(json.dumps(out))
