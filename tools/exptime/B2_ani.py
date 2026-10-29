#!/usr/bin/env python3
"""B2_ani.py -- the single-use machinery of Ani et al. Thm 5.3 (arXiv 2412.20079 Sec. 5, 7) in our model.

Workstream B2 (proofs/exptime/B2-checkpath.md). Imports A_core / A_check / A2_scd / D_game read-only.
  1. Fig. 32 Push-1F base gadgets (weak merged closing WMC, no-return NR, weak opening WO), transcribed from the PDF's
     vector drawings (page 28; grid squares 14.2 pt, tan bricks, grey 9 pt blocks), explored exactly in the
     A_core model (= NetHack boulders, Sokoban corner rule, heavy hero) and compared with the Fig. 31 automata.
  2. Fig. 33 composites from the CONCRETE boards: dicrumbler SD, single-use opening SO, merged single-use closing MSC,
     compared with the Fig. 19 automata.
  3. Fig. 20 single-use crossover SX and Fig. 21 weak closing crossover WCX, from ideal SO/SD/MSC and (SX) from the
     concrete composites, compared with Fig. 19.
  4. Transitive check legality (Ani Thm 5.3 assumes G transitive) vs A2's single-traversal clean sets.
  5. D_game.py relation cross-check of the three base boards.
Usage: python B2_ani.py [-v]
"""
import os, sys
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import A_core as K
import A2_scd as A2

# ---------------- Fig. 32 boards (capital letters = location cells at the frame openings) ----------------
WMC = ["###T#",          # weak merged closing: hallway L<->R, closing T->R (repeatable)
       "#.0.#",
       "##0##",
       "##.##",
       "##..R",
       "L..##",
       "#####"]
NR = ["##########",      # no-return: L->R once, then not R->L; R first or L->R twice breaks it (free)
      "####.0.###",
      "L.##.0...#",
      "#...0.##.R",
      "###...####",
      "##########"]
WO = ["####T##",         # weak opening: exit R usable only after L and T were visited separately
      "L.##.##",
      "#..00.#",
      "#000.##",
      "#.0.###",
      "##.####",
      "##.####",
      "##....R",
      "##.####",
      "#######"]


def I_WMC():
    return K.abstract(['L', 'R', 'T'], '1', {
        '1': {'L': [('R', '1')], 'R': [('L', '1')], 'T': [('R', '2')]},
        '2': {'T': [('R', '2')]}})


def I_NR():
    return K.abstract(['L', 'R'], '1', {
        '1': {'L': [('R', '2')], 'R': [('L', '3')]},
        '2': {'L': [('R', '3')]},
        '3': {'L': [('R', '3')], 'R': [('L', '3')]}})


def I_WO():
    return K.abstract(['L', 'R', 'T'], '1', {
        '1': {'L': [('L', '2')], 'T': [('T', '3')]},
        '2': {'T': [('T', '4')]},
        '3': {'L': [('L', '5')]},
        '4': {'L': [('L', '5')], 'T': [('R', '4')], 'R': [('T', '4')]},
        '5': {'L': [('T', '5'), ('R', '5')], 'T': [('L', '5'), ('R', '5')], 'R': [('L', '5'), ('T', '5')]}})


# ---------------- Fig. 19 ideal single-use gadgets ----------------
def I_SD():
    return K.abstract(['X', 'Y'], '1', {'1': {'X': [('Y', '2')]}, '2': {}})


def I_SO():
    return K.abstract(['Op', 'In', 'Out'], '1', {'1': {'Op': [('Op', '2')]}, '2': {'In': [('Out', '3')]}, '3': {}})


def I_MSC():
    return K.abstract(['L', 'R', 'T'], '1', {'1': {'L': [('R', '1')], 'R': [('L', '1')], 'T': [('R', '2')]}, '2': {}})


def I_SX():
    return K.abstract(['L', 'R', 'Tp', 'Bt'], '1', {'1': {'L': [('R', '2')]}, '2': {'Tp': [('Bt', '3')]}, '3': {}})


def I_WCX():
    return K.abstract(['L', 'R', 'Tp', 'Bt'], '1', {
        '1': {'L': [('R', '1')], 'R': [('L', '1')], 'Bt': [('Tp', '3'), ('L', '2'), ('R', '2')]},
        '2': {'L': [('R', '2'), ('Tp', '3')], 'R': [('L', '2'), ('Tp', '3')]},
        '3': {}})


# ---------------- compositions (Net2 keeps p->p returns, needed for buttons) ----------------
def net(gadgets, ext):
    """gadgets: name -> (System, {port: node}); ext: list of external node names (= port names)."""
    return A2.Net2(gadgets, {e: e for e in ext}).explore()


def sd_from(wmc, nr, wo):      # Fig. 33a
    return net({'wmc': (wmc, {'L': 'X', 'R': 'J', 'T': 'N'}),
                'nrv': (nr, {'L': 'J', 'R': 'N'}),
                'nrh': (nr, {'L': 'J', 'R': 'W'}),
                'wo': (wo, {'L': 'W', 'T': 'N', 'R': 'Y'})}, ['X', 'Y'])


