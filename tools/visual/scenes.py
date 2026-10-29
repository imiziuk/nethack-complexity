"""Scene list for the visual demo: level, typed keys, captions. Shared by capture.py (WSL) and render.py."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
KEYNAME = {'h': 'h (west)', 'j': 'j (south)', 'k': 'k (north)', 'l': 'l (east)', 'u': 'u (north-east)',
           'y': 'y (north-west)', 'b': 'b (south-west)', 'n': 'n (south-east)', 'ml': 'm l (move east, never push)'}


def board(level):
    return open(os.path.join(HERE, 'levels', level + '.txt')).read().rstrip('\n').split('\n')


def cell_of(level, ch):
    for y, r in enumerate(board(level)):
        x = r.find(ch)
        if x >= 0:
            return x, y
    return None


def screen_of(mx, my):
    # map placed at absolute (1,0); tty shows map column x at screen column x-1 and map row y at screen row y+1
    return mx + 1 - 1, my + 1


SCENES = [
    dict(id='a1_push', level='a1_push', start='@',
         title='1. Orthogonal push',
         caption='Pushing a boulder moves it one square; the hero follows. Against a wall the push fails, '
                 'and the heavy hero (cursed loadstone) cannot squeeze onto the boulder square.',
         keys=[('l', 'push east'), ('l', 'push east'), ('l', 'push east'), ('l', 'push east'),
               ('l', 'push into the wall: refused'), ('ml', 'm-prefix move: still blocked')]),
    dict(id='a2_diag', level='a2_diag', start='@',
         title='2. No diagonal pushes',
         caption='The level has the Sokoban flag: a diagonal push is refused, exactly like Push-1F, '
                 'where blocks move only in the 4 directions.',
         keys=[('u', 'diagonal push: refused'), ('k', 'step north'), ('l', 'orthogonal push works')]),
    dict(id='a3_squeeze', level='a3_squeeze', start='@',
         title='3. No squeezing between boulders',
         caption='A diagonal step between two boulders is refused, so a diagonal step is only ever '
                 'a shortcut for two orthogonal steps.',
         keys=[('u', 'squeeze between boulders: refused'), ('l', 'push east instead'),
               ('k', 'now the way north is open')]),
    dict(id='b_wrong', level='b_puzzle', start='@', goal='g',
         title='4a. Puzzle, wrong order',
         caption='Goal g. Pushing the boulder in front of g first jams it onto g against the wall: '
                 'no later push can free it. The level is lost. (Right: the sealed sentinel pit of the reduction, '
                 'unreachable; it keeps the Sokoban rules on.)',
         keys=[('l', 'walk'), ('l', 'walk'), ('l', 'walk'), ('l', 'push the lower boulder first: it lands on g'),
               ('k', 'push north: wall behind, refused'), ('h', 'walk'), ('k', 'walk'),
               ('l', 'push the upper boulder away'), ('j', 'walk'),
               ('l', 'boulder on g, wall behind: stuck forever')]),
    dict(id='b_right', level='b_puzzle', start='@', goal='g',
         title='4b. Puzzle, right order',
         caption='First push the upper boulder away, then push the lower boulder down into the pocket: '
                 'the corridor to g opens.',
         keys=[('l', 'walk'), ('l', 'walk'), ('l', 'walk'), ('k', 'walk'), ('l', 'push the upper boulder first'),
               ('j', 'push the lower boulder into the pocket'), ('l', 'step onto g: solved')]),
    dict(id='c_oneway', level='c_oneway', start='a', labels='ab',
         title='5. Gadget: self-closing one-way door',
         caption='From a the hero can reach b, and on the way he pushes the door boulder back into the '
                 'doorway behind him. From b there is no way back to a.',
         keys=[('l', 'push the door boulder east'), ('j', 'walk'), ('l', 'walk'), ('l', 'walk'),
               ('k', 'push the side boulder out of the way'), ('h', 'push the door boulder back: arrive at b'),
               ('j', 'try to go back...'), ('h', 'walk'), ('k', 'push north: blocked by the other boulder')]),
]

for sc in SCENES:
    sc['expect_screen'] = screen_of(*cell_of(sc['level'], sc['start']))
