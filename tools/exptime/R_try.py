"""R_try.py -- debug probe: run the step queries of one gadget in one game (batch size argv[2]), report failures."""
import sys, time, random, subprocess
import R_model as M, R_oracle as O, R_game
import R_run as RR

name = sys.argv[1]
bs = int(sys.argv[2]) if len(sys.argv) > 2 else 50
w = RR.WINDOWS[name]
qs, info = RR.step_queries(name, random.Random(1))
if len(sys.argv) > 4:
    keep = sys.argv[4]
    qs = [q for q in qs if (RR.expect_of(w, w.idx[q[1]], w.mask(q[2]), w.mask(q[3]), q[4])[0] == 'loss') == (keep == 'loss')]
print(name, len(qs), info)
g = R_game.Game('p'); g.start()
t = time.time()
try:
    res = O.run_fast(g, w, qs[:int(sys.argv[3])] if len(sys.argv) > 3 else qs, batch=bs, timeout=60,
                     log=lambda s: print('LOG', s))
except Exception as e:
    print('ERR', str(e)[-800:])
    print('\n'.join(x.rstrip() for x in g.screen() if x.strip()))
    print(subprocess.run(['bash', '-c', 'grep -v "^\\s*$" ' + g.hack + '/paniclog | tail -15'],
                         capture_output=True, text=True).stdout)
    g.close()
    raise SystemExit(1)
print('fast', len(res), 'in %.2fs' % (time.time() - t))
bad = 0
for q in qs:
    if q[0] not in res:
        continue
    ok, real, pred = RR.compare(w, q, res[q[0]])
    if not ok:
        bad += 1
        if bad < 15:
            print('MISMATCH', q, '| real', real, '| pred', pred)
print('mismatches', bad)
g.close()
