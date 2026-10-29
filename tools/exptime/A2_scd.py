#!/usr/bin/env python3
"""A2_scd.py -- checkable self-closing door for Push-1F / NetHack boulders (EXPTIME workstream A2).

Source: Ani, Chung, Demaine, Diomidov, Hendrickson, Lynch, "Pushing Blocks via Checkable Gadgets" (arXiv 2412.20079)
Sec. 7, Figs. 35-37. Layouts were transcribed from the PDF's vector drawings (floor squares / brick rectangles /
block squares, pitch 19.2 pt) and re-checked against the rendered figures; see proofs/exptime/A2-scd.md.

Pipeline (all exact, exhaustive; model and checks = A_core, imported read-only):
  1. proto-precursor (Fig. 36a), checks [A->D, C->G, B->A, B->C], L' = {A,B,C,E,F}  -> clean set, G3, relation
  2. precursor  = postselected proto-precursor with A,B,C joined to one location T          vs ideal precursor
  3. 1-toggle   = precursor with T closed (A,B,C joined to an internal node)                vs ideal 1-toggle
  4. diode      = postselected protodiode (Fig. 35a, = A_library PROTODIODE), C-D joined      vs ideal diode
  5. SCD (Fig. 37) = network: O -1toggle-> T(precursor) ; I -diode-> E ; F -diode-> J.
     5a hierarchical: components postselected, then the SCD itself postselected with [O->O, I->J]   vs ideal SCD
     5b flat: RAW concrete components (pockets D/G, joined diode C-D), clean = every component clean + 5a-clean;
        raw transitions restricted to clean = ideal SCD? broken absorbing in the raw network (game-safety G3)?
  6. D_game.py relation cross-check on the proto-precursor window.
Usage: python A2_scd.py [-v]
"""
import os, sys, itertools

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import A_core as K
import A_check as AC

# ---------------- layouts (x = column, y = row; capital letters = port cells outside the figure frame) ----------
# Fig. 36a checkable proto-precursor. Figure rows are y=1..3; y=0 / y=4 hold the location cells.
# B is a 2-wide opening (x=4,5) in the figure; the location cell sits above x=4 (x=5,y=1 is reachable from x=4,y=1;
# no block can ever enter row 1, so this is the same location).
PROTO_PRECURSOR = ["##A#B##C##",
                   "##.#..#.##",
                   "#...0.0..#",     # track y=2, x=1..8; blocks on x=4, x=6 (figure's initial state)
                   "#.#.##.#.#",
                   "#D#E##F#G#"]
PP_CHECKS = [('A', 'D'), ('C', 'G'), ('B', 'A'), ('B', 'C')]
PP_L = ['A', 'B', 'C', 'E', 'F']

# Fig. 35a checkable protodiode (identical to A_library.PROTODIODE), checks [A->C, D->B], C and D joined.
PROTODIODE = ["#A#B##",
              "#.0..#",
              "##C#D#",
              "######"]
PD_CHECKS = [('A', 'C'), ('D', 'B')]


# ---------------- ideal automata ----------------
def T_precursor(init='1'):
    # Fig. 36d: state 1: T<->E free, T->F goes to 2; state 2: T<->F free, T->E goes to 1.
    # Exact single-traversal refinement: the switch passes through a middle state m (blocks x=3,6; E and F both
    # sealed) that is entered by a T->T visit; from m every exit starts at T. Paper's 2-state precursor = this
    # automaton with T->T->X chained (the hero stands on T in between, no other agent acts there).
    a = K.abstract(['E', 'F', 'T'], init, {
        '1': {'T': [('E', '1'), ('T', 'm')], 'E': [('T', '1')]},
        'm': {'T': [('T', '1'), ('E', '1'), ('T', '2'), ('F', '2')]},
        '2': {'T': [('F', '2'), ('T', 'm')], 'F': [('T', '2')]},
    })
    return a


def T_toggle(init='r'):
    a = K.abstract(['E', 'F'], init, {'r': {'E': [('F', 'l')]}, 'l': {'F': [('E', 'r')]}})
    return a


def T_scd(init):
    a = AC.T_scd_button()          # ports I, J, O; c: O->O opens; o: O->O, I->J closes
    a.init = init
    return a


# ---------------- helpers ----------------
def with_init(S, init):
    return K.System(S.ports, init, S.T, S.states)


