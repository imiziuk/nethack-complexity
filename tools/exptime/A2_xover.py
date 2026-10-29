#!/usr/bin/env python3
"""A2_xover.py -- planar directed crossover from self-closing doors, abstract level (EXPTIME workstream A2).

Source: Ani, Demaine, Diomidov, Hendrickson, Lynch, "Traversability, Reconfiguration, and Reachability in the
Gadget Framework" / doors paper, arXiv 2006.01256: Lemma 2.5 (Fig. 10, two opening buttons) and Lemma 2.6
(Fig. 11 overlapping pair of doors, Fig. 12 directed crossover). Wiring transcribed in proofs/exptime/A2-scd.md §4.

Base gadgets = the ideal pieces A2_scd.py verified for Push-1F: the directed open-buttoned self-closing door
(A_check.T_scd_button: ports O (button), I -> J (self-closing tunnel)) and the diode. An opening *tunnel* X -> Y is
X -diode-> button -diode-> Y (Lemma 2.5's remark). Each construction is checked (sound + complete, A_core.check)
  (a) with its sub-constructions replaced by their ideal automata (one level at a time), and
  (b) fully flattened down to base SCDs + diodes.
Usage: python A2_xover.py [--no-flat]
"""
import os, sys, itertools

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import A_core as K
import A_check as AC
from A2_scd import Net2

DIODE = AC.T_diode()


def scd_button(init):
    a = AC.T_scd_button()
    a.init = init
    return a


# ---------------- ideal automata ----------------
def I_door(buttons, tunnels, A='A', B='B', init='c'):
    """door with several opening buttons and opening tunnels (X, Y), self-closing tunnel A -> B."""
    ports = sorted(set(buttons) | {x for t in tunnels for x in t} | {A, B})
    opens = [(b, b) for b in buttons] + list(tunnels)
    tr = {'c': {}, 'o': {}}
    for s in 'co':
        for x, y in opens:
            tr[s].setdefault(x, []).append((y, 'o'))
    tr['o'].setdefault(A, []).append((B, 'c'))
    return K.abstract(ports, init, tr)


def I_pair(i1='c', i2='c'):
    """Fig. 11 target: two independent doors; door 1: buttons O1, O1p, tunnel A1->B1; door 2: O2, O2p, A2->B2."""
    d1 = I_door(['O1', 'O1p'], [], 'A1', 'B1', i1)
    d2 = I_door(['O2', 'O2p'], [], 'A2', 'B2', i2)
    ports = sorted(d1.ports + d2.ports)
    tr = {}
    for s1, s2 in itertools.product('co', 'co'):
        st = s1 + s2
        tr[st] = {}
        for p in d1.ports:
            tr[st][p] = [(q, t + s2) for q, t in d1.T[(s1, p)]]
        for p in d2.ports:
            tr[st][p] = [(q, s1 + t) for q, t in d2.T[(s2, p)]]
    return K.abstract(ports, i1 + i2, tr)


def I_xover():
    return K.abstract(['A1', 'A2', 'B1', 'B2'], 'x', {'x': {'A1': [('B1', 'x')], 'A2': [('B2', 'x')]}})


# ---------------- builder ----------------
class Build:
    """collects gadgets (System, {port: node}) for one A_core Network; `flat` expands every construction down to
    base SCDs + diodes, otherwise a construction one level down is inserted as its ideal automaton."""
    def __init__(self):
        self.g = {}
        self.n = 0

    def node(self, tag='n'):
        self.n += 1
        return f'{tag}{self.n}'

    def add(self, sysm, pm):
        self.g[f'g{len(self.g):03d}'] = (sysm, pm)

    def diode(self, a, b):
        self.add(DIODE, {'A': a, 'B': b})

    def opener(self, b, tunnel):
        """turn opening tunnel (X, Y) into a button node b: X -diode-> b -diode-> Y"""
        x, y = tunnel
        self.diode(x, b)
        self.diode(b, y)

    def door(self, buttons, tunnels, A, B, init, depth):
        """door with len(buttons)+len(tunnels) <= 2 openers; depth > 0 expands Fig. 10 for two openers."""
        bnodes = list(buttons)
        for t in tunnels:
            b = self.node('b')
            self.opener(b, t)
            bnodes.append(b)
        if len(bnodes) == 1:
            self.add(scd_button(init), {'O': bnodes[0], 'I': A, 'J': B})
        elif depth <= 0:
            self.add(I_door(['O1', 'O2'], [], 'A', 'B', init), {'O1': bnodes[0], 'O2': bnodes[1], 'A': A, 'B': B})
        else:
            two_button(self, bnodes[0], bnodes[1], A, B, init)

    def network(self, ext):
        return Net2(self.g, {e: e for e in ext})


