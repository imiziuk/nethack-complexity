"""R_oracle.py -- in-game single-step / walk oracle for gadget windows (real compiled NetHack 5.0.0, wizard mode).

Fast mode (lua): one #wizloadlua script runs a whole batch of queries inside ONE game session. Per query it rebuilds
the level from scratch (des.reset_level; noflip + sokoban + noteleport + solidify + premapped flags, solidfill stone,
des.map of the window, des.object boulders, des.trap holes, sealed sentinel pit, branch stair forced into a sealed
pocket, 1-cell teleport_region on the hero cell, finalize; hunger and monster generation off; inventory = one cursed
loadstone), verifies the hero stands on the requested cell (else retries, max 10 builds), then feeds the keys through
the game's own command queue (nh.pushkey + nh.doturn = rhack -> domove, the same path as a typed key), and reads the
true engine state back: hero cell, dungeon level (falling through a hole changes it), boulders (obj.at) and the traps
left in the window. All game messages are suppressed (MSGTYPE=hide) in this mode for speed.

Screen mode: the same level is built by a script, then the key is TYPED into the tty; the message line (every
--More-- page) and the hero glyph are read from the pyte screen; the ground truth is read by a dump script.
"""
import re
import R_game

BUILD = r'''
nh.debug_flags({ mongen = false, hunger = false });
%(hide)s
local OX, OY = 2, 2;
local MAP = [[
%(map)s]];
local W, H = %(W)d, %(H)d;
local CELLS = {%(cells)s};
local HC = {%(hc)s};
local function build(hx, hy, bs, hs)
  for attempt = 1, 10 do
    des.reset_level();
    des.level_flags("noflip", "sokoban", "noteleport", "solidify", "premapped");
    des.level_init({ style = "solidfill", fg = " ", lit = true });
    des.map({ x = OX, y = OY, map = MAP });
    for i = 1, #bs, 2 do des.object("boulder", bs[i], bs[i + 1]); end
    for i = 1, #hs, 2 do des.trap("hole", hs[i], hs[i + 1]); end
    des.trap("pit", %(SX)d, %(SY)d);
    des.levregion({ region = { %(PX)d + OX, %(PY)d + OY, %(PX)d + OX, %(PY)d + OY }, region_islev = true, type = "branch" });
    des.teleport_region({ region = { hx + OX, hy + OY, hx + OX, hy + OY }, region_islev = true, dir = "both" });
    des.finalize_level();
    u.clear_inventory();
    u.giveobj(obj.new("cursed loadstone"));
    if (u.ux == hx + OX and u.uy == hy + OY) then return attempt; end
  end
  return 0;
end
local function snap(d0)
  if (u.dlevel ~= d0) then return "FELL:" .. u.dlevel; end
  local s = (u.ux - OX) .. "." .. (u.uy - OY) .. " b=";
  local o = obj.next();               -- whole floor chain (fobj): every boulder on the level
  while (o ~= nil and not o:isnull()) do
    local t = o:totable();
    if (t.otyp_name == "boulder") then s = s .. (t.ox - OX) .. "." .. (t.oy - OY) .. ":"; end
    o = o:next();
  end
  s = s .. " t=";
  for i = 1, #HC, 2 do
    local x, y = HC[i], HC[i + 1];
    if (nh.getmap(x + OX, y + OY).has_trap) then
      s = s .. x .. "." .. y .. nh.gettrap(x + OX, y + OY).ttyp_name:sub(1, 1) .. ":";
    end
  end
  if (collectgarbage ~= nil) then collectgarbage(); end
  return s;
end
'''

FAST = r'''
local Q = {
%(queries)s
};
local out = {};
for _, q in ipairs(Q) do
  local a = build(q[2], q[3], q[5], q[6]);
  if (a == 0) then out[#out + 1] = "R" .. q[1] .. " NOBUILD";
  else
    local d0 = u.dlevel;
    local tr = {};
    local keys = q[4];
    for i = 1, #keys do
      nh.pushkey(string.sub(keys, i, i)); nh.doturn(true);
      if (u.dlevel ~= d0) then break; end
      if (#keys > 1) then tr[#tr + 1] = (u.ux - OX) .. "." .. (u.uy - OY); end
    end
    out[#out + 1] = "R" .. q[1] .. " a" .. a .. " " .. snap(d0);
    if (u.dlevel ~= d0) then out[#out + 1] = "DEEP"; break; end   -- fell: stop, the driver restarts the game
    for k = 0, (#tr - 1) // 10 do       -- 10 cells per line (tty menu lines are width-limited)
      out[#out + 1] = "T" .. q[1] .. "_" .. k .. " " .. table.concat(tr, ",", 10 * k + 1, math.min(#tr, 10 * k + 10)) .. ",";
    end
  end
  if (u.dlevel > 5) then out[#out + 1] = "DEEP"; break; end
end
nh.text(table.concat(out, "\n") .. "\nBATCH END\n");
'''

SCREEN_BUILD = r'''
local a = build(%(hx)d, %(hy)d, {%(bs)s}, {%(hs)s});
nh.pline("BUILT a" .. a .. " dl" .. u.dlevel .. " BATCH END");
'''

SCREEN_DUMP = r'''
nh.text("S " .. snap(%(d0)d) .. "\nBATCH END\n");
'''

RES = re.compile(r'R(\d+) (NOBUILD|a\d+ (?:FELL:\d+|-?\d+\.-?\d+ b=[\d.:-]* t=[\w.:]*))')
TRC = re.compile(r'T(\d+)_(\d+) ([\d.,]+)')


