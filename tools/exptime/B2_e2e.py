#!/usr/bin/env python3
"""B2_e2e.py -- end-to-end two-player check of the global check path (workstream B2, proofs/exptime/B2-checkpath.md).

Game = gadget network + one coin (nature node) + goal. Hero position = (node, gadget states); at a node the hero may
traverse any gadget port located there (gadget relation T, exact); arriving at the coin node hands the move to nature,
which picks an outcome node. Win = reach the goal node; infinite plays lose (attractor = least fixed point).

Gadgets used: RAW concrete Push-1F/NetHack windows from A2 (checkable proto-precursor Fig. 36a, 28 states;
checkable protodiode Fig. 35a, 4 states), joined into the checkable SCD of Fig. 37 exactly as A2_scd.py; the
single-use machinery (SO, SD, WCX) as ideal automata, verified against the concrete Fig. 32/33 boards in B2_ani.py.
Ani et al. Thm 5.3 wrapper G' (two delimiter WCX per L' location, one SO + one SD per check traversal) around every
raw component AND around the SCD composite (check [O->O, I->J]); Lemma 5.6 chain t -> SCD-level G' -> the four
component G's -> g, with one CHX (= WCX) where the chain crosses the main hallway s <-> coin.
The planar routing crossings inside G' (SX on the delimiter path, WCX on dead middle segments) are omitted: this is a
non-planar wiring of the same machinery (see B2-checkpath.md §6).

Instance (ideal level): start region s holds the SCD's opening button O and the hallway to the coin; coin outcome
alpha -> region of the SCD entrance I; outcome beta -> back to s ('lose' variant) or -> I ('win' variant);
SCD exit J -> t. SCD starts closed.
  ideal  : lose variant LOSE (nature answers beta forever), win variant WIN (press O, coin, I->J).
  raw, goal t (no check path): lose variant WIN via the O->J leak of the checkable SCD (it breaks the SCD).
  raw + check path, goal g: must equal the ideal answers.
Usage: python B2_e2e.py
"""
import os, sys, time
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import A_core as K
import A_check as AC
import A2_scd as A2
import B2_ani as BA


class Game:
    def __init__(self, gadgets, coin, start, goal, inits=None):
        """gadgets: list of (name, System, {port: node}); coin: (node, [outcome nodes]) or None."""
        self.g = gadgets
        self.at = {}
        for gi, (_, S, pm) in enumerate(gadgets):
            for p, n in pm.items():
                self.at.setdefault(n, []).append((gi, p))
        self.coin = coin
        self.start = (start, tuple((inits or {}).get(nm, S.init) for nm, S, _ in gadgets))
        self.goal = goal

    def solve(self, cap=12_000_000):
        """packed encoding: key = (node, int with a few bits per gadget)."""
        t0 = time.time()
        sts, sidx, shift, width = [], [], [], []
        off = 0
        for _, S, _ in self.g:
            lst = list(S.states)
            sts.append(lst)
            sidx.append({s: k for k, s in enumerate(lst)})
            w = max(1, (len(lst) - 1).bit_length())
            shift.append(off)
            width.append((1 << w) - 1)
            off += w
        trans = []
        for gi, (_, S, pm) in enumerate(self.g):
            d = {}
            for (s, p), lst in S.T.items():
                if s not in sidx[gi]:
                    continue
                si = sidx[gi][s]
                d[(si, p)] = [(pm[q], sidx[gi][s2]) for q, s2 in lst if not (q == p and s2 == s)]
            trans.append(d)
        node0, S0 = self.start
        packed0 = sum(sidx[gi][s] << shift[gi] for gi, s in enumerate(S0))
        idx, key, succ = {}, [], []
        dq = deque()

        def add(k):
            i = idx.get(k)
            if i is None:
                i = idx[k] = len(key)
                key.append(k)
                succ.append(None)
                dq.append(i)
            return i
        add((node0, packed0))
        coin = self.coin[0] if self.coin else None
        while dq:
            i = dq.popleft()
            node, P = key[i]
            out = []
            if node != self.goal:
                if node == coin:
                    out = [add((o, P)) for o in self.coin[1]]
                else:
                    for gi, p in self.at.get(node, []):
                        cur = (P >> shift[gi]) & width[gi]
                        for nn, s2 in trans[gi].get((cur, p), ()):
                            out.append(add((nn, P ^ ((cur ^ s2) << shift[gi]))))
            succ[i] = list(set(out))
            if len(key) > cap:
                raise RuntimeError('cap')
        self._unpack = lambda P, gi: sts[gi][(P >> shift[gi]) & width[gi]]
        n = len(key)
        pred = [[] for _ in range(n)]
        for i, s in enumerate(succ):
            for j in s:
                pred[j].append(i)
        win = [False] * n
        cnt = [len(s) for s in succ]
        q = deque(i for i in range(n) if key[i][0] == self.goal)
        for i in q:
            win[i] = True
        while q:
            j = q.popleft()
            for i in pred[j]:
                if win[i]:
                    continue
                if self.coin and key[i][0] == self.coin[0]:
                    cnt[i] -= 1
                    if cnt[i] == 0:
                        win[i] = True
                        q.append(i)
                else:
                    win[i] = True
                    q.append(i)
        coop = any(k[0] == self.goal for k in key)
        return dict(win=win[0], positions=n, coop_reach=coop, secs=round(time.time() - t0, 1)), key, win