def postselect_L(C, checks, L):
    """Ani Def. 5.2: clean = checks legal; G3 measured on L' only (paper) and on all ports (info)."""
    clean = {c for c in C.states if K.check_legal(C, c, checks)}
    absL = all(c2 not in clean for c in C.states if c not in clean for p in L for q, c2 in C.T[(c, p)] if q in L)
    absA = all(c2 not in clean for c in C.states if c not in clean for p in C.ports for _, c2 in C.T[(c, p)])
    T = {}
    for c in clean:
        for p in L:
            T[(c, p)] = {(q, c2) for (q, c2) in C.T[(c, p)] if c2 in clean and q in L}
    return clean, absL, absA, K.System(sorted(L), C.init, T, sorted(clean))


class Net2(K.Network):
    """A_core.Network, except that a walk returning to its start node with an unchanged state IS recorded as a
    traversal (A_core drops it because the start position is pre-marked as seen). Needed for button checks such as
    [O->O, ...]: 'go in and come back without changing anything' is a legal O->O traversal."""
    def traversals(self, S, p):
        from collections import deque
        start = (self.ext[p], S)
        seen = set()
        dq = deque([start])
        out = set()
        first = True
        while dq:
            node, St = dq.popleft()
            if not first and node in self.extnode:
                continue
            first = False
            for gi, port in self.at.get(node, []):
                sysm, pm = self.g[self.names[gi]]
                for q, s2 in sysm.T[(St[gi], port)]:
                    S2 = St[:gi] + (s2,) + St[gi + 1:]
                    st = (pm[q], S2)
                    if st in seen:
                        continue
                    seen.add(st)
                    if pm[q] in self.extnode:
                        out.add((self.extnode[pm[q]], S2))
                    else:
                        dq.append(st)
        return out


def net(gadgets, ext):
    return Net2(gadgets, {e: e for e in ext})


def blocks(board, B):
    return tuple(sorted(board.cells[i] for i in range(len(board.cells)) if B >> i & 1))


def track(board, B, y):
    return tuple(x for (x, yy) in blocks(board, B) if yy == y)


def verdict(N, A, label):
    s, c, Rs, Rc = K.check(N, A)
    print(f'  {label}: {len(N.states)} states vs ideal: SOUND {s}  COMPLETE {c}')
    return s and c


def closure_rel(C, state, p):
    """(q, s') reachable by chaining A_core traversals starting at port p in `state` (D_game semantics:
    the hero may pass through intermediate port cells)."""
    seen = set()
    stack = [(p, state)]
    out = set()
    while stack:
        pp, s = stack.pop()
        for q, s2 in C.T[(s, pp)]:
            if (q, s2) not in seen:
                seen.add((q, s2))
                out.add((q, s2))
                stack.append((q, s2))
    return out


