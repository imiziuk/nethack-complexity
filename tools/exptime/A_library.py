#!/usr/bin/env python3
"""A_library.py -- the workstream-A gadget library (layouts + intended automata), checked by A_check.py.

LIB[name] = (rows, target)   locally exact gadgets (pure: every reachable state checked, sound + complete)
CHECKABLE[name] = (rows, checks, joins, ext, target)   postselected gadgets (A-gadgets.md §2-3)
NEGATIVE[name] = (rows, target)   instructive failures, expected to FAIL (documented counterexamples)
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import A_core as K

# ---- sanity: hu-on-lower §3.3 G_D one-way door (single use; NOT reusable, used only as an engine test) ----
GD_ROWS = ["######",
           "E.e0.#",
           "###q##",
           "###Q##"]
# ports E (outside, entry side) and Q (exit side); e, q are named floor cells (documentation)


def T_gd():
    # closed: E->Q (or a visit E->E) opens it (boulder into pocket); open: free both ways. Q->E never while closed.
    return K.abstract(['E', 'Q'], 'c', {'c': {'E': [('Q', 'o'), ('E', 'o')]}, 'o': {'E': [('Q', 'o')], 'Q': [('E', 'o')]}})


# ---- checkable diode = Ani et al. protodiode (block confined to the middle two track cells), C and D joined ----
PROTODIODE = ["#A#B##",
              "#.0..#",
              "##C#D#",
              "######"]
#   track row y=1: e1=(1,1) m1=(2,1) m2=(3,1) e2=(4,1); block X starts on m1.
#   A above e1, B above m2, C below m1, D below e2.

# ---- negative examples (expected FAIL as pure gadgets): overshoot ----
SLOT1 = ["#A#B##",      # one-boulder slot, return push from the far end: overshoot into R opens B->A
         "#.0..#",
         "##.#.#",
         "##...#",
         "######"]
UTURN2 = ["########",   # two boulders (Z behind-blocker on a U-turn, Y interlock): complete, but unsound
          "##...###",
          "##.#.###",
          "##.#.#.B",
          "#.0.0..#",
          "#.#....#",
          "#A##..##",
          "########"]

LIB = {}
NEGATIVE = {'slot1': (SLOT1, 'diode'), 'uturn2': (UTURN2, 'diode')}
CHECKABLE = {'diode_ck': (PROTODIODE, [('A', 'C'), ('D', 'B')], [('C', 'D')], ['A', 'B'], 'diode')}
SANITY = {'gd_single_use': (GD_ROWS, T_gd)}


# ---- abstract networks (ideal gadgets wired by free corridors) ----
def net_naive_xover():
    """two directed-tunnel SCDs sharing a middle node M: sound + complete directed crossover, but NOT planar
    (A-gadgets.md §6). Returns (network System, target name)."""
    import A_check as AC
    d = AC.T_scd_tunnel()
    net = K.Network({'d1': (d, {'O': 'A', 'P': 'M', 'I': 'M', 'J': 'B'}),
                     'd2': (d, {'O': 'C', 'P': 'M', 'I': 'M', 'J': 'D'})},
                    {'A': 'A', 'B': 'B', 'C': 'C', 'D': 'D'})
    return net.explore(), 'xover'


NETS = {'naive_xover_nonplanar': net_naive_xover}