# ---------------- builders ----------------
class Builder:
    def __init__(self):
        self.gs = []
        self.k = 0
        self.inits = {}

    def node(self, tag):
        self.k += 1
        return f'{tag}#{self.k}'

    def add(self, name, S, pm, init=None):
        self.gs.append((name, S, pm))
        if init is not None:
            self.inits[name] = init

    def wcx(self, left, right, name):
        """weak closing crossover on hallway left<->right; returns (Bt, Tp) nodes of its check line."""
        bt, tp = self.node(name + '.bt'), self.node(name + '.tp')
        self.add(name, BA.I_WCX(), {'L': left, 'R': right, 'Bt': bt, 'Tp': tp})
        return bt, tp

    def chain(self, a, b):
        """join two check-line nodes by a plain hallway gadget."""
        self.add(self.node('h'), K.abstract(['P', 'Q'], 'h', {'h': {'P': [('Q', 'h')], 'Q': [('P', 'h')]}}),
                 {'P': a, 'Q': b})

    def gprime(self, name, place, Lp, checks):
        """Ani Thm 5.3 wrapper. place(gside) must add the gadget(s) G with its L' locations on the given nodes
        (hidden locations on private nodes of its own; return {hidden name: node}). Lp: {loc: outer node}.
        checks: [(a, b)]. Returns (cin, cout)."""
        gside = {l: self.node(f'{name}.{l}.g') for l in Lp}
        hidden = place(gside)
        loc = dict(gside)
        loc.update(hidden)
        cin = self.node(name + '.cin')
        cur = cin
        top, bot = [], []
        for l in Lp:                       # delimiters: e_l = gside -- WCX_b -- mid -- WCX_t -- outer
            mid = self.node(f'{name}.{l}.mid')
            bot.append(self.wcx(gside[l], mid, f'{name}.{l}.Wb'))
            top.append(self.wcx(mid, Lp[l], f'{name}.{l}.Wt'))
        for bt, tp in top + bot[::-1]:     # top pass rightward, bottom pass leftward
            self.chain(cur, bt)
            cur = tp
        for i, (a, b) in enumerate(checks):
            op = self.node(f'{name}.O{i}.op')
            self.chain(cur, op)
            out = self.node(f'{name}.O{i}.out')
            self.add(f'{name}.O{i}', BA.I_SO(), {'Op': op, 'In': loc[b], 'Out': out})
            self.add(f'{name}.D{i}', BA.I_SD(), {'X': op, 'Y': loc[a]})
            cur = out
        return cin, cur