# ---------------- main ----------------
def main():
    verbose = '-v' in sys.argv
    ok = True

    # 1. proto-precursor
    bp = K.Board(PROTO_PRECURSOR)
    Cp = K.explore(bp)
    clean, absL, absA, Pp = postselect_L(Cp, PP_CHECKS, PP_L)
    print('== 1. checkable proto-precursor (Fig. 36a)')
    print('\n'.join(PROTO_PRECURSOR))
    pairs = sorted(track(bp, s, 2) for s in clean)
    print(f'  reachable states {len(Cp.states)}; clean (track x of the 2 blocks): {pairs}; init clean: {Cp.init in clean}')
    exp = [(3, 5), (3, 6), (4, 6)]     # paper: both blocks in the 4 centre cells x=3..6, not adjacent
    print(f'  clean set = paper ("4 centre cells, not adjacent"): {pairs == exp}')
    print(f'  broken absorbing w.r.t. L\'={PP_L}: {absL}   (w.r.t. all ports incl. D,G: {absA}, paper: needs D,G closed)')
    ok &= pairs == exp and absL and Cp.init in clean
    for s in sorted(clean, key=lambda s: track(bp, s, 2)):
        tr = sorted({(p, q, track(bp, s2, 2)) for p in PP_L for q, s2 in Pp.T[(s, p)] if not (q == p and s2 == s)})
        print(f'    blocks {track(bp, s, 2)}: ' + ', '.join(f'{p}->{q}{"" if t == track(bp, s, 2) else " =>" + str(t)}'
                                                         for p, q, t in tr))
    S1 = [s for s in clean if track(bp, s, 2) == (4, 6)][0]
    S2 = [s for s in clean if track(bp, s, 2) == (3, 5)][0]

    # 2. precursor: A,B,C joined -> T
    print('== 2. precursor = postselected proto-precursor, A,B,C joined to T')
    for init, ai in ((S1, '1'), (S2, '2')):
        N = net({'p': (with_init(Pp, init), {'A': 'T', 'B': 'T', 'C': 'T', 'E': 'E', 'F': 'F'})}, ['T', 'E', 'F']).explore()
        ok &= verdict(N, T_precursor(ai), f'init state {ai} (blocks {track(bp, init, 2)})')
    Nraw = net({'p': (Cp, {'A': 'T', 'B': 'T', 'C': 'T', 'E': 'E', 'F': 'F', 'D': 'pD', 'G': 'pG'})}, ['T', 'E', 'F']).explore()
    s, c, _, _ = K.check(Nraw, T_precursor('1'))
    print(f'  raw (no postselection, D/G as pockets): {len(Nraw.states)} states, SOUND {s} COMPLETE {c}')

    # 3. 1-toggle: T closed
    print('== 3. 1-toggle = precursor with T closed')
    for init, ai in ((S1, 'r'), (S2, 'l')):
        N = net({'p': (with_init(Pp, init), {'A': 'tT', 'B': 'tT', 'C': 'tT', 'E': 'E', 'F': 'F'})}, ['E', 'F']).explore()
        ok &= verdict(N, T_toggle(ai), f'init {ai} (blocks {track(bp, init, 2)}; r = E->F passable)')

    # 4. diode
    bd = K.Board(PROTODIODE)
    Cd = K.explore(bd)
    dclean, dabsL, dabsA, Pd = postselect_L(Cd, PD_CHECKS, ['A', 'B', 'C', 'D'])
    print('== 4. checkable protodiode (Fig. 35a), C-D joined')
    print(f'  clean {len(dclean)} of {len(Cd.states)}; absorbing {dabsL}')
    N = net({'d': (Pd, {'A': 'A', 'B': 'B', 'C': 'cd', 'D': 'cd'})}, ['A', 'B']).explore()
    ok &= verdict(N, AC.T_diode(), 'diode')
    ok &= dabsL

    # 5. SCD (Fig. 37)
    def scd_net(Pprec, Ptog, Pdio, prec_init, extra_ports=False):
        pm_prec = {'A': 'T', 'B': 'T', 'C': 'T', 'E': 'X', 'F': 'Y'}
        pm_tog = {'A': 'tT', 'B': 'tT', 'C': 'tT', 'E': 'O', 'F': 'T'}
        if extra_ports:                       # raw components: hidden check locations become private pockets
            pm_prec.update(D='pD', G='pG')
            pm_tog.update(D='tD', G='tG')
        g = {'prec': (with_init(Pprec, prec_init), pm_prec),
             'tog': (with_init(Ptog, S1), pm_tog),
             'd1': (Pdio, {'A': 'I', 'B': 'X', 'C': 'd1cd', 'D': 'd1cd'}),
             'd2': (Pdio, {'A': 'Y', 'B': 'J', 'C': 'd2cd', 'D': 'd2cd'})}
        return Net2(g, {'O': 'O', 'I': 'I', 'J': 'J'})

    print('== 5a. SCD (Fig. 37) from postselected components, then postselect [O->O, I->J]')
    names = None
    results = {}
    for prec_init, ai in ((S1, 'o'), (S2, 'c')):
        NW = scd_net(Pp, Pp, Pd, prec_init)
        names = NW.names
        N = NW.explore()
        sclean, sabs, P = K.postselect(N, [('O', 'O'), ('I', 'J')])
        broken = [s for s in N.states if s not in sclean]
        print(f'  init {"open " if ai == "o" else "closed"} (precursor blocks {track(bp, prec_init, 2)}): '
              f'{len(N.states)} states, {len(sclean)} clean, broken absorbing {sabs}')
        for st in N.states:
            desc = ' '.join(f'{n}={track(bp, x, 2) if n in ("prec", "tog") else track(bd, x, 1)}' for n, x in zip(names, st))
            rel = sorted({(p, q) for p in N.ports for q, _ in N.T[(st, p)] if q != p})
            print(f'    {"clean " if st in sclean else "BROKEN"} {desc}  relation {", ".join(p + "->" + q for p, q in rel) or "(none)"}')
        s, c, _, _ = K.check(N, T_scd(ai))
        print(f'    raw composite vs ideal SCD: SOUND {s} COMPLETE {c}')
        ok &= verdict(P, T_scd(ai), 'postselected composite vs ideal SCD') and sabs
        results[ai] = sclean

    print('== 5b. flat: raw concrete components (D/G pockets), clean = all components clean + 5a-clean')
    for prec_init, ai in ((S1, 'o'), (S2, 'c')):
        NW = scd_net(Cp, Cp, Cd, prec_init, extra_ports=True)
        N = NW.explore()
        comp_ok = {'prec': clean, 'tog': clean, 'd1': dclean, 'd2': dclean}
        cl = {st for st in N.states if all(x in comp_ok[n] for n, x in zip(NW.names, st)) and st in results[ai]}
        absorbing = all(s2 not in cl for st in N.states if st not in cl for p in N.ports for _, s2 in N.T[(st, p)])
        T = {(st, p): {(q, s2) for q, s2 in N.T[(st, p)] if s2 in cl} for st in cl for p in N.ports}
        P = K.System(N.ports, N.init, T, sorted(cl))
        nb = len(N.states) - len(cl)
        print(f'  init {ai}: raw network {len(N.states)} states ({len(cl)} clean, {nb} broken); '
              f'broken absorbing in the raw network (G3): {absorbing}')
        ok &= verdict(P, T_scd(ai), 'flat postselected vs ideal SCD') and absorbing
        s, c, _, _ = K.check(N, T_scd(ai))
        print(f'    raw flat (no postselection) vs ideal SCD: SOUND {s} COMPLETE {c}')
        if verbose:
            # list what a broken raw state can still do
            kinds = {}
            for st in N.states:
                if st in cl:
                    continue
                rel = tuple(sorted({(p, q) for p in N.ports for q, _ in N.T[(st, p)] if q != p}))
                kinds[rel] = kinds.get(rel, 0) + 1
            for r, n in sorted(kinds.items(), key=lambda kv: -kv[1]):
                print(f'      {n:5d} broken states, relation {", ".join(p + "->" + q for p, q in r) or "(none)"}')

    # 6. D_game cross-check on the proto-precursor window
    print('== 6. D_game.py relation cross-check (proto-precursor window, clean states)')
    try:
        import D_game as DG
        txt = [r.replace('A', '.').replace('B', '.').replace('C', '.').replace('D', '.').replace('E', '.')
               .replace('F', '.').replace('G', '.') for r in PROTO_PRECURSOR]
        for n, i in bp.ports.items():
            x, y = bp.cells[i]
            txt.append(f':port {n} {x} {y}')
        sts = {}
        for s in sorted(clean, key=lambda s: track(bp, s, 2)):
            nm = 'k' + ''.join(map(str, track(bp, s, 2)))
            sts[nm] = s
            txt.append(f':state {nm} ' + ' '.join(f'{x} {y}' for x, y in blocks(bp, s)))
        L = DG.Level('\n'.join(txt))
        info, rel = DG.relation(L)
        mism = 0
        tot = 0
        for r in rel:
            if r['state'] not in sts or r['frm'] in ('@', 'G') or r['to'] in ('@', 'G'):
                continue
            s = sts[r['state']]
            cl = closure_rel(Cp, s, r['frm'])
            if r['exit_state'] == '*':
                mine = any(q == r['to'] for q, _ in cl)
            elif r['exit_state'] in sts:
                mine = (r['to'], sts[r['exit_state']]) in cl
            else:
                continue
            tot += 1
            if mine != r['win']:
                mism += 1
                print('    MISMATCH', r, mine)
        print(f'  {tot} relation entries compared (A_core chained traversals vs D_game attractor): {mism} mismatches')
        ok &= mism == 0
    except Exception as e:      # pragma: no cover
        print('  D_game cross-check failed to run:', repr(e))
        ok = False

    print('ALL AS EXPECTED' if ok else 'SOME UNEXPECTED RESULT')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