def two_button(bd, O1, O2, A, B, init):
    """Lemma 2.5 / Fig. 10: doors 1, 2 (opening tunnel O_i -> N, self-closing N -> O_i), door 0 (button N, A -> B)."""
    N = bd.node('N')
    bd.door([], [(O1, N)], N, O1, 'c', 0)
    bd.door([], [(O2, N)], N, O2, 'c', 0)
    bd.door([N], [], A, B, init, 0)


def pair(bd, O1, O1p, O2, O2p, A1, B1, A2, B2, i1, i2, depth):
    """Lemma 2.6 / Fig. 11 (doors numbered as in the figure)."""
    V, M, Nt, Nb = bd.node('V'), bd.node('M'), bd.node('Nt'), bd.node('Nb')
    bd.door([], [(O2, V)], Nt, O2, 'c', depth - 1)       # door 1: open O2 -> V, self-close Nt -> O2
    bd.door([], [(O1, V)], Nb, O1, 'c', depth - 1)       # door 2: open O1 -> V, self-close Nb -> O1
    bd.door([V], [], M, Nt, 'c', depth - 1)              # door 3: button V, self-close M -> Nt (up)
    bd.door([V], [], M, Nb, 'c', depth - 1)              # door 4: button V, self-close M -> Nb (down)
    bd.diode(V, M)                                       # diode V -> M
    bd.door([O1p], [(Nt, M)], A1, B1, i1, depth - 1)     # door 5: button O'1, open Nt -> M, self-close A1 -> B1
    bd.door([O2p], [(Nb, M)], A2, B2, i2, depth - 1)     # door 6: button O'2, open Nb -> M, self-close A2 -> B2


def xover(bd, A1, B1, A2, B2, depth):
    """Lemma 2.6 / Fig. 12: pair (1,2) and pair (3,4); opening buttons used as tunnels via diodes."""
    P, U, Q, S, R, Vp = (bd.node(t) for t in ('P', 'U', 'Q', 'S', 'R', 'Vp'))
    bs = [bd.node('o') for _ in range(8)]
    # pair (1,2): X1 = door 1 (open A1->P, U->Q; self-close Q->S), X2 = door 2 (open P->U; self-close R->B2)
    bd.opener(bs[0], (A1, P))
    bd.opener(bs[1], (U, Q))
    bd.opener(bs[2], (P, U))
    # pair (3,4): X1 = door 3 (open A2->P, Vp->Q; self-close S->R), X2 = door 4 (open P->Vp; self-close R->B1)
    bd.opener(bs[4], (A2, P))
    bd.opener(bs[5], (Vp, Q))
    bd.opener(bs[6], (P, Vp))
    unused1, unused2 = bd.node('x'), bd.node('x')        # O'2 of each pair is not used
    if depth <= 0:
        bd.add(I_pair(), {'O1': bs[0], 'O1p': bs[1], 'O2': bs[2], 'O2p': unused1,
                          'A1': Q, 'B1': S, 'A2': R, 'B2': B2})
        bd.add(I_pair(), {'O1': bs[4], 'O1p': bs[5], 'O2': bs[6], 'O2p': unused2,
                          'A1': S, 'B1': R, 'A2': R, 'B2': B1})
    else:
        pair(bd, bs[0], bs[1], bs[2], unused1, Q, S, R, B2, 'c', 'c', depth - 1)
        pair(bd, bs[4], bs[5], bs[6], unused2, S, R, R, B1, 'c', 'c', depth - 1)


