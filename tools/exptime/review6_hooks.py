#!/usr/bin/env python3
"""review6_hooks.py -- review 6: what do L_gen's hook curves cross?

L_gen routes, per G', one 'hook' path from the chain head to every check location and only counts its jumps
("hook crossings (bound, not drawn)", said to be SX in time order). This script re-runs the tile-block templates
(SCD compound tile, diode tile; both lane parities) with Router.dijkstra wrapped, and classifies every jump on a
hook path by the role of the jumped floor point:
  SX           over the chain itself (single-use x single-use: safe in time order)
  GX           WCX over a (dead) own/finished leg stub between location and Wb: the stub is LIVE main floor before t
  CHX.<role>   WCX over other floor (corridor, leg mid, SCD interior): LIVE main floor before t
A hook from a location b_i to its SO entrance is walkable from b_i BEFORE t (b_i is a component location reachable
in clean play). A WCX on it is entered at Bt from the b_i side, and the ideal WCX allows Bt->L / Bt->R (leak) in
state 1: a path from b_i onto that main corridor before t, not a dead end. Read-only import of L_gen.
"""
import sys, random, collections
sys.path.insert(0, __file__.rsplit('\\', 1)[0].rsplit('/', 1)[0])
import L_gen as L

ROLE_NAMES = None
stats = collections.Counter()
per_loc = []
final = {}


def wrap():
    orig = L.Router.dijkstra

    def dij(self, src, targets, level, own, limit=None, dead=(), pen=None, box=None):
        path, cost = orig(self, src, targets, level, own, limit=limit, dead=dead, pen=pen, box=box)
        if path is not None and isinstance(own, set) and not own:        # hook call (own = set())
            kinds = collections.Counter()
            for i, jv in path:
                if not jv:
                    continue
                k = jv[0]
                if k == 'CHX':
                    r = self.role[jv[1]]
                    k = 'CHX.r%d' % r
                kinds[k] += 1
            self._hk_cur.append((level, dict(kinds)))
        return path, cost
    L.Router.dijkstra = dij
    og = L.Router._gprime

    def gp(self, head, G, own, rot, gap, rad):
        self._hk_cur = []
        nh, info = og(self, head, G, own, rot, gap, rad)
        if nh is not None:
            final[(G['tile'], G.get('name'), G['level'])] = list(self._hk_cur)
        return nh, info
    L.Router._gprime = gp


def main():
    wrap()
    rng = random.Random(1)
    inst = L.random_instance(rng)
    N = L.netlist(inst); L.contract(N)
    B = L.Bus(N); B.order(); B.rows()
    Lv = L.Level(B); Lv.blocks()
    names = {getattr(L, n): n for n in ('WIN', 'LOC', 'COINC', 'SLOT', 'MIDR', 'SCDINT', 'GXR', 'CORR') if hasattr(L, n)}
    for kind in ('scdc', 'dio'):
        tn = [t for t in B.tiles if B.tiles[t]['kind'] == kind][0]
        for par in (0, 1):
            stats.clear(); per_loc.clear(); final.clear()
            r = L.block_template(Lv.tb[tn], par)
            for key, lst in final.items():
                for lv, d in lst:
                    per_loc.append((lv, d))
                    for k, v in d.items():
                        stats[(lv, k)] += v
            errs = {k: v['err'] for k, v in r['levels'].items()}
            hooks_with_live = sum(1 for lv, d in per_loc if any(k != 'SX' for k in d))
            print(f'{kind} parity {par}: errors {errs}; hook paths {len(per_loc)}, '
                  f'with a non-SX crossing (GX/CHX over live floor) {hooks_with_live}')
            for (lv, k), v in sorted(stats.items()):
                kk = k
                if k.startswith('CHX.r'):
                    kk = 'CHX.' + names.get(int(k[5:]), k[5:])
                print(f'   level {lv} {kk}: {v}')


if __name__ == '__main__':
    main()