def raw():
    Cp = K.explore(K.Board(A2.PROTO_PRECURSOR))
    Cd = K.explore(K.Board(A2.PROTODIODE))
    bp = K.Board(A2.PROTO_PRECURSOR)
    S1 = [s for s in Cp.states if A2.track(bp, s, 2) == (4, 6)][0]   # precursor state 1 / toggle r / SCD open
    S2 = [s for s in Cp.states if A2.track(bp, s, 2) == (3, 5)][0]   # precursor state 2 / SCD closed
    return Cp, Cd, S1, S2


def build(variant, mode):
    """mode: 'ideal' (ideal SCD, goal t), 'raw' (raw composite, goal t), 'checked' (raw + check path, goal g)."""
    Cp, Cd, S1, S2 = raw()
    B = Builder()
    s, coinE, I, J, t, g = 's', 'coin', 'I', 'J', 't', 'g'
    O = s                                  # the SCD's opening button lies in the start region
    beta = s if variant == 'lose' else I
    if mode == 'ideal':
        B.add('scd', AC.T_scd_button(), {'O': O, 'I': I, 'J': J})        # init 'c' = closed
        B.chain(s, coinE)
        B.chain(J, t)
        return Game(B.gs, (coinE, [I, beta]), s, t, B.inits)
    if mode == 'raw':
        pm_prec = {'A': 'T', 'B': 'T', 'C': 'T', 'E': 'X', 'F': 'Y', 'D': 'pD', 'G': 'pG'}
        pm_tog = {'A': 'tT', 'B': 'tT', 'C': 'tT', 'E': O, 'F': 'T', 'D': 'tD', 'G': 'tG'}
        B.add('prec', Cp, pm_prec, S2)
        B.add('tog', Cp, pm_tog, S1)
        B.add('d1', Cd, {'A': I, 'B': 'X', 'C': 'd1cd', 'D': 'd1cd'})
        B.add('d2', Cd, {'A': 'Y', 'B': J, 'C': 'd2cd', 'D': 'd2cd'})
        B.chain(s, coinE)
        B.chain(J, t)
        return Game(B.gs, (coinE, [I, beta]), s, t, B.inits)
    # 'checked'  : SCD-level G' around the composite whose RAW components are themselves G'-wrapped (full, flat)
    # 'scdlevel' : components replaced by their postselected automata (A2-verified), SCD-level G' only
    # 'complevel': raw components with their G's, but NO SCD-level check (expected to miss the O->J leak)
    comp_io = {}
    scd_check = mode in ('checked', 'scdlevel')
    comp_raw = mode in ('checked', 'complevel')
    Pp = A2.postselect_L(Cp, A2.PP_CHECKS, A2.PP_L)[3]
    Pd = A2.postselect_L(Cd, A2.PD_CHECKS, ['A', 'B', 'C', 'D'])[3]

    def place_scd(gs):
        X, Y, T, tT = B.node('X'), B.node('Y'), B.node('T'), B.node('tT')
        d1cd, d2cd = B.node('d1cd'), B.node('d2cd')

        def pp(nm, init, outer):
            if not comp_raw:
                B.add(nm, Pp, dict(outer), init)
                return
            def place(gside):
                hid = {'D': B.node(nm + '.Dh'), 'G': B.node(nm + '.Gh')}
                pm = dict(gside)
                pm.update(hid)
                B.add(nm, Cp, pm, init)
                return hid
            comp_io[nm] = B.gprime(nm, place, outer, A2.PP_CHECKS)

        def pd(nm, outer):
            if not comp_raw:
                B.add(nm, Pd, dict(outer))
                return

            def place(gside):
                B.add(nm, Cd, dict(gside))
                return {}
            comp_io[nm] = B.gprime(nm, place, outer, A2.PD_CHECKS)
        pp('prec', S2, {'A': T, 'B': T, 'C': T, 'E': X, 'F': Y})
        pp('tog', S1, {'A': tT, 'B': tT, 'C': tT, 'E': gs['O'], 'F': T})
        pd('d1', {'A': gs['I'], 'B': X, 'C': d1cd, 'D': d1cd})
        pd('d2', {'A': Y, 'B': gs['J'], 'C': d2cd, 'D': d2cd})
        return {}
    if scd_check:
        cin_s, cout_s = B.gprime('scd', place_scd, {'O': O, 'I': I, 'J': J}, [('O', 'O'), ('I', 'J')])
    else:
        place_scd({'O': O, 'I': I, 'J': J})
        cin_s = cout_s = B.node('noscd')
    # main hallway s <-> coin carries a CHX crossed by the global chain (Lemma 5.6)
    bt, tp = B.wcx(s, coinE, 'chx')
    B.chain(J, t)
    B.chain(t, cin_s)                     # chain: t -> SCD checks -> CHX -> component checks -> g
    B.chain(cout_s, bt)
    cur = tp
    for nm in (('prec', 'tog', 'd1', 'd2') if comp_raw else ()):
        cin, cout = comp_io[nm]
        B.chain(cur, cin)
        cur = cout
    B.chain(cur, g)
    return Game(B.gs, (coinE, [I, beta]), s, g, B.inits)