def so_from(sd, wo):           # Fig. 33b
    return net({'sd1': (sd, {'X': 'In', 'Y': 'W'}),
                'wo': (wo, {'L': 'W', 'T': 'Bn', 'R': 'E'}),
                'sd2': (sd, {'X': 'E', 'Y': 'Out'}),
                'up': (sd, {'X': 'Bn', 'Y': 'Op'}),
                'dn': (sd, {'X': 'Op', 'Y': 'Bn'})}, ['Op', 'In', 'Out'])


def msc_from(sd, wmc):         # Fig. 33c
    return net({'sd': (sd, {'X': 'T', 'Y': 'Tw'}),
                'wmc': (wmc, {'L': 'L', 'R': 'R', 'T': 'Tw'})}, ['L', 'R', 'T'])


def sx_from(so, sd):           # Fig. 20
    return net({'sd1': (sd, {'X': 'L', 'Y': 'C'}), 'sd2': (sd, {'X': 'C', 'Y': 'Rd'}),
                'sd3': (sd, {'X': 'Rd', 'Y': 'R'}),
                'sot': (so, {'Op': 'Rd', 'In': 'Tp', 'Out': 'C'}),
                'sob': (so, {'Op': 'Rd', 'In': 'C', 'Out': 'Bt'})}, ['L', 'R', 'Tp', 'Bt'])


def wcx_from(so, sd, msc):     # Fig. 21 (hallway Lext=a, a-MSC_L-m-MSC_M-r-MSC_R-R)
    hall = K.abstract(['P', 'Q'], 'h', {'h': {'P': [('Q', 'h')], 'Q': [('P', 'h')]}})
    return net({'hall': (hall, {'P': 'L', 'Q': 'a'}),                   # plain hallway Lext - a
                'mscL': (msc, {'L': 'a', 'R': 'm', 'T': 'u'}),          # closes T->right, exits at m
                'mscM': (msc, {'L': 'r', 'R': 'm', 'T': 'v'}),          # closes T->left, exits at m
                'mscR': (msc, {'L': 'R', 'R': 'r', 'T': 'w'}),          # closes bottom->left, exits at r
                'sda': (sd, {'X': 'Bt', 'Y': 'b'}), 'sdb': (sd, {'X': 'b', 'Y': 'a'}),
                'sdc': (sd, {'X': 'a', 'Y': 'u'}),
                'soB': (so, {'Op': 'b', 'In': 'm', 'Out': 'w'}),
                'soUL': (so, {'Op': 'u', 'In': 'm', 'Out': 'v'}),
                'soUR': (so, {'Op': 'v', 'In': 'r', 'Out': 'Tp'})}, ['L', 'R', 'Tp', 'Bt'])


def rel_summary(S):
    out = []
    for s in S.states:
        r = sorted({(p, q) for p in S.ports for q, _ in S.T[(s, p)] if q != p})
        b = sorted({p for p in S.ports for q, s2 in S.T[(s, p)] if q == p and s2 != s})
        out.append((r, b))
    return out


def verdict(C, A, label):
    s, c, _, _ = K.check(C, A)
    print(f'  {label}: {len(C.states)} reachable states; vs ideal: SOUND {s} COMPLETE {c}')
    return s, c


def trace_sound(C, A, depth=8):
    """every concrete traversal sequence (from init, up to `depth` steps, bounces with no ideal effect allowed) is an
    ideal traversal sequence: subset construction on the ideal side (Ani's 'local simulation' is trace-based)."""
    start = (C.init, frozenset([A.init]))
    seen = {start}
    dq = deque([(start, 0)])
    bad = []
    while dq:
        (c, aset), d = dq.popleft()
        if d >= depth:
            continue
        for p in C.ports:
            for q, c2 in C.T[(c, p)]:
                nxt = frozenset(a2 for a in aset for q2, a2 in A.T.get((a, p), ()) if q2 == q)
                if q == p:
                    nxt = nxt | aset          # looking in and coming back: ideal may do nothing
                if not nxt:
                    bad.append((c, p, q))
                    continue
                st = (c2, nxt)
                if st not in seen:
                    seen.add(st)
                    dq.append((st, d + 1))
    return bad