def window_map(w):
    """MAP text for the window + sealed pocket (branch stair) and sealed sentinel pit to its right."""
    Wm = w.W + 5
    Hm = max(w.H, 6)
    g = [[' '] * Wm for _ in range(Hm)]
    for y, r in enumerate(w.rows):
        for x, ch in enumerate(r):
            if ch not in '# ':
                g[y][x] = '.'
    px, py = w.W + 2, 1
    sx, sy = w.W + 2, 4
    g[py][px] = '.'
    g[sy][sx] = '.'
    return '\n'.join(''.join(r) for r in g), (px, py), (sx, sy)


def header(w, hide):
    m, (px, py), (sx, sy) = window_map(w)
    return BUILD % dict(map=m, W=w.W, H=w.H, PX=px, PY=py, SX=sx, SY=sy, cells=lua_list(w.cells), hc=lua_list(w.bset(w.h0)),
                        hide='nh.parse_config("MSGTYPE=hide \\".*\\"");' if hide else '')


def lua_list(cells):
    return ','.join(f'{x},{y}' for x, y in cells)


def fast_src(w, queries):
    """queries: list of (qid, (hx,hy), [boulder cells], [hole cells], keys)"""
    ql = ',\n'.join(f'{{{qid},{h[0]},{h[1]},"{keys}",{{{lua_list(bs)}}},{{{lua_list(hs)}}}}}'
                    for qid, h, bs, hs, keys in queries)
    return header(w, True) + FAST % dict(queries=ql)


def parse_snap(s):
    """'a1 3.2 b=4.2:5.6: t=1.2h:' -> dict"""
    if s == 'NOBUILD':
        return {'kind': 'nobuild'}
    parts = s.split(' ')
    a = int(parts[0][1:])
    if parts[1].startswith('FELL'):
        return {'kind': 'fell', 'dl': int(parts[1][5:]), 'att': a}
    hx, hy = map(int, parts[1].split('.'))
    bs = sorted(tuple(map(int, c.split('.'))) for c in parts[2][2:].split(':') if c)
    traps = {}
    for c in parts[3][2:].split(':'):
        if c:
            xy, t = c[:-1], c[-1]
            traps[tuple(map(int, xy.split('.')))] = t
    return {'kind': 'ok', 'h': (hx, hy), 'b': bs, 'traps': traps, 'att': a}


def run_fast(game, w, queries, batch=300, log=None, timeout=900):
    """returns {qid: result dict (+ 'trace': [cells])}; restarts the game after a fall."""
    out = {}
    i = 0
    while i < len(queries):
        chunk = queries[i:i + batch]
        try:
            txt, dt = game.run(fast_src(w, chunk), timeout=timeout)
        except R_game.LuaError as e:
            if log:
                log(f'LUA ERROR batch@{i}: {e}')
            raise
        got = {}
        for m in RES.finditer(txt):
            got[int(m.group(1))] = parse_snap(m.group(2))
        tr = {}
        for m in TRC.finditer(txt):
            tr.setdefault(int(m.group(1)), {})[int(m.group(2))] = m.group(3)
        for qid, parts in tr.items():
            if qid in got:
                s = ''.join(parts[k] for k in sorted(parts))
                got[qid]['trace'] = [tuple(map(int, c.split('.'))) for c in s.split(',') if c]
        done = [q for q in chunk if q[0] in got]
        for q in done:
            out[q[0]] = got[q[0]]
        fell = any(r['kind'] == 'fell' for r in got.values()) or 'DEEP' in txt
        if len(done) < len(chunk):
            # batch stopped early (DEEP) or lost lines: restart and continue with the rest
            missing = [q for q in chunk if q[0] not in got]
            if log:
                log(f'batch@{i}: {len(missing)} queries missing, restarting game')
            game.start()
            queries = queries[:i] + done + missing + queries[i + len(chunk):]
            i += len(done)
            continue
        if fell:
            game.start()
        i += len(chunk)
    return out


def run_screen(game, w, h, bs, hs, keys, settle=0.08):
    """build, TYPE keys one by one into the tty; returns dict(msgs=[...per key], screen_hero=[...per key], truth)."""
    src = header(w, False) + SCREEN_BUILD % dict(hx=h[0], hy=h[1], bs=lua_list(bs), hs=lua_list(hs))
    game.run(src)
    game.p.send('\x12')            # ^R redraw
    game.quiet(0.1)
    scr0 = screen_hero(game)
    msgs, heroes = [], []
    for k in keys:
        msgs.append(game.keys(k, settle))
        game.p.send('\x12')
        game.quiet(0.08)
        heroes.append(screen_hero(game))
    txt, _ = game.run(header(w, False) + SCREEN_DUMP % dict(d0=1))
    m = re.search(r'S (FELL:\d+|-?\d+\.-?\d+ b=[\d.:-]* t=[\w.:]*)', txt)
    truth = parse_snap('a0 ' + m.group(1)) if m else {'kind': 'nodump'}
    return dict(msgs=msgs, heroes=heroes, hero0=scr0, truth=truth)


def screen_hero(game):
    """(x, y) of '@' on the map part of the screen, in window coordinates (tty: col = x - 1, row = y + 1)."""
    rows = game.screen()
    found = []
    for r in range(1, 22):
        c = rows[r].find('@')
        if c >= 0:
            found.append((c + 1 - 2, r - 1 - 2))
    return found[0] if len(found) == 1 else (found or None)