def main():
    ok = True
    expect = {('lose', 'ideal'): False, ('win', 'ideal'): True, ('lose', 'raw'): True, ('win', 'raw'): True,
              ('lose', 'scdlevel'): False, ('win', 'scdlevel'): True,
              ('lose', 'complevel'): True, ('win', 'complevel'): True,
              ('lose', 'checked'): False, ('win', 'checked'): True}
    modes = [m for m in ('ideal', 'raw', 'scdlevel', 'complevel', 'checked') if m in sys.argv] or \
        ['ideal', 'raw', 'scdlevel', 'complevel', 'checked']
    for variant in ('lose', 'win'):
        for mode in modes:
            G = build(variant, mode)
            try:
                res, key, win = G.solve()
            except RuntimeError as e:
                print(f'{variant:4s} {mode:9s}: state cap reached ({e}); not decided')
                ok = False
                continue
            good = res['win'] == expect[(variant, mode)]
            ok &= good
            print(f'{variant:4s} {mode:8s}: {"WIN " if res["win"] else "LOSE"}  positions {res["positions"]:8d}  '
                  f'coop_reach {res["coop_reach"]}  gadgets {len(G.g)}  {res["secs"]} s  '
                  f'{"as expected" if good else "UNEXPECTED"}')
            if mode == 'checked':
                # every winning position must have all raw components clean (A2 clean sets) -- broken => doomed
                Cp, Cd, _, _ = raw()
                pc = {c for c in Cp.states if K.check_legal(Cp, c, A2.PP_CHECKS)}
                dc = {c for c in Cd.states if K.check_legal(Cd, c, A2.PD_CHECKS)}
                names = [nm for nm, _, _ in G.g]
                comp = {nm: (pc if nm in ('prec', 'tog') else dc) for nm in ('prec', 'tog', 'd1', 'd2')}
                ix = {nm: names.index(nm) for nm in comp}
                # broken before its own check started (its first SD still unused): such a position must be losing
                d0 = {nm: names.index(nm + '.D0') for nm in comp}
                isbroken = lambda P: any(G._unpack(P, ix[nm]) not in comp[nm] and G._unpack(P, d0[nm]) == '1'
                                         for nm in comp)
                bad = sum(1 for k, w in zip(key, win) if w and isbroken(k[1]))
                broken = sum(1 for k in key if isbroken(k[1]))
                print(f'      reachable positions with a broken component: {broken}; of them winning: {bad}')
                ok &= bad == 0
    print('ALL AS EXPECTED' if ok else 'SOME UNEXPECTED RESULT')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