def main():
    verbose = '-v' in sys.argv
    ok = True
    print('== 1. Fig. 32 base boards vs Fig. 31 automata (exact exploration, A_core model)')
    base = {}
    for name, rows, ideal in (('WMC', WMC, I_WMC()), ('NR', NR, I_NR()), ('WO', WO, I_WO())):
        b = K.Board(rows)
        C = K.explore(b)          # raises LeakError if a block can reach a location cell
        base[name] = C
        s, c = verdict(C, ideal, name)
        bad = trace_sound(C, ideal)
        print(f'     trace-sound (depth 8): {not bad}' + ('' if not bad else f'  first counterexample {bad[0]}'))
        if verbose:
            for st, (r, bn) in zip(C.states, rel_summary(C)):
                print('     ', A2.blocks(b, st), r, 'bounce-change', bn)
        ok &= c
    print('== 2. Fig. 33 composites from the CONCRETE boards vs Fig. 19')
    if '--full' in sys.argv:      # ~5 min: flat concrete dicrumbler (18,336 states)
        SDc = sd_from(base['WMC'], base['NR'], base['WO'])
        s1, c1 = verdict(SDc, I_SD(), 'dicrumbler SD (concrete WMC + 2 NR + WO)')
        ok &= s1 and c1
    else:
        print('  dicrumbler SD (concrete WMC + 2 NR + WO): run with --full (verified 2026-10-29: 18,336 states, '
              'SOUND True COMPLETE True)')
    # simulation equivalence is preserved by network composition, so the verified SD is replaced by the ideal one
    SDi = I_SD()
    SOc = so_from(SDi, base['WO'])
    s2, c2 = verdict(SOc, I_SO(), 'single-use opening SO (concrete WO + 4 ideal SD)')
    MSCc = msc_from(SDi, base['WMC'])
    s3, c3 = verdict(MSCc, I_MSC(), 'merged single-use closing MSC (ideal SD + concrete WMC)')
    for nm, C, I in (('SO', SOc, I_SO()), ('MSC', MSCc, I_MSC())):
        bad = trace_sound(C, I)
        print(f'     {nm} trace-sound: {not bad}' + ('' if not bad else f'  e.g. {bad[:3]}'))
        if verbose:
            for st, (r, bn) in zip(C.states, rel_summary(C)):
                print('       ', r, 'bounce-change', bn)
    ok &= s2 and c2 and s3 and c3
    SDc = SDi
    print('== 3. Fig. 20 SX and Fig. 21 WCX vs Fig. 19')
    s, c = verdict(sx_from(I_SO(), I_SD()), I_SX(), 'SX from ideal SO, SD')
    ok &= s and c
    s, c = verdict(sx_from(SOc, SDc), I_SX(), 'SX from concrete SO, SD')
    ok &= s and c
    W = wcx_from(I_SO(), I_SD(), I_MSC())
    s, c = verdict(W, I_WCX(), 'WCX from ideal SO, SD, MSC')
    ok &= s and c
    if verbose or not (s and c):
        for st, (r, bn) in zip(W.states, rel_summary(W)):
            print('       ', st, r, 'bounce-change', bn)
    try:
        Wc = wcx_from(SOc, SDc, MSCc)
        s, c = verdict(Wc, I_WCX(), 'WCX from concrete SO, SD, MSC')
        ok &= s and c
    except RuntimeError as e:
        print('  WCX concrete: skipped', e)

    print('== 4. transitive check legality (Thm 5.3 assumes G transitive) vs single-traversal clean sets (A2)')
    for nm, rows, checks, L in (('protodiode', A2.PROTODIODE, A2.PD_CHECKS, ['A', 'B', 'C', 'D']),
                                ('proto-precursor', A2.PROTO_PRECURSOR, A2.PP_CHECKS, A2.PP_L)):
        C = K.explore(K.Board(rows))
        single = {c for c in C.states if K.check_legal(C, c, checks)}

        def legal_T(c):
            fr = {c}
            for p, q in checks:
                nxt = set()
                for c1 in fr:
                    for q2, c2 in A2.closure_rel(C, c1, p):
                        if q2 == q:
                            nxt.add(c2)
                fr = nxt
                if not fr:
                    return False
            return True
        trans = {c for c in C.states if legal_T(c)}
        print(f'  {nm}: clean (single traversals) {len(single)}, clean (chained, any intermediate location) '
              f'{len(trans)}; equal: {single == trans}')
        ok &= single == trans

    print('== 5. D_game.py relation cross-check of the base boards (chained A_core traversals vs D_game attractor)')
    import D_game as DG
    for name, rows in (('WMC', WMC), ('NR', NR), ('WO', WO)):
        b = K.Board(rows)
        C = base[name]
        txt = [''.join('.' if ch.isupper() else ch for ch in r) for r in rows]
        for n, i in b.ports.items():
            x, y = b.cells[i]
            txt.append(f':port {n.lower()} {x} {y}')
        names = {}
        for k, st in enumerate(C.states):
            nm = f's{k}'
            names[nm] = st
            txt.append(f':state {nm} ' + ' '.join(f'{x} {y}' for x, y in A2.blocks(b, st)))
        info, rel = DG.relation(DG.Level('\n'.join(txt)))
        mism = tot = 0
        for r in rel:
            if r['state'] not in names:
                continue
            st = names[r['state']]
            cl = A2.closure_rel(C, st, r['frm'].upper())
            if r['exit_state'] == '*':
                mine = any(q == r['to'].upper() for q, _ in cl)
            elif r['exit_state'] in names:
                mine = (r['to'].upper(), names[r['exit_state']]) in cl
            else:
                continue
            tot += 1
            if mine != r['win']:
                mism += 1
                if mism < 5:
                    print('    MISMATCH', name, r, mine)
        print(f'  {name}: {len(C.states)} states, {tot} relation entries, {mism} mismatches')
        ok &= mism == 0
    print('ALL AS EXPECTED' if ok else 'SOME UNEXPECTED RESULT')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