def run(label, bd, ext, ideal):
    N = bd.network(ext).explore()
    s, c, _, _ = K.check(N, ideal)
    print(f'  {label}: {len(bd.g)} gadgets, {len(N.states)} reachable states: SOUND {s}  COMPLETE {c}', flush=True)
    return s and c


def main():
    flat = '--no-flat' not in sys.argv
    ok = True
    print('== opening tunnel from a button SCD + 2 diodes (vs A_check.T_scd_tunnel)')
    for init in 'co':
        bd = Build()
        bd.door([], [('O', 'P')], 'I', 'J', init, 0)
        a = AC.T_scd_tunnel()
        a.init = init
        ok &= run(f'init {init}', bd, ['O', 'P', 'I', 'J'], a)
    print('== Lemma 2.5 / Fig. 10: two opening buttons')
    for init in 'co':
        bd = Build()
        two_button(bd, 'O1', 'O2', 'A', 'B', init)
        ok &= run(f'init {init}', bd, ['O1', 'O2', 'A', 'B'], I_door(['O1', 'O2'], [], 'A', 'B', init))
    print('== door with button + opening tunnel (doors 5, 6 of Fig. 11), via Fig. 10')
    bd = Build()
    bd.door(['O'], [('X', 'Y')], 'A', 'B', 'c', 1)
    ok &= run('init c', bd, ['O', 'X', 'Y', 'A', 'B'], I_door(['O'], [('X', 'Y')], 'A', 'B', 'c'))
    print('== Lemma 2.6 / Fig. 11: overlapping pair of doors (two independent 2-button doors)')
    ext = ['O1', 'O1p', 'O2', 'O2p', 'A1', 'B1', 'A2', 'B2']
    for i1, i2 in (('c', 'c'), ('o', 'c'), ('c', 'o'), ('o', 'o')):
        bd = Build()
        pair(bd, *ext, i1, i2, 1)                        # sub-doors ideal (2-opener doors atomic)
        ok &= run(f'init {i1}{i2}, 2-opener doors ideal', bd, ext, I_pair(i1, i2))
    bd = Build()
    pair(bd, *ext, 'c', 'c', 2)
    ok &= run('init cc, flat (Fig. 10 expanded)', bd, ext, I_pair('c', 'c'))
    print('== Lemma 2.6 / Fig. 12: directed crossover A1->B1, A2->B2')
    bd = Build()
    xover(bd, 'A1', 'B1', 'A2', 'B2', 0)
    ok &= run('pairs ideal', bd, ['A1', 'B1', 'A2', 'B2'], I_xover())
    print('== negative controls (expected False): crossover vs undirected crossover and vs a leaky one (A1->B2 allowed)')
    bd = Build()
    xover(bd, 'A1', 'B1', 'A2', 'B2', 0)
    N = bd.network(['A1', 'B1', 'A2', 'B2']).explore()
    u = K.abstract(['A1', 'A2', 'B1', 'B2'], 'x', {'x': {'A1': [('B1', 'x')], 'A2': [('B2', 'x')],
                                                        'B1': [('A1', 'x')], 'B2': [('A2', 'x')]}})
    s, c, _, _ = K.check(N, u)
    leak = K.abstract(['A1', 'A2', 'B1', 'B2'], 'x', {'x': {'A1': [('B1', 'x'), ('B2', 'x')], 'A2': [('B2', 'x')]}})
    s2, c2, _, _ = K.check(N, leak)
    print(f'  vs undirected: COMPLETE {c} (expect False); vs leaky A1->B2: COMPLETE {c2} (expect False)')
    ok &= (not c) and (not c2)
    if flat:
        bd = Build()
        xover(bd, 'A1', 'B1', 'A2', 'B2', 3)
        ok &= run('fully flat (base SCDs + diodes only)', bd, ['A1', 'B1', 'A2', 'B2'], I_xover())
    print('ALL AS EXPECTED' if ok else 'SOME UNEXPECTED RESULT')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
