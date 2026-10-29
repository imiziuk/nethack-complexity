#!/usr/bin/env python3
"""A_check.py -- exhaustive local verification of the workstream-A gadget library (see proofs/exptime/A-gadgets.md).

For every gadget: enumerate all local states reachable from the initial boulder set by traversals from any port
(A_core.explore; a boulder able to reach a port cell aborts with LEAK), print the port-to-port relation per state, and
check game-safety = sound and complete simulation against the intended automaton (A_core.check).

Usage: python A_check.py            (all gadgets)
       python A_check.py diode -v   (one gadget, print every state)
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import A_core as K


# ---------------- intended automata ----------------
def T_diode():
    return K.abstract(['A', 'B'], 'd', {'d': {'A': [('B', 'd')]}})


def T_scd_button():
    # self-closing door, opening button O (visit O: O->O sets open), traverse tunnel I->J only when open, closes.
    return K.abstract(['I', 'J', 'O'], 'c', {
        'c': {'O': [('O', 'o')]},
        'o': {'O': [('O', 'o')], 'I': [('J', 'c')]},
    })


def T_scd_button_open():
    a = T_scd_button()
    a.init = 'o'
    return a


def T_scd_tunnel():
    # opening tunnel O->P (always passable, sets open), traverse tunnel I->J (only open, closes)
    return K.abstract(['I', 'J', 'O', 'P'], 'c', {
        'c': {'O': [('P', 'o')]},
        'o': {'O': [('P', 'o')], 'I': [('J', 'c')]},
    })


def T_xover():
    # directed crossover: A->B and C->D, each any number of times, nothing else
    return K.abstract(['A', 'B', 'C', 'D'], 'x', {'x': {'A': [('B', 'x')], 'C': [('D', 'x')]}})


def T_uxover():
    # undirected crossover
    return K.abstract(['A', 'B', 'C', 'D'], 'x', {'x': {'A': [('B', 'x')], 'B': [('A', 'x')],
                                                       'C': [('D', 'x')], 'D': [('C', 'x')]}})


def T_toggle1():
    # 1-toggle: tunnel A<->B traversable in one direction, flips direction
    return K.abstract(['A', 'B'], 'r', {'r': {'A': [('B', 'l')]}, 'l': {'B': [('A', 'r')]}})


TARGETS = {'diode': T_diode, 'scd': T_scd_button, 'scd4': T_scd_tunnel, 'xover': T_xover,
           'uxover': T_uxover, 'toggle1': T_toggle1}
NPORTS = {'diode': 2, 'scd': 3, 'scd4': 4, 'xover': 4, 'uxover': 4, 'toggle1': 2}


# ---------------- concrete gadgets (filled in by the library) ----------------
GADGETS = {}


def report(name, rows, target, verbose=False):
    b = K.Board(rows)
    print(f'== {name}  (target {target}; {b.W}x{b.H} box, {len(b.cells)} floor cells, '
          f'{bin(b.b0).count("1")} boulders)')
    print('\n'.join(rows))
    try:
        C = K.explore(b)
    except K.LeakError as e:
        print('LEAK: a boulder can reach a port cell', e)
        return False
    A = TARGETS[target]()
    s, c, Rs, Rc = K.check(C, A)
    rel = K.relation_table(C)
    kinds = {}
    for st, r in rel.items():
        kinds.setdefault(tuple(r), []).append(st)
    print(f'reachable local states: {len(C.states)}; distinct port relations: {len(kinds)}')
    for r, sts in sorted(kinds.items(), key=lambda kv: -len(kv[1])):
        abs_of = sorted({a for st in sts for (cc, a) in Rs if cc == st})
        print(f'  {len(sts):4d} states  relation {", ".join(p + "->" + q for p, q in r) or "(none)"}'
              f'   simulated by abstract {abs_of}')
        if verbose:
            for st in sts:
                print(b.show(st))
                print()
    print(f'SOUND (concrete <= intended): {s}   COMPLETE (intended <= concrete): {c}')
    return s and c


def report_checkable(name, rows, checks, joins, ext, target):
    b = K.Board(rows)
    print(f'== {name}  (checkable; target {target} after joining {joins}; checks {checks})')
    print('\n'.join(rows))
    C = K.explore(b)
    clean, absorbing, P = K.postselect(C, checks)
    rel = K.relation_table(C)
    for st in C.states:
        print(f'  {"clean " if st in clean else "BROKEN"} relation {", ".join(p + "->" + q for p, q in rel[st])}')
        print('    ' + b.show(st).replace(chr(10), chr(10) + '    '))
    N = K.wire(P, joins, ext)
    s, c, _, _ = K.check(N, TARGETS[target]())
    Nraw = K.wire(C, joins, ext)
    sr, cr, _, _ = K.check(Nraw, TARGETS[target]())
    print(f'broken absorbing (G3): {absorbing}; init clean: {C.init in clean}')
    print(f'postselected + wired vs {target}: SOUND {s} COMPLETE {c}   (raw, no postselection: SOUND {sr} COMPLETE {cr})')
    return absorbing and s and c and C.init in clean


def main():
    import A_library as L
    verbose = '-v' in sys.argv
    sel = [a for a in sys.argv[1:] if not a.startswith('-')]
    ok = True
    for n, (rows, mk) in L.SANITY.items():
        if sel and n not in sel:
            continue
        b = K.Board(rows)
        C = K.explore(b)
        s, c, _, _ = K.check(C, mk())
        print(f'== sanity {n}: {len(C.states)} states, SOUND {s} COMPLETE {c}')
        ok &= s and c
    for n, (rows, target) in L.LIB.items():
        if sel and n not in sel:
            continue
        ok &= report(n, rows, target, verbose)
        print()
    for n, args in L.CHECKABLE.items():
        if sel and n not in sel:
            continue
        ok &= report_checkable(n, *args)
        print()
    for n, (rows, target) in L.NEGATIVE.items():
        if sel and n not in sel:
            continue
        print('(negative example, expected to FAIL)')
        res = report(n, rows, target, verbose)
        ok &= not res
        print()
    for n, mk in getattr(L, 'NETS', {}).items():
        if sel and n not in sel:
            continue
        N, target = mk()
        s, c, _, _ = K.check(N, TARGETS[target]())
        print(f'== network {n}: {len(N.states)} states vs {target}: SOUND {s} COMPLETE {c}')
        ok &= s and c
    print('ALL AS EXPECTED' if ok else 'SOME UNEXPECTED RESULT')


if __name__ == '__main__':
    main()
