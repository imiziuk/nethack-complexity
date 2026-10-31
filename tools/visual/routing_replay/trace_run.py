"""Record the routing attempts of one crossover template for the slow-motion replay viewer.

    python tools/visual/routing_replay/trace_run.py 0 1 1 [--cap 1080]

Imports the COPY L_gen_trace.py (never tools/exptime/L_gen.py), wraps Router.dijkstra / commit / restore / _wreg
and writes build/replay/trace_<fx><fy><p>.jsonl (one JSON object per line) plus build/replay/static_<...>.json.
Events (doubled-resolution points p = Y * W + X of the Router grid are written as flat [X, Y, X, Y, ...]):
  {"e":"try", tile, g, lv, var, what, n (try index in the tile), ok, cells, [best, cloud, nexp], t}
  {"e":"commit", n0, cells, t}      chain piece drawn (n0 = trace length before it)
  {"e":"wire", n0, cells, t}        reserved wire (SO / SD box to its location)
  {"e":"restore", nt, t}            backtrack: everything with n0 >= nt is undone
  {"e":"done", tile, left, rewinds, t} / {"e":"stuck", tile, info, t} / {"e":"strategy", name} / {"e":"end", why}
Runs below normal priority and stops itself after --cap seconds (the trace so far stays usable).
"""
import json, os, sys, threading, time, heapq, random

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)

if os.name == 'nt':
    import ctypes
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)  # BELOW_NORMAL

os.environ.setdefault('LGEN_STRATS', 'l2first')
os.environ['LGEN_PROGRESS'] = '1'
os.environ['LGEN_DEBUG'] = '1'
import L_gen_trace as L  # noqa: E402

args = [a for a in sys.argv[1:] if not a.startswith('--')]
fx, fy, par = (int(v) for v in (args + ['0', '1', '1'])[:3]) if args else (0, 1, 1)
CAP = float(sys.argv[sys.argv.index('--cap') + 1]) if '--cap' in sys.argv else 1080.0
tag = f'{fx}{fy}{par}'
OUTD = os.path.join(ROOT, 'build', 'replay')
os.makedirs(OUTD, exist_ok=True)
fout = open(os.path.join(OUTD, f'trace_{tag}.jsonl'), 'w', buffering=1 << 16)
T0 = time.time()
lock = threading.Lock()
RT = {'W': None}
CLOUD_MAX = 1500


def emit(**k):
    k['t'] = round(time.time() - T0, 2)
    with lock:
        fout.write(json.dumps(k, separators=(',', ':')) + '\n')


def flat(points):
    W = RT['W']
    out = []
    for i in points:
        out += (i % W, i // W)
    return out


# ---------------- stdout / stderr: progress lines -> events
class Tap:
    def __init__(self, s):
        self.s, self.buf = s, ''

    def write(self, x):
        self.s.write(x)
        self.buf += x
        while '\n' in self.buf:
            line, self.buf = self.buf.split('\n', 1)
            w = line.split()
            if 'tile' in w and 'done,' in w:
                k = w.index('tile')
                emit(e='done', tile=w[k + 1], left=int(w[k + 3]), rewinds=int(w[-1]))
            elif w[:1] == ['stuck']:
                emit(e='stuck', tile=w[1], info=line[:400])
            elif w[:1] == ['strategy']:
                emit(e='strategy', name=w[1])
        return len(x)

    def flush(self):
        self.s.flush()


sys.stdout, sys.stderr = Tap(sys.stdout), Tap(sys.stderr)

# ---------------- Router hooks
R = L.Router
_orig_init, _orig_commit, _orig_restore, _orig_wreg = R.__init__, R.commit, R.restore, R._wreg
VAR = {v: k for k, v in enumerate(R.VARIANTS)}
tries = {}


def init(self, *a, **k):
    _orig_init(self, *a, **k)
    RT['W'] = self.W


def dijkstra(self, src, targets, level, own, limit=None, dead=(), pen=None, box=None, tpen=None):
    """verbatim copy of L_gen.Router.dijkstra, plus: on failure the explored set is kept in self._srch"""
    box = box or self.box
    if box:
        W = self.W
        x0, y0, x1, y1 = (2 * v for v in box)
        hx, hy = src % W, src // W
        x0, y0, x1, y1 = min(x0, hx - 6), min(y0, hy - 6), max(x1, hx + 6), max(y1, hy + 6)
    dist = {src: 0}
    prev = {}
    pq = [(0, src)]
    self._srch = None
    while pq:
        dd, i = heapq.heappop(pq)
        if i < 0:
            i = -1 - i
            path = []
            while i != src:
                path.append((i, prev[i][1]))
                i = prev[i][0]
            return path[::-1], dd
        if dd > dist[i]:
            continue
        if i in targets and tpen is not None:
            if i != src:
                heapq.heappush(pq, (dd + tpen.get(i, 0), -1 - i))
                if not self.free(i):
                    continue
        elif i in targets:
            path = []
            while i != src:
                path.append((i, prev[i][1]))
                i = prev[i][0]
            return path[::-1], dd
        if limit and dd > limit:
            break
        for j, w, jv in self.neigh(i, level, own, targets, dead):
            if box and not (x0 <= j % W <= x1 and y0 <= j // W <= y1):
                continue
            nd = dd + w + (pen.get(j, 0) if pen else 0)
            if nd < dist.get(j, 1 << 60):
                dist[j] = nd
                prev[j] = (i, jv)
                heapq.heappush(pq, (nd, j))
    self._srch = (src, dist, prev)
    return None, None


def context(self):
    """what is this search for? read from the caller's frame (no source edits in L_gen)"""
    f = sys._getframe(2)
    name = f.f_code.co_name
    lo = f.f_locals
    if name == '_gprime':
        G = lo['G']
        v = VAR.get((lo['rot'], lo['gap'], lo['rad']), -1)
        return G['tile'], G['name'], G['level'], v, ('Wt' if lo['slot'] == 0 else 'Wb') + ' ' + lo['ln']
    if name == 'rec':
        g = f.f_back
        while g is not None and g.f_code.co_name != '_checks':
            g = g.f_back
        G = g.f_locals['G'] if g else {'tile': '?', 'name': '?', 'level': 0}
        gp = g.f_back.f_locals if g and g.f_back else {}
        v = VAR.get((gp.get('rot'), gp.get('gap'), gp.get('rad')), -1)
        k = lo.get('k')
        what = f"check {k} SD box -> {lo.get('a')}" if 'Ra' in lo else f"check {k} SO box -> {lo.get('b')}"
        return G['tile'], G['name'], G['level'], v, what
    if name == '_can_reach':
        return None, None, lo.get('lv'), -1, 'lookahead: head still reaches lane exit?'
    if name == 'joint':
        return None, None, lo.get('lv'), -1, 'back to the lane exit'
    return None, None, None, -1, name


def traced_dijkstra(self, src, targets, level, own, limit=None, dead=(), pen=None, box=None, tpen=None):
    path, cost = dijkstra(self, src, targets, level, own, limit, dead, pen, box, tpen)
    tile, g, lv, v, what = context(self)
    if tile is None and what.startswith('lookahead'):
        emit(e='look', ok=path is not None, lv=lv)
        return path, cost
    n = tries[tile] = tries.get(tile, 0) + 1
    rec = dict(e='try', tile=tile, g=g, lv=lv, var=v, what=what, n=n, ok=path is not None, src=flat([src]))
    if path is not None:
        rec['cells'] = flat([src] + [i for i, _ in path])
    else:
        s, dist, prev = self._srch
        W = self.W
        tg = list(targets)
        if len(tg) > 60:
            tg = random.Random(0).sample(tg, 60)
        tgxy = [(t % W, t // W) for t in tg]
        best, bd = s, 1 << 60
        for i in dist:
            x, y = i % W, i // W
            d = min(abs(x - a) + abs(y - b) for a, b in tgxy) if tgxy else 0
            if d < bd:
                best, bd = i, d
        bp = []
        i = best
        while i != s and i in prev:
            bp.append(i)
            i = prev[i][0]
        rec['cells'] = flat([s] + bp[::-1])
        rec['tgt'] = flat(tg[:12])
        cells = {(i % W // 2, i // W // 2) for i in dist}
        cl = sorted(cells)
        if len(cl) > CLOUD_MAX:
            cl = cl[::len(cl) // CLOUD_MAX + 1]
        rec['cloud'] = [u for c in cl for u in c]
        rec['nexp'] = len(dist)
        rec['gap'] = bd // 2
    emit(**rec)
    return path, cost


def commit(self, path):
    n0 = len(self.trace)
    _orig_commit(self, path)
    if path:
        emit(e='commit', n0=n0, lv=self.cur, cells=flat([self.trace[n0 - 1]] + [i for i, _ in path]) if n0 else
             flat([i for i, _ in path]))


def restore(self, sn):
    _orig_restore(self, sn)
    emit(e='restore', nt=sn[5])


def wreg(self, seq, level):
    _orig_wreg(self, seq, level)
    emit(e='wire', n0=len(self.trace) - 0.5, lv=level, cells=flat(seq))


R.__init__, R.dijkstra, R.commit, R.restore, R._wreg = init, traced_dijkstra, commit, restore, wreg


# ---------------- static background
def dump_static(b):
    W, H = b.W, b.H
    xs = [c[0] for c in b.floor]
    ys = [c[1] for c in b.floor]
    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    rows = []
    for y in range(y0, y1 + 1):
        rows.append(''.join(b.floor.get((x, y), '#') for x in range(x0, x1 + 1)))
    tiles = []
    for t in b.tiles:
        cx = [c[0] for c in t['cells']]
        cy = [c[1] for c in t['cells']]
        legs = {k: dict(Wt=L_['Wt'], Wb=L_['Wb'], g=L_['gside']) for k, L_ in t['legs'].items()}
        tiles.append(dict(id=t['id'], kind=t['kind'], box=[min(cx), min(cy), max(cx), max(cy)], legs=legs,
                          comps=[c['name'] for c in t['comps']]))
    st = dict(tag=tag, kind=str(b.kind), W=W, H=H, x0=x0, y0=y0, rows=rows, tiles=tiles, lanes=list(L.LANES),
              strategy=os.environ.get('LGEN_STRATS'), source='tools/exptime/L_gen.py (copy L_gen_trace.py)',
              made=time.strftime('%Y-%m-%d %H:%M'))
    json.dump(st, open(os.path.join(OUTD, f'static_{tag}.json'), 'w'), separators=(',', ':'))


def watchdog():
    time.sleep(CAP)
    emit(e='end', why=f'time cap {CAP:.0f}s reached')
    with lock:
        fout.flush()
        os._exit(0)


threading.Thread(target=watchdog, daemon=True).start()
b = L.x_block(bool(fx), bool(fy))
dump_static(b)
emit(e='start', tag=tag)
r = L.block_template(b, par)
errs = {k: v['err'] for k, v in r['levels'].items()}
emit(e='end', why='finished', errs=str(errs), ok=bool(r.get('validate', {}).get('ok')) if 'validate' in r else False)
fout.flush()
print('done', errs, file=sys.__stderr__)
os._exit(0)
