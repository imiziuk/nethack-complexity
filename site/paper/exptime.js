/* exptime.js -- interactive parts of exptime.html (work in progress page).
   Core = a JavaScript port of tools/exptime/A_core.py + the targets of A_check.py (gadget lab),
   plus a tiny solver for the formula game G6 (Play 2) and the teleport-coin demo (Play 1).
   The Core part also runs under node (module.exports) so it can be compared with A_check.py. */
(function () {
"use strict";

/* =====================================================================
   Core: exact local model of boulder gadgets (mirror of A_core.py)
   ===================================================================== */
var D4 = [[1, 0], [-1, 0], [0, 1], [0, -1]];
var DG = [[1, 1], [1, -1], [-1, 1], [-1, -1]];
var ONE = BigInt(1), ZERO = BigInt(0);
function bit(i) { return ONE << BigInt(i); }
function has(B, i) { return ((B >> BigInt(i)) & ONE) === ONE; }
function popcount(B) { var n = 0; while (B) { if (B & ONE) { n++; } B >>= ONE; } return n; }

function LeakError(a, b) { this.leak = true; this.from = a; this.to = b; }
function TooBig(what) { this.tooBig = true; this.what = what; }

/* rows: array of strings. '#' or ' ' wall/stone, '.' floor, '0' boulder, 'A'-'Z' ports, 'a'-'z' named floor. */
function Board(rows) {
  rows = rows.map(function (r) { return r.replace(/\n+$/, ""); });
  this.rows = rows;
  this.H = rows.length;
  this.W = Math.max.apply(null, rows.map(function (r) { return r.length; }));
  var W = this.W, g = rows.map(function (r) { while (r.length < W) { r += " "; } return r; });
  this.grid = g;
  this.cells = []; this.idx = {}; this.ports = {}; this.portname = {};
  var b0 = ZERO;
  for (var y = 0; y < this.H; y++) {
    for (var x = 0; x < W; x++) {
      var ch = g[y][x];
      if (ch === "#" || ch === " ") { continue; }
      var i = this.cells.length;
      this.idx[x + "," + y] = i;
      this.cells.push([x, y]);
      if (ch === "0") { b0 |= bit(i); }
      else if (ch >= "A" && ch <= "Z") { this.ports[ch] = i; }
    }
  }
  this.b0 = b0;
  var pm = ZERO, self = this;
  Object.keys(this.ports).forEach(function (n) { pm |= bit(self.ports[n]); self.portname[self.ports[n]] = n; });
  this.portmask = pm;
  var n = this.cells.length;
  this.orth = []; this.diag = [];
  for (var k = 0; k < n; k++) {
    var cx = this.cells[k][0], cy = this.cells[k][1], o = [], d = [];
    D4.forEach(function (v) {
      var t = self.idx[(cx + v[0]) + "," + (cy + v[1])];
      if (t === undefined) { return; }
      var b = self.idx[(cx + 2 * v[0]) + "," + (cy + 2 * v[1])];
      o.push([t, b === undefined ? -1 : b]);
    });
    DG.forEach(function (v) {
      var t = self.idx[(cx + v[0]) + "," + (cy + v[1])];
      if (t === undefined) { return; }
      var cm = ZERO, c1 = self.idx[(cx + v[0]) + "," + cy], c2 = self.idx[cx + "," + (cy + v[1])];
      if (c1 !== undefined) { cm |= bit(c1); }
      if (c2 !== undefined) { cm |= bit(c2); }
      if (cm) { d.push([t, cm]); }
    });
    this.orth.push(o); this.diag.push(d);
  }
  this.budget = Infinity;
}
/* every legal hero move from h with boulders B: [[h', B'], ...]; throws LeakError like A_core */
Board.prototype.moves = function (h, B) {
  var out = [], i, t, b;
  for (i = 0; i < this.orth[h].length; i++) {
    t = this.orth[h][i][0]; b = this.orth[h][i][1];
    if (has(B, t)) {
      if (b < 0 || has(B, b)) { continue; }
      if (has(this.portmask, b)) { throw new LeakError(this.cells[t], this.cells[b]); }
      out.push([t, (B & ~bit(t)) | bit(b)]);
    } else { out.push([t, B]); }
  }
  for (i = 0; i < this.diag[h].length; i++) {
    t = this.diag[h][i][0];
    if (has(B, t)) { continue; }
    if (this.diag[h][i][1] & ~B) { out.push([t, B]); }
  }
  return out;
};
/* T(B, p): list of [q, B'] (unique) */
Board.prototype.traversals = function (B, p) {
  var start = this.ports[p], seen = new Set([start + ":" + B]), dq = [[start, B]], head = 0, out = new Map();
  while (head < dq.length) {
    var s = dq[head++], ms = this.moves(s[0], s[1]);
    for (var i = 0; i < ms.length; i++) {
      var k = ms[i][0] + ":" + ms[i][1];
      if (seen.has(k)) { continue; }
      seen.add(k);
      if (--this.budget < 0) { throw new TooBig("hero positions"); }
      if (has(this.portmask, ms[i][0])) {
        var q = this.portname[ms[i][0]];
        out.set(q + "|" + ms[i][1], [q, ms[i][1]]);
      } else { dq.push(ms[i]); }
    }
  }
  return Array.from(out.values());
};
/* shortest hero walk from port p (state B) to port q ending with boulders B2 (or any if B2 null). [[h,B],...] or null */
Board.prototype.walk = function (B, p, q, B2) {
  var start = [this.ports[p], B], prev = new Map(), k0 = start[0] + ":" + B;
  prev.set(k0, null);
  var dq = [start], head = 0;
  while (head < dq.length) {
    var s = dq[head++], ms;
    try { ms = this.moves(s[0], s[1]); } catch (e) { ms = []; }
    for (var i = 0; i < ms.length; i++) {
      var k = ms[i][0] + ":" + ms[i][1];
      if (prev.has(k)) { continue; }
      prev.set(k, s);
      if (has(this.portmask, ms[i][0])) {
        if (this.portname[ms[i][0]] === q && (B2 === null || B2 === undefined || ms[i][1] === B2)) {
          var path = [ms[i]], c = s;
          while (c) { path.push(c); c = prev.get(c[0] + ":" + c[1]); }
          return path.reverse();
        }
      } else { dq.push(ms[i]); }
    }
  }
  return null;
};
Board.prototype.show = function (B, hero) {
  var g = this.grid.map(function (r) { return r.split(""); }), self = this;
  this.cells.forEach(function (c, i) {
    if (g[c[1]][c[0]] === "0") { g[c[1]][c[0]] = "."; }
    if (has(B, i)) { g[c[1]][c[0]] = "0"; }
  });
  if (hero !== undefined && hero !== null) { g[this.cells[hero][1]][this.cells[hero][0]] = "@"; }
  return g.map(function (r) { return r.join(""); });
};

function System(ports, init, T, states) { this.ports = ports; this.init = init; this.T = T; this.states = states; }
System.prototype.tr = function (s, p) { return this.T.get(s + "|" + p) || []; };

/* all local states reachable by traversals; states are keys B.toString() */
function explore(board, maxStates) {
  maxStates = maxStates || 200000;
  var ports = Object.keys(board.ports).sort(), T = new Map(), init = board.b0;
  var seen = new Set([String(init)]), dq = [init], head = 0;
  while (head < dq.length) {
    var B = dq[head++];
    for (var i = 0; i < ports.length; i++) {
      var tr = board.traversals(B, ports[i]);
      T.set(String(B) + "|" + ports[i], tr.map(function (x) { return [x[0], String(x[1])]; }));
      for (var j = 0; j < tr.length; j++) {
        var k = String(tr[j][1]);
        if (!seen.has(k)) {
          if (seen.size >= maxStates) { throw new TooBig("local states"); }
          seen.add(k); dq.push(tr[j][1]);
        }
      }
    }
  }
  return new System(ports, String(init), T, Array.from(seen));
}
function abstract(ports, init, trans) {
  var T = new Map();
  Object.keys(trans).forEach(function (s) {
    ports.forEach(function (p) { T.set(s + "|" + p, (trans[s][p] || []).slice()); });
  });
  return new System(ports, init, T, Object.keys(trans).sort());
}
var SEP = "\u0001";
function simSound(C, A) {
  var R = new Set();
  C.states.forEach(function (c) { A.states.forEach(function (a) { R.add(c + SEP + a); }); });
  var changed = true;
  while (changed) {
    changed = false;
    Array.from(R).forEach(function (key) {
      var parts = key.split(SEP), c = parts[0], a = parts[1], ok = true;
      for (var i = 0; i < C.ports.length && ok; i++) {
        var p = C.ports[i], ct = C.tr(c, p);
        for (var j = 0; j < ct.length; j++) {
          var q = ct[j][0], c2 = ct[j][1];
          if (q === p && R.has(c2 + SEP + a)) { continue; }
          if (A.tr(a, p).some(function (x) { return x[0] === q && R.has(c2 + SEP + x[1]); })) { continue; }
          ok = false; break;
        }
      }
      if (!ok) { R.delete(key); changed = true; }
    });
  }
  return R;
}
function simComplete(A, C) {
  var R = new Set();
  A.states.forEach(function (a) { C.states.forEach(function (c) { R.add(a + SEP + c); }); });
  var changed = true;
  while (changed) {
    changed = false;
    Array.from(R).forEach(function (key) {
      var parts = key.split(SEP), a = parts[0], c = parts[1], ok = true;
      for (var i = 0; i < A.ports.length && ok; i++) {
        var p = A.ports[i], at = A.tr(a, p);
        for (var j = 0; j < at.length; j++) {
          var q = at[j][0], a2 = at[j][1];
          if (!C.tr(c, p).some(function (x) { return x[0] === q && R.has(a2 + SEP + x[1]); })) { ok = false; break; }
        }
      }
      if (!ok) { R.delete(key); changed = true; }
    });
  }
  return R;
}
function check(C, A) {
  var Rs = simSound(C, A), Rc = simComplete(A, C);
  return { sound: Rs.has(C.init + SEP + A.init), complete: Rc.has(A.init + SEP + C.init), Rs: Rs, Rc: Rc };
}
function relationTable(C) {
  var out = {};
  C.states.forEach(function (c) {
    var s = new Set();
    C.ports.forEach(function (p) { C.tr(c, p).forEach(function (x) { if (x[0] !== p) { s.add(p + "->" + x[0]); } }); });
    out[c] = Array.from(s).sort();
  });
  return out;
}
function checkLegal(C, c, checks) {
  var frontier = new Set([c]);
  for (var i = 0; i < checks.length; i++) {
    var p = checks[i][0], q = checks[i][1], nf = new Set();
    frontier.forEach(function (c1) { C.tr(c1, p).forEach(function (x) { if (x[0] === q) { nf.add(x[1]); } }); });
    frontier = nf;
    if (!frontier.size) { return false; }
  }
  return true;
}
function postselect(C, checks, ports) {
  var clean = new Set(C.states.filter(function (c) { return checkLegal(C, c, checks); }));
  var absorbing = true;
  C.states.forEach(function (c) {
    if (clean.has(c)) { return; }
    C.ports.forEach(function (p) { C.tr(c, p).forEach(function (x) { if (clean.has(x[1])) { absorbing = false; } }); });
  });
  ports = ports || C.ports;
  var T = new Map();
  clean.forEach(function (c) {
    ports.forEach(function (p) {
      T.set(c + "|" + p, C.tr(c, p).filter(function (x) { return clean.has(x[1]) && ports.indexOf(x[0]) >= 0; }));
    });
  });
  return { clean: clean, absorbing: absorbing, sys: new System(ports.slice().sort(), C.init, T, Array.from(clean).sort()) };
}
/* close a single gadget's ports into a network (A_core.wire with one gadget) */
function wire(sys, joins, ext) {
  var pm = {};
  joins.forEach(function (grp, k) { grp.forEach(function (p) { pm[p] = "j" + k; }); });
  ext.forEach(function (p) { pm[p] = "e" + p; });
  var at = {};
  Object.keys(pm).forEach(function (p) { (at[pm[p]] = at[pm[p]] || []).push(p); });
  function isExt(node) { return node.charAt(0) === "e"; }
  function trav(S, p) {
    var start = "e" + p, seen = new Set([start + "|" + S]), dq = [[start, S]], head = 0, out = new Map();
    while (head < dq.length) {
      var st = dq[head++], node = st[0], St = st[1];
      (at[node] || []).forEach(function (port) {
        sys.tr(St, port).forEach(function (x) {
          var nn = pm[x[0]];
          if (nn === undefined) { return; }
          var k = nn + "|" + x[1];
          if (seen.has(k)) { return; }
          seen.add(k);
          if (isExt(nn)) { out.set(nn.slice(1) + "|" + x[1], [nn.slice(1), x[1]]); } else { dq.push([nn, x[1]]); }
        });
      });
    }
    return Array.from(out.values());
  }
  var ports = ext.slice().sort(), T = new Map(), seen = new Set([sys.init]), dq = [sys.init], head = 0;
  while (head < dq.length) {
    var S = dq[head++];
    ports.forEach(function (p) {
      var tr = trav(S, p);
      T.set(S + "|" + p, tr);
      tr.forEach(function (x) { if (!seen.has(x[1])) { seen.add(x[1]); dq.push(x[1]); } });
    });
  }
  return new System(ports, sys.init, T, Array.from(seen).sort());
}

/* intended automata (A_check.py) */
var TARGETS = {
  diode: { name: "diode", ports: ["A", "B"], desc: "one-way corridor: A to B, never B to A",
    mk: function () { return abstract(["A", "B"], "d", { d: { A: [["B", "d"]] } }); } },
  scd: { name: "self-closing door (button)", ports: ["I", "J", "O"], desc: "visit O to open; tunnel I to J only when open, and it closes behind you",
    mk: function () { return abstract(["I", "J", "O"], "c", { c: { O: [["O", "o"]] }, o: { O: [["O", "o"]], I: [["J", "c"]] } }); } },
  scd4: { name: "self-closing door (tunnel)", ports: ["I", "J", "O", "P"], desc: "tunnel O to P opens it; tunnel I to J only when open, closes",
    mk: function () { return abstract(["I", "J", "O", "P"], "c", { c: { O: [["P", "o"]] }, o: { O: [["P", "o"]], I: [["J", "c"]] } }); } },
  xover: { name: "directed crossover", ports: ["A", "B", "C", "D"], desc: "A to B and C to D, any number of times, nothing else",
    mk: function () { return abstract(["A", "B", "C", "D"], "x", { x: { A: [["B", "x"]], C: [["D", "x"]] } }); } },
  uxover: { name: "undirected crossover", ports: ["A", "B", "C", "D"], desc: "A and B connected, C and D connected, nothing else",
    mk: function () { return abstract(["A", "B", "C", "D"], "x", { x: { A: [["B", "x"]], B: [["A", "x"]], C: [["D", "x"]], D: [["C", "x"]] } }); } },
  gd: { name: "single-use one-way door (G_D)", ports: ["E", "Q"], desc: "closed: E to Q opens it for good; open: free both ways",
    mk: function () { return abstract(["E", "Q"], "c", { c: { E: [["Q", "o"], ["E", "o"]] }, o: { E: [["Q", "o"]], Q: [["E", "o"]] } }); } },
  toggle1: { name: "1-toggle", ports: ["A", "B"], desc: "A to B once, then B to A once, alternating",
    mk: function () { return abstract(["A", "B"], "r", { r: { A: [["B", "l"]] }, l: { B: [["A", "r"]] } }); } }
};

/* full report for a pure gadget (= A_check.report) */
function reportPure(rows, target, opts) {
  opts = opts || {};
  var b = new Board(rows), res = { board: b, target: target };
  b.budget = opts.budget || 3000000;
  var C;
  try { C = explore(b, opts.maxStates || 5000); }
  catch (e) { if (e.leak || e.tooBig) { res.error = e; return res; } throw e; }
  var A = TARGETS[target].mk(), ck = check(C, A), rel = relationTable(C);
  var kinds = new Map();
  C.states.forEach(function (st) { var k = rel[st].join(", "); if (!kinds.has(k)) { kinds.set(k, []); } kinds.get(k).push(st); });
  var groups = Array.from(kinds.entries()).map(function (kv) {
    var abs = new Set();
    kv[1].forEach(function (st) { A.states.forEach(function (a) { if (ck.Rs.has(st + SEP + a)) { abs.add(a); } }); });
    return { relation: kv[0] || "(none)", states: kv[1], simulatedBy: Array.from(abs).sort() };
  }).sort(function (x, y) { return y.states.length - x.states.length; });
  res.C = C; res.rel = rel; res.groups = groups; res.sound = ck.sound; res.complete = ck.complete;
  res.portsMatch = sameSet(C.ports, A.ports);
  return res;
}
function reportCheckable(rows, checks, joins, ext, target, opts) {
  opts = opts || {};
  var b = new Board(rows), res = { board: b, target: target, checkable: true };
  b.budget = opts.budget || 3000000;
  var C;
  try { C = explore(b, opts.maxStates || 5000); }
  catch (e) { if (e.leak || e.tooBig) { res.error = e; return res; } throw e; }
  var ps = postselect(C, checks), rel = relationTable(C);
  var A = TARGETS[target].mk();
  var N = wire(ps.sys, joins, ext), ck = check(N, A);
  var Nraw = wire(C, joins, ext), ckr = check(Nraw, A);
  res.C = C; res.rel = rel; res.clean = ps.clean; res.absorbing = ps.absorbing; res.initClean = ps.clean.has(C.init);
  res.sound = ck.sound; res.complete = ck.complete; res.rawSound = ckr.sound; res.rawComplete = ckr.complete;
  res.ok = ps.absorbing && ck.sound && ck.complete && res.initClean;
  return res;
}
function sameSet(a, b) { return a.length === b.length && a.slice().sort().join() === b.slice().sort().join(); }

/* shortest sequence of traversals (from any port) reaching a state where pair p->q is possible; for counterexamples */
function findPair(board, p, q, maxStates) {
  var C = explore(board, maxStates || 5000), init = C.init, prev = new Map([[init, null]]), dq = [init], head = 0, hit = null;
  function bad(s) { return C.tr(s, p).some(function (x) { return x[0] === q; }); }
  if (bad(init)) { hit = init; }
  while (!hit && head < dq.length) {
    var s = dq[head++];
    for (var i = 0; i < C.ports.length && !hit; i++) {
      var tr = C.tr(s, C.ports[i]);
      for (var j = 0; j < tr.length; j++) {
        if (prev.has(tr[j][1])) { continue; }
        prev.set(tr[j][1], [s, C.ports[i], tr[j][0]]);
        if (bad(tr[j][1])) { hit = tr[j][1]; break; }
        dq.push(tr[j][1]);
      }
    }
  }
  if (!hit) { return null; }
  var legs = [], c = hit;
  while (prev.get(c)) { var pv = prev.get(c); legs.push([pv[1], pv[2], pv[0], c]); c = pv[0]; }
  legs.reverse();
  legs.push([p, q, hit, null]);
  return legs; /* [from, to, stateBefore, stateAfter|null] */
}

var Core = { Board: Board, explore: explore, abstract: abstract, check: check, simSound: simSound, simComplete: simComplete,
  relationTable: relationTable, postselect: postselect, wire: wire, TARGETS: TARGETS, reportPure: reportPure,
  reportCheckable: reportCheckable, findPair: findPair, has: has, bit: bit, popcount: popcount };

/* =====================================================================
   G6 (Play 2): exact solver by attractor
   ===================================================================== */
/* formula: {nx, ny, clauses: [[lit,...]]}, lit = {v:'x'|'y', i, neg} ; assignment bits: x_i -> bit i, y_j -> bit nx+j */
function g6Eval(f, a) {
  return f.clauses.every(function (cl) {
    return cl.some(function (l) { var v = (a >> (l.v === "x" ? l.i : f.nx + l.i)) & 1; return l.neg ? !v : !!v; });
  });
}
function g6Solve(f) {
  var n = f.nx + f.ny, N = 1 << n, rank = [new Int32Array(N).fill(-1), new Int32Array(N).fill(-1)]; /* [turn][a] */
  var r, changed;
  for (var a = 0; a < N; a++) { if (g6Eval(f, a)) { rank[0][a] = 0; rank[1][a] = 0; } }
  for (r = 1, changed = true; changed; r++) {
    changed = false;
    var add = [];
    for (a = 0; a < N; a++) {
      if (rank[0][a] < 0) { /* I to move: some move (flip x_i or pass) leads to II-turn position won */
        var ok = rank[1][a] >= 0 && rank[1][a] < r;
        for (var i = 0; i < f.nx && !ok; i++) { var b = a ^ (1 << i); if (rank[1][b] >= 0 && rank[1][b] < r) { ok = true; } }
        if (ok) { add.push([0, a]); }
      }
      if (rank[1][a] < 0) { /* II to move: every move leads to a won I-turn position */
        var all = rank[0][a] >= 0 && rank[0][a] < r;
        for (var j = 0; j < f.ny && all; j++) { var c = a ^ (1 << (f.nx + j)); if (!(rank[0][c] >= 0 && rank[0][c] < r)) { all = false; } }
        if (all) { add.push([1, a]); }
      }
    }
    add.forEach(function (t) { rank[t[0]][t[1]] = r; });
    if (add.length) { changed = true; }
  }
  return rank;
}
/* opponent's move: -1 = pass, j = flip y_j */
function g6Opp(f, rank, a) {
  var opts = [-1];
  for (var j = 0; j < f.ny; j++) { opts.push(j); }
  function nxt(m) { return m < 0 ? a : a ^ (1 << (f.nx + m)); }
  var losing = opts.filter(function (m) { return rank[0][nxt(m)] < 0; });
  if (losing.length) { /* keep I outside his winning region; prefer moves that also keep F false */
    var safe = losing.filter(function (m) { return !g6Eval(f, nxt(m)); });
    var pool = safe.length ? safe : losing;
    return pool[Math.floor(Math.random() * pool.length)];
  }
  var best = -1, bestR = -1;
  opts.forEach(function (m) { var rr = rank[0][nxt(m)]; if (rr > bestR) { bestR = rr; best = m; } });
  return best;
}
Core.g6Eval = g6Eval; Core.g6Solve = g6Solve; Core.g6Opp = g6Opp;

if (typeof module !== "undefined" && module.exports) { module.exports = Core; }
if (typeof document === "undefined") { return; }

/* =====================================================================
   Page: depth switch, view mode, tiles
   ===================================================================== */
var root = document.documentElement;
function $(s, el) { return (el || document).querySelector(s); }
function $$(s, el) { return Array.prototype.slice.call((el || document).querySelectorAll(s)); }
function h(tag, attrs, kids) {
  var e = document.createElement(tag);
  if (attrs) { Object.keys(attrs).forEach(function (k) {
    if (k === "text") { e.textContent = attrs[k]; } else if (k === "html") { e.innerHTML = attrs[k]; }
    else if (k.slice(0, 2) === "on") { e.addEventListener(k.slice(2), attrs[k]); } else { e.setAttribute(k, attrs[k]); }
  }); }
  (kids || []).forEach(function (c) { if (c !== null && c !== undefined) { e.appendChild(typeof c === "string" ? document.createTextNode(c) : c); } });
  return e;
}
function store(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* storage unavailable */ } }

var secs = $$("section.lv");
function gdepth() { var d = root.getAttribute("data-depth"); return d === "0" || d === "1" || d === "3" ? d : "2"; }
function eff(sec) { return sec.getAttribute("data-depth") || gdepth(); }
var proofBtn = $("#proofs-all");
function paintAll() {
  var d = gdepth();
  secs.forEach(function (sec) {
    var e = eff(sec);
    $$(".seg.local button", sec).forEach(function (b) { b.setAttribute("aria-pressed", String(b.getAttribute("data-d") === e)); });
  });
  $$("#g-depth button").forEach(function (b) { b.setAttribute("aria-pressed", String(b.getAttribute("data-d") === d)); });
  if (proofBtn) { proofBtn.hidden = !secs.some(function (s) { return eff(s) === "3"; }); }
}
function setGlobal(d, save) {
  root.setAttribute("data-depth", d);
  secs.forEach(function (s) { s.removeAttribute("data-depth"); });
  paintAll();
  if (save) { store("exptime-depth", d); }
  redrawAll();
}
$$("#g-depth button").forEach(function (b) { b.addEventListener("click", function () { setGlobal(b.getAttribute("data-d"), true); }); });
$$("[data-goto]").forEach(function (b) { b.addEventListener("click", function () { setGlobal(b.getAttribute("data-goto"), true); window.scrollTo(0, 0); }); });
secs.forEach(function (s) {
  $$(".seg.local button", s).forEach(function (b) {
    b.addEventListener("click", function () { s.setAttribute("data-depth", b.getAttribute("data-d")); paintAll(); });
  });
});
if (proofBtn) {
  proofBtn.addEventListener("click", function () {
    var ds = $$("details.proof"), anyClosed = ds.some(function (d) { return !d.open; });
    ds.forEach(function (d) { d.open = anyClosed; });
    proofBtn.textContent = anyClosed ? "Close all proofs" : "Open all proofs";
  });
}
/* a link into hidden content raises the depth */
document.addEventListener("click", function (e) {
  var a = e.target.closest && e.target.closest("a[href^='#']");
  if (!a) { return; }
  var t = document.getElementById(a.getAttribute("href").slice(1));
  if (!t || t.offsetParent !== null) { return; }
  var need = 1, n = t;
  while (n && n !== document.body) { var dm = n.getAttribute && n.getAttribute("data-dm"); if (dm && +dm > need) { need = +dm; } n = n.parentNode; }
  if (gdepth() === "0" || +gdepth() < need) { setGlobal(String(Math.max(need, 1)), false); }
  if (t.tagName === "DETAILS") { t.open = true; }
  setTimeout(function () { t.scrollIntoView(); }, 0);
});
var bar = $("#bar");
function barH() { if (bar) { root.style.setProperty("--barh", bar.offsetHeight + "px"); } }
window.addEventListener("resize", barH); barH();

/* view mode */
function setView(v, save) {
  root.classList.toggle("tilemode", v === "tiles");
  $$("#view-mode button").forEach(function (b) { b.setAttribute("aria-pressed", String(b.getAttribute("data-v") === v)); });
  if (save) { store("exptime-view", v); }
  redrawAll();
}
$$("#view-mode button").forEach(function (b) { b.addEventListener("click", function () { setView(b.getAttribute("data-v"), true); }); });

var TILES = null, views = [];
function redrawAll() { views.forEach(function (f) { f(); }); }
function loadTiles() {
  if (!window.fetch) { return; }
  Promise.all([fetch("engine/tiles.json").then(function (r) { return r.json(); }),
    fetch("engine/tiles_exp.json").then(function (r) { return r.json(); })]).then(function (x) {
    TILES = Object.assign({}, x[0], x[1]);
    redrawAll();
  }).catch(function () { TILES = null; });
}

/* =====================================================================
   Grid renderer (text or tiles). rows: array of strings with chars
   '#',' ' wall · '.' floor · '0' boulder · '@' hero · '^' teleport trap · 'A'-'Z' port · 'a'-'z' named floor
   marks: {"x,y": className}
   ===================================================================== */
function isWall(ch) { return ch === "#" || ch === " " || ch === undefined; }
function wallTile(g, x, y) {
  function W(xx, yy) { return yy >= 0 && yy < g.length && xx >= 0 && xx < g[yy].length && isWall(g[yy][xx]); }
  function F(xx, yy) { return yy >= 0 && yy < g.length && xx >= 0 && xx < g[yy].length && !isWall(g[yy][xx]); }
  function vis(xx, yy) {
    if (!W(xx, yy)) { return false; }
    for (var dy = -1; dy <= 1; dy++) { for (var dx = -1; dx <= 1; dx++) { if (F(xx + dx, yy + dy)) { return true; } } }
    return false;
  }
  if (!vis(x, y)) { return "stone"; }
  var L = vis(x - 1, y), R = vis(x + 1, y), U = vis(x, y - 1), D = vis(x, y + 1);
  var k = (L ? "L" : "") + (R ? "R" : "") + (U ? "U" : "") + (D ? "D" : "");
  var map = { "": "h", L: "h", R: "h", LR: "h", U: "v", D: "v", UD: "v", RD: "tl", LD: "tr", RU: "bl", LU: "br",
    LRD: "td", LRU: "tu", LUD: "tlw", RUD: "trw", LRUD: "cross" };
  return map[k] || "h";
}
function drawGrid(host, rows, opts) {
  opts = opts || {};
  var tiles = root.classList.contains("tilemode") && TILES;
  var H = rows.length, W = Math.max.apply(null, rows.map(function (r) { return r.length; }));
  var g = rows.map(function (r) { while (r.length < W) { r += " "; } return r; });
  host.innerHTML = "";
  host.className = "gx" + (tiles ? " tl" : "") + (opts.cls ? " " + opts.cls : "");
  host.style.setProperty("--cols", W);
  host.setAttribute("role", "img");
  if (opts.label) { host.setAttribute("aria-label", opts.label); }
  for (var y = 0; y < H; y++) {
    for (var x = 0; x < W; x++) {
      var ch = g[y][x], c = document.createElement("span"), cls = "c";
      c.setAttribute("data-x", x); c.setAttribute("data-y", y);
      var wall = isWall(ch);
      if (wall) { cls += " w"; } else { cls += " f"; }
      if (opts.marks && opts.marks[x + "," + y]) { cls += " " + opts.marks[x + "," + y]; }
      if (tiles) {
        var base = wall ? TILES[wallTile(g, x, y)] : TILES.floor, top = null;
        if (ch === "0") { top = TILES.boulder; } else if (ch === "@") { top = TILES.hero; } else if (ch === "^") { top = TILES.tele; }
        else if (ch === "*") { top = TILES.hole; }
        else if (ch === "G" && !opts.noGoal) { top = TILES.goal; }
        c.style.backgroundImage = (top ? "url(" + top + "), " : "") + "url(" + base + ")";
        if (ch >= "A" && ch <= "Z" && (ch !== "G" || opts.noGoal)) { c.appendChild(h("b", { text: ch })); cls += " port"; }
        if (opts.over && opts.over[x + "," + y]) { c.appendChild(h("b", { text: opts.over[x + "," + y] })); }
      } else {
        var t = wall ? (ch === "#" ? "#" : " ") : ch;
        if (ch === "*") { t = "^"; cls += " trap hole"; }
        if (ch === "0") { cls += " bd"; } else if (ch === "@") { cls += " hero"; } else if (ch === "^") { cls += " trap"; }
        else if (ch >= "A" && ch <= "Z") { cls += " port"; }
        if (opts.over && opts.over[x + "," + y] && !wall && ch === ".") { t = opts.over[x + "," + y]; cls += " ov"; }
        c.textContent = t;
      }
      c.className = cls;
      host.appendChild(c);
    }
  }
}

/* =====================================================================
   PLAY 1: be the dungeon (teleport coin)
   ===================================================================== */
function play1() {
  var host = $("#p1"); if (!host) { return; }
  var MAP = ["#############",
             "#.#.#.#.....#",
             "#.#.#.#.....#",
             "#.#.#.#.....#",
             "#.#.#.#.....#",
             "#############"];
  var A = [1, 1], T = [3, 1], B = [5, 1], START = [3, 4];
  var st = { hero: START.slice(), boots: true, zone: true, mode: "you", pending: false, onT: false, cnt: { A: 0, B: 0, esc: 0, out: 0 }, busy: false };
  var grid = $("#p1-grid"), log = $("#p1-log"), ctrl = $("#p1-nature"), note = $("#p1-note"), cnt = $("#p1-cnt");
  function rows() {
    var g = MAP.map(function (r) { return r.split(""); });
    g[T[1]][T[0]] = "^"; g[A[1]][A[0]] = "A"; g[B[1]][B[0]] = "B";
    if (!(st.onT)) { g[st.hero[1]][st.hero[0]] = "@"; } else { g[T[1]][T[0]] = "@"; }
    return g.map(function (r) { return r.join(""); });
  }
  function marks() {
    var m = {};
    if (st.zone) { for (var x = 1; x <= 5; x++) { m[x + ",1"] = "zone"; } }
    if (st.last) { m[st.last[0] + "," + st.last[1]] = (m[st.last[0] + "," + st.last[1]] || "") + " land"; }
    return m;
  }
  function draw() {
    drawGrid(grid, rows(), { marks: marks(), label: "Teleport coin: trap in the middle of the top row, landing cells A and B, hero below the trap", cls: "p1g" });
    cnt.textContent = "A " + st.cnt.A + " · B " + st.cnt.B + " · escaped " + st.cnt.esc + (st.zone ? "" : " · elsewhere " + st.cnt.out);
    paintCtrl();
  }
  views.push(draw);
  function say(s, cls) {
    var p = h("p", { text: s }); if (cls) { p.className = cls; }
    log.insertBefore(p, log.firstChild);
    while (log.children.length > 6) { log.removeChild(log.lastChild); }
  }
  function freeCells() {
    var out = [];
    for (var y = 1; y <= 4; y++) { for (var x = 1; x <= 11; x++) { if (MAP[y][x] === "." && !(x === T[0] && y === T[1])) { out.push([x, y]); } } }
    return out;
  }
  function options() {
    var o = [["A", "Land on A"], ["B", "Land on B"]];
    if (!st.zone) { o.push(["out", "Land anywhere else"]); }
    if (!st.boots) { o.push(["esc", "“You escape” (stay on the trap)"]); }
    return o;
  }
  function paintCtrl() {
    ctrl.innerHTML = "";
    var go = $("#p1-go"), back = $("#p1-back");
    go.disabled = st.busy || st.pending || st.landed;
    back.disabled = st.busy || st.pending || (!st.landed && !st.onT && st.hero[1] === START[1]);
    if (st.pending && st.mode === "you") {
      ctrl.appendChild(h("span", { class: "p1-ask", text: "You are the dungeon. Where does the hero land?" }));
      options().forEach(function (o) {
        ctrl.appendChild(h("button", { type: "button", class: "btn " + (o[0] === "esc" ? "warn" : ""), text: o[1], onclick: function () { resolve(o[0]); } }));
      });
    }
    var n;
    if (!st.boots && st.mode === "you") { n = "No fumble boots: as the dungeon you may answer “escape” every single time. The hero never gets through, so the coin is just a wall. That is why the construction gives the hero cursed fumble boots."; }
    else if (!st.boots) { n = "No fumble boots: with fair dice the hero escapes the trap about 1 time in 5 (the game rolls 1 in 5). Under the worst-case reading (R3) the dungeon could pick that every time."; }
    else if (!st.zone) { n = "No zone: the trap may send the hero anywhere on the level. A two-way choice turns into a choice among dozens of cells, including ones the construction never planned for."; }
    else { n = "Boots on, zone on: the only two outcomes are A and B. Nothing else can happen, and the trap works forever. This is the coin."; }
    note.textContent = n;
  }
  function anim(path, done) {
    st.busy = true; paintCtrl();
    var i = 0;
    (function step() {
      if (i >= path.length) { st.busy = false; done(); return; }
      st.hero = path[i++].slice(); draw();
      setTimeout(step, 170);
    })();
  }
  function fire() {
    st.onT = true; st.pending = true; draw();
    say("The hero steps onto the teleportation trap.");
    if (st.mode === "random") { setTimeout(function () { resolve(rollRandom()); }, 350); }
  }
  function rollRandom() {
    if (!st.boots && Math.random() < 0.2) { return "esc"; }
    if (st.zone) { return Math.random() < 0.5 ? "A" : "B"; }
    var cells = freeCells(); var c = cells[Math.floor(Math.random() * cells.length)];
    if (c[0] === A[0] && c[1] === A[1]) { return "A"; }
    if (c[0] === B[0] && c[1] === B[1]) { return "B"; }
    st.outCell = c; return "out";
  }
  function resolve(o) {
    st.pending = false;
    if (o === "esc") {
      st.cnt.esc++; say("You escape a teleportation trap.", "tty");
      st.landed = false; st.last = null; draw(); return;
    }
    st.onT = false; st.landed = true;
    if (o === "A") { st.hero = A.slice(); st.cnt.A++; say("Teleported to A. From here the corridor leads down the left branch.", "tty"); }
    else if (o === "B") { st.hero = B.slice(); st.cnt.B++; say("Teleported to B. From here the corridor leads down the right branch.", "tty"); }
    else {
      var c = st.outCell; if (!c) { var cs = freeCells().filter(function (z) { return z[0] > 6; }); c = cs[Math.floor(Math.random() * cs.length)]; }
      st.outCell = null; st.hero = c.slice(); st.cnt.out++; say("Teleported to (" + c[0] + "," + c[1] + "): outside the planned cells.", "tty bad");
    }
    st.last = st.hero.slice(); draw();
  }
  $("#p1-go").addEventListener("click", function () {
    if (st.onT) { /* escaped: step off and on again */
      st.onT = false; st.hero = [T[0], 2]; draw();
      setTimeout(fire, 250); return;
    }
    var path = [];
    for (var y = st.hero[1] - 1; y >= 2; y--) { path.push([3, y]); }
    anim(path, fire);
  });
  $("#p1-back").addEventListener("click", function () {
    st.onT = false; st.landed = false; st.pending = false; st.last = null; st.hero = START.slice(); draw();
  });
  $("#p1-run").addEventListener("click", function () {
    var n = 200, c = { A: 0, B: 0, esc: 0, out: 0 };
    for (var i = 0; i < n; i++) { var r = rollRandom(); c[r]++; st.cnt[r]++; }
    st.outCell = null;
    say("200 random steps onto the trap: A " + c.A + ", B " + c.B + ", escaped " + c.esc + (st.zone ? "" : ", elsewhere " + c.out) + ".");
    draw();
  });
  function bindSeg(id, key, conv) {
    $$("#" + id + " button").forEach(function (b) {
      b.addEventListener("click", function () {
        st[key] = conv(b.getAttribute("data-v"));
        $$("#" + id + " button").forEach(function (x) { x.setAttribute("aria-pressed", String(x === b)); });
        if (st.pending && st.mode === "random") { resolve(rollRandom()); }
        draw();
      });
    });
  }
  bindSeg("p1-boots", "boots", function (v) { return v === "on"; });
  bindSeg("p1-zone", "zone", function (v) { return v === "on"; });
  bindSeg("p1-mode", "mode", function (v) { return v; });
  draw();
}

/* =====================================================================
   PLAY 2: the formula game G6
   ===================================================================== */
function lit(s) { var neg = s.charAt(0) === "~"; s = neg ? s.slice(1) : s; return { v: s.charAt(0), i: +s.slice(1) - 1, neg: neg }; }
function formula(nx, ny, cls) { return { nx: nx, ny: ny, clauses: cls.map(function (c) { return c.map(lit); }) }; }
var G6P = [
  { id: "win", name: "You can force a win", f: formula(2, 2, [["x1", "y2"], ["x2", "y1"], ["~x2", "y2", "~y1"], ["~x1", "~y2"]]), a0: 0,
    hint: "Hint: it takes three of your moves; watch which clause the opponent attacks after each one." },
  { id: "lose", name: "The opponent can hold you off", f: formula(2, 2, [["x1", "y1"], ["x2", "~y1"], ["~x1", "y2"], ["~x2", "~y2"]]), a0: 0,
    hint: "Every clause is satisfiable, and with luck F becomes true. Against a careful opponent it never does." },
  { id: "race", name: "Three of yours vs two of theirs", f: formula(3, 2, [["x1", "y1"], ["x2", "y2"], ["x3", "~y1", "~y2"], ["~x1", "~x2", "~y1"]]), a0: 0,
    hint: "Try to find a strategy, then switch on “show the solver” to check." }
];
function litStr(l) { return (l.neg ? "¬" : "") + l.v + (l.i + 1); }
function play2() {
  var host = $("#p2"); if (!host) { return; }
  var st = {};
  var fEl = $("#p2-f"), vEl = $("#p2-vars"), mEl = $("#p2-moves"), logEl = $("#p2-log"), hintEl = $("#p2-solver"), sizeEl = $("#p2-size");
  function load(k) {
    var P = G6P[k];
    st = { P: P, f: P.f, a: P.a0, turn: 0, rank: g6Solve(P.f), round: 1, over: false, hist: [] };
    logEl.innerHTML = "";
    say("New game. You move first. " + P.hint);
    draw();
  }
  function say(s, cls) { var p = h("p", { text: s }); if (cls) { p.className = cls; } logEl.insertBefore(p, logEl.firstChild); while (logEl.children.length > 7) { logEl.removeChild(logEl.lastChild); } }
  function val(v, i) { return (st.a >> (v === "x" ? i : st.f.nx + i)) & 1; }
  function draw() {
    var f = st.f;
    fEl.innerHTML = "";
    f.clauses.forEach(function (cl, k) {
      var sat = cl.some(function (l) { var b = val(l.v, l.i); return l.neg ? !b : !!b; });
      var c = h("span", { class: "cl" + (sat ? " sat" : "") });
      c.appendChild(document.createTextNode("("));
      cl.forEach(function (l, j) {
        var b = val(l.v, l.i), t = l.neg ? !b : !!b;
        if (j) { c.appendChild(document.createTextNode(" ∨ ")); }
        c.appendChild(h("span", { class: "li " + l.v + (t ? " on" : ""), text: litStr(l) }));
      });
      c.appendChild(document.createTextNode(")"));
      fEl.appendChild(c);
      if (k < f.clauses.length - 1) { fEl.appendChild(h("span", { class: "and", text: "∧" })); }
    });
    var F = g6Eval(f, st.a);
    fEl.appendChild(h("span", { class: "fv " + (F ? "t" : "f"), text: F ? "F is TRUE" : "F is false" }));
    vEl.innerHTML = "";
    var mine = h("div", { class: "vg" }, [h("span", { class: "vl", text: "Yours (X):" })]);
    for (var i = 0; i < f.nx; i++) { mine.appendChild(h("span", { class: "vb x" + (val("x", i) ? " on" : ""), text: "x" + (i + 1) + " = " + val("x", i) })); }
    var theirs = h("div", { class: "vg" }, [h("span", { class: "vl", text: "Opponent's (Y):" })]);
    for (var j = 0; j < f.ny; j++) { theirs.appendChild(h("span", { class: "vb y" + (val("y", j) ? " on" : ""), text: "y" + (j + 1) + " = " + val("y", j) })); }
    vEl.appendChild(mine); vEl.appendChild(theirs);
    mEl.innerHTML = "";
    if (!st.over) {
      for (var k2 = 0; k2 < f.nx; k2++) { (function (q) { mEl.appendChild(h("button", { type: "button", class: "btn", text: "Flip x" + (q + 1), onclick: function () { move(q); } })); })(k2); }
      mEl.appendChild(h("button", { type: "button", class: "btn ghost", text: "Pass", onclick: function () { move(-1); } }));
    }
    mEl.appendChild(h("span", { class: "rd", text: "Round " + st.round }));
    var r = st.rank[0][st.a];
    hintEl.textContent = st.over ? "" : (r >= 0 ? "Solver: from here you CAN force a win (in at most " + Math.ceil(r / 2) + " of your moves)." : "Solver: from here the opponent can stop you forever. You cannot force a win.");
    var n = f.nx + f.ny;
    sizeEl.textContent = "This game: " + n + " variables, so 2^" + n + " × 2 = " + (2 << n) + " positions. Every position was solved above. With 40 variables there would be 2^41 ≈ 2.2 trillion positions; with 300, more than atoms in the universe.";
  }
  function move(i) {
    if (st.over) { return; }
    st.a = i < 0 ? st.a : st.a ^ (1 << i);
    say("You: " + (i < 0 ? "pass" : "flip x" + (i + 1) + " to " + ((st.a >> i) & 1)) + ".");
    if (g6Eval(st.f, st.a)) { st.over = true; say("F is true: you win!", "good"); draw(); return; }
    var m = g6Opp(st.f, st.rank, st.a);
    st.a = m < 0 ? st.a : st.a ^ (1 << (st.f.nx + m));
    say("Opponent: " + (m < 0 ? "pass" : "flip y" + (m + 1) + " to " + ((st.a >> (st.f.nx + m)) & 1)) + ".");
    if (g6Eval(st.f, st.a)) { st.over = true; say("F became true after the opponent's move: you win anyway (G6: “if F ever becomes true”).", "good"); draw(); return; }
    st.round++;
    if (st.round === 13 && st.rank[0][st.a] < 0) { say("Twelve rounds and still false. If this goes on forever, the opponent wins (a draw counts for them).", "bad"); }
    draw();
  }
  $$("#p2-preset button").forEach(function (b, k) {
    b.addEventListener("click", function () { $$("#p2-preset button").forEach(function (x) { x.setAttribute("aria-pressed", String(x === b)); }); load(k); });
  });
  $("#p2-show").addEventListener("change", function (e) { hintEl.hidden = !e.target.checked; });
  $("#p2-reset").addEventListener("click", function () { load(G6P.indexOf(st.P)); });
  load(0);
}

/* =====================================================================
   Gadget library (from tools/exptime/A_library.py, 2026-10-29)
   ===================================================================== */
var LIB = {
  diode_ck: { name: "Checkable diode (diode_ck)", rows: ["#A#B##", "#.0..#", "##C#D#", "######"], mode: "checkable", target: "diode",
    checks: "A>C, D>B", joins: "C=D", ext: "A,B" },
  slot1: { name: "SLOT1 (fails: overshoot)", rows: ["#A#B##", "#.0..#", "##.#.#", "##...#", "######"], mode: "pure", target: "diode" },
  uturn2: { name: "UTURN2 (fails: complete, unsound)", rows: ["########", "##...###", "##.#.###", "##.#.#.B", "#.0.0..#", "#.#....#", "#A##..##", "########"], mode: "pure", target: "diode" },
  gd: { name: "G_D one-way door (single use, NP proof)", rows: ["######", "E.e0.#", "###q##", "###Q##"], mode: "pure", target: "gd" },
  precursor: { name: "Proto-precursor (Ani et al. Fig. 36a, in progress)", rows: ["##A#B##C##", "##.#..#.##", "#...0.0..#", "#.#.##.#.#", "#D#E##F#G#"], mode: "pure", target: "diode",
    note: "No ideal target for this piece is in the lab yet: use Walk inside to explore it. Its checks in the paper are A>D, C>G, B>A, B>C." },
  empty: { name: "Empty frame", rows: ["########", "#......#", "#......#", "#......#", "#......#", "##A##B##"], mode: "pure", target: "diode" }
};

/* =====================================================================
   PLAY 3: gadget lab
   ===================================================================== */
var Lab = null;
function lab() {
  var host = $("#lab"); if (!host) { return; }
  var MAXW = 10, MAXH = 8;
  var st = { rows: LIB.diode_ck.rows.slice(), tool: "#", hero: null, B: null, walkBoard: null, painting: false };
  var gEl = $("#lab-grid"), out = $("#lab-out"), txt = $("#lab-text"), tgt = $("#lab-target"), mode = $("#lab-mode");
  var chk = $("#lab-checks"), jn = $("#lab-joins"), ex = $("#lab-ext"), wmsg = $("#lab-walkmsg");
  Object.keys(TARGETS).forEach(function (k) { tgt.appendChild(h("option", { value: k, text: TARGETS[k].name + " — ports " + TARGETS[k].ports.join(" ") })); });
  function grid() { return st.rows.map(function (r) { return r.split(""); }); }
  function setRows(r) {
    var W = Math.min(MAXW, Math.max(3, Math.max.apply(null, r.map(function (s) { return s.length; }))));
    st.rows = r.slice(0, MAXH).map(function (s) { s = s.slice(0, W); while (s.length < W) { s += "#"; } return s.replace(/ /g, "#"); });
    while (st.rows.length < 3) { st.rows.push(new Array(W + 1).join("#")); }
    stopWalk(); draw();
  }
  function draw() {
    var r = st.rows;
    if (st.walkBoard) { r = st.walkBoard.show(st.B, st.hero).map(function (s, y) {
      /* keep port letters visible under the hero only when not on them */
      return s; }); }
    drawGrid(gEl, r, { cls: "labg" + (st.walkBoard ? " walking" : ""), label: "Gadget lab grid" });
    txt.value = st.rows.join("\n");
    $("#lab-size").textContent = st.rows[0].length + " × " + st.rows.length;
    var cp = $("#lab-ckrow"); cp.hidden = mode.value !== "checkable";
  }
  views.push(draw);
  function nextPort() {
    var used = st.rows.join(""), want = TARGETS[tgt.value].ports.concat("ABCDEFGHIJKLMNOPQRSTUVWXYZ".split(""));
    for (var i = 0; i < want.length; i++) { if (used.indexOf(want[i]) < 0 && want[i] !== "G") { return want[i]; } }
    return null;
  }
  function paint(x, y) {
    if (st.walkBoard) { return; }
    var g = grid(), cur = g[y][x], ch = st.tool;
    if (ch === "P") { if (cur >= "A" && cur <= "Z") { return; } ch = nextPort(); if (!ch) { return; } }
    if (cur === ch) { return; }
    g[y][x] = ch;
    st.rows = g.map(function (r) { return r.join(""); });
    draw();
  }
  function cellOf(e) { var c = e.target.closest && e.target.closest(".c"); return c ? [+c.getAttribute("data-x"), +c.getAttribute("data-y")] : null; }
  gEl.addEventListener("pointerdown", function (e) {
    var c = cellOf(e); if (!c) { return; }
    if (st.walkBoard) { walkTo(c); return; }
    st.painting = true; paint(c[0], c[1]); e.preventDefault();
  });
  gEl.addEventListener("pointerover", function (e) { if (!st.painting) { return; } var c = cellOf(e); if (c) { paint(c[0], c[1]); } });
  document.addEventListener("pointerup", function () { st.painting = false; });
  $$("#lab-tools button").forEach(function (b) {
    b.addEventListener("click", function () {
      st.tool = b.getAttribute("data-t");
      $$("#lab-tools button").forEach(function (x) { x.setAttribute("aria-pressed", String(x === b)); });
    });
  });
  function resize(dw, dh) {
    var g = grid(), W = g[0].length + dw, H = g.length + dh;
    if (W < 3 || W > MAXW || H < 3 || H > MAXH) { return; }
    if (dw > 0) { g.forEach(function (r) { r.push("#"); }); } else if (dw < 0) { g.forEach(function (r) { r.pop(); }); }
    if (dh > 0) { g.push(new Array(W).fill("#")); } else if (dh < 0) { g.pop(); }
    st.rows = g.map(function (r) { return r.join(""); }); draw();
  }
  $("#lab-wm").addEventListener("click", function () { resize(-1, 0); });
  $("#lab-wp").addEventListener("click", function () { resize(1, 0); });
  $("#lab-hm").addEventListener("click", function () { resize(0, -1); });
  $("#lab-hp").addEventListener("click", function () { resize(0, 1); });
  $("#lab-apply").addEventListener("click", function () {
    var r = txt.value.split(/\r?\n/).filter(function (s) { return s.length; });
    if (r.length) { setRows(r.map(function (s) { return s.replace(/[^#.0A-Za-z ]/g, "#"); })); }
  });
  mode.addEventListener("change", draw);
  function parsePairs(s) {
    return s.split(/[,;]/).map(function (t) { return t.trim().toUpperCase(); }).filter(Boolean).map(function (t) { var m = t.split(/\s*(?:>|->|→)\s*/); return [m[0], m[1]]; })
      .filter(function (p) { return p[0] && p[1]; });
  }
  function load(key) {
    var L = LIB[key]; if (!L) { return; }
    tgt.value = L.target; mode.value = L.mode;
    chk.value = L.checks || ""; jn.value = L.joins || ""; ex.value = L.ext || TARGETS[L.target].ports.join(",");
    setRows(L.rows.slice());
    out.innerHTML = ""; out.appendChild(h("p", { class: "muted", text: "Loaded “" + L.name + "”. " + (L.note || "Press Check.") }));
  }
  $$("#lab-presets button").forEach(function (b) { b.addEventListener("click", function () { load(b.getAttribute("data-g")); }); });
  tgt.addEventListener("change", function () { ex.value = TARGETS[tgt.value].ports.join(","); });

  /* walk mode */
  function stopWalk() { st.walkBoard = null; st.hero = null; wmsg.textContent = ""; $("#lab-walk").textContent = "Walk inside"; }
  $("#lab-walk").addEventListener("click", function () {
    if (st.walkBoard) { stopWalk(); draw(); return; }
    var b = new Board(st.rows), ps = Object.keys(b.ports).sort();
    if (!ps.length) { wmsg.textContent = "Add a port first."; return; }
    st.walkBoard = b; st.B = b.b0; st.hero = b.ports[ps[0]];
    $("#lab-walk").textContent = "Stop walking";
    wmsg.textContent = "Hero on port " + ps[0] + ". Click a neighbouring cell to step or push; click another port letter's cell when adjacent to leave through it. Click any port far away to re-enter there.";
    draw();
  });
  function walkTo(c) {
    var b = st.walkBoard, i = b.idx[c[0] + "," + c[1]];
    if (i === undefined) { return; }
    if (b.portname[i] !== undefined && b.portname[st.hero] !== undefined && i !== st.hero) {
      var adj = Math.abs(b.cells[i][0] - b.cells[st.hero][0]) <= 1 && Math.abs(b.cells[i][1] - b.cells[st.hero][1]) <= 1;
      if (!adj) { st.hero = i; wmsg.textContent = "Re-entered at port " + b.portname[i] + " (walking around outside)."; draw(); return; }
    }
    var ms;
    try { ms = b.moves(st.hero, st.B); } catch (e) { ms = []; wmsg.textContent = "A push here would put a boulder on a port: LEAK."; }
    var m = ms.filter(function (x) { return x[0] === i; })[0];
    if (!m) { wmsg.textContent = "Not a legal move (walls, two boulders in a row, no diagonal pushes, corner rule)."; return; }
    var pushed = m[1] !== st.B;
    st.hero = m[0]; st.B = m[1];
    wmsg.textContent = (pushed ? "Pushed a boulder. " : "") + (b.portname[i] !== undefined ? "Hero on port " + b.portname[i] + ": this traversal ends here." : "");
    draw();
  }

  function fmtState(board, s) { return board.show(BigInt(s)).join("\n"); }
  function run() {
    stopWalk(); draw();
    out.innerHTML = "";
    var b0 = new Board(st.rows), ports = Object.keys(b0.ports).sort();
    var T = TARGETS[tgt.value];
    if (ports.length < 2) { out.appendChild(h("p", { class: "bad", text: "Need at least two ports (capital letters on floor cells)." })); return; }
    if (b0.cells.length > 60) { out.appendChild(h("p", { class: "bad", text: "Too big for the browser: " + b0.cells.length + " floor cells (limit 60). Use tools/exptime/A_check.py." })); return; }
    var res, t0 = Date.now();
    if (mode.value === "checkable") {
      var joins = jn.value.split(/[,;]/).map(function (g) { return g.split(/[=\s]+/).map(function (x) { return x.trim().toUpperCase(); }).filter(Boolean); }).filter(function (g) { return g.length; });
      var ext = ex.value.split(/[,\s]+/).map(function (x) { return x.trim().toUpperCase(); }).filter(Boolean);
      var allp = [].concat.apply(ext, joins);
      if (!sameSet(allp, ports)) { out.appendChild(h("p", { class: "bad", text: "In checkable mode every port must be either joined or external. Ports on the board: " + ports.join(" ") + "." })); return; }
      if (!sameSet(ext, T.ports)) { out.appendChild(h("p", { class: "bad", text: "External ports must be the target's ports: " + T.ports.join(" ") + "." })); return; }
      res = reportCheckable(st.rows, parsePairs(chk.value), joins, ext, tgt.value);
    } else {
      if (!sameSet(ports, T.ports)) { out.appendChild(h("p", { class: "bad", text: "The target “" + T.name + "” has ports " + T.ports.join(" ") + "; the board has " + ports.join(" ") + ". Rename ports (type in the text box) or change the target." })); return; }
      res = reportPure(st.rows, tgt.value);
    }
    var dt = Date.now() - t0;
    if (res.error) {
      if (res.error.leak) { out.appendChild(h("p", { class: "bad", text: "LEAK: a boulder can be pushed onto a port cell (from " + res.error.from + " to " + res.error.to + "). Boulders must never leave the gadget. Rejected." })); }
      else { out.appendChild(h("p", { class: "bad", text: "Too big: the search passed its cap (" + res.error.what + "). Try a smaller board or fewer boulders, or run A_check.py." })); }
      return;
    }
    var C = res.C;
    out.appendChild(h("p", { text: C.states.length + " reachable local states (boulder positions), " + b0.cells.length + " floor cells, " + popcount(b0.b0) + " boulder(s); " + dt + " ms." }));
    if (res.checkable) {
      var tb = h("table", { class: "rt" }, [h("tr", {}, [h("th", { text: "state" }), h("th", { text: "status" }), h("th", { text: "port-to-port traversals" })])]);
      C.states.forEach(function (s) {
        tb.appendChild(h("tr", {}, [h("td", {}, [h("pre", { class: "mini", text: fmtState(res.board, s) })]),
          h("td", { class: res.clean.has(s) ? "good" : "bad", text: res.clean.has(s) ? "clean" : "BROKEN" }),
          h("td", { text: res.rel[s].join(", ") || "(none)" })]));
      });
      out.appendChild(h("div", { class: "tbl" }, [tb]));
      out.appendChild(h("ul", { class: "verd" }, [
        h("li", { html: "initial state clean: <b>" + res.initClean + "</b>" }),
        h("li", { html: "broken states absorbing (no traversal repairs them): <b>" + res.absorbing + "</b>" }),
        h("li", { html: "after postselection and joining, vs the ideal " + T.name + ": SOUND <b>" + res.sound + "</b>, COMPLETE <b>" + res.complete + "</b>" }),
        h("li", { html: "raw (no check path): SOUND <b>" + res.rawSound + "</b>, COMPLETE <b>" + res.rawComplete + "</b>" })]));
      out.appendChild(h("p", { class: "verdict " + (res.ok ? "good" : "bad"), text: res.ok
        ? "✓ Works as a CHECKABLE " + T.name + ": correct as long as a final check path proves it was never broken. (That is the kind we already have.)"
        : "✗ Not a checkable " + T.name + " with these checks." }));
    } else {
      var tb2 = h("table", { class: "rt" }, [h("tr", {}, [h("th", { text: "states" }), h("th", { text: "port-to-port traversals" }), h("th", { text: "behaves like ideal state" })])]);
      res.groups.forEach(function (g) {
        tb2.appendChild(h("tr", {}, [h("td", { text: String(g.states.length) }), h("td", { text: g.relation }),
          h("td", { class: g.simulatedBy.length ? "good" : "bad", text: g.simulatedBy.length ? g.simulatedBy.join(", ") : "none (unsafe)" })]));
      });
      out.appendChild(h("div", { class: "tbl" }, [tb2]));
      out.appendChild(h("ul", { class: "verd" }, [
        h("li", { html: "SOUND (it never does more than the ideal " + T.name + "): <b>" + res.sound + "</b>" }),
        h("li", { html: "COMPLETE (it can do everything the ideal one does): <b>" + res.complete + "</b>" })]));
      var good = res.sound && res.complete;
      var wanted = tgt.value === "diode" || tgt.value === "scd" || tgt.value === "scd4" || tgt.value === "xover";
      out.appendChild(h("p", { class: "verdict " + (good ? "good" : "bad"), text: good
        ? (wanted ? "✓ A reusable, unbreakable " + T.name + "! None was found in about 1.4 million boards. Please copy the layout below and send it to Ivan." : "✓ Behaves exactly like the ideal " + T.name + ".")
        : "✗ Not game-safe as a reusable " + T.name + (res.sound ? " (it cannot do everything the ideal one does)." : " (some reachable state allows a move the ideal gadget forbids).") }));
      if (good && wanted) { txt.focus(); }
    }
  }
  $("#lab-run").addEventListener("click", run);
  Lab = { load: load };
  load("diode_ck");
}

/* =====================================================================
   Gadget gallery: step-throughs built from the engine
   ===================================================================== */
function legsToFrames(board, legs, captions) {
  /* legs: [[from, to, B_before, B_after|null(any)]], returns frames {rows, cap} */
  var frames = [];
  legs.forEach(function (lg, k) {
    var Bb = typeof lg[2] === "bigint" ? lg[2] : BigInt(lg[2]), Ba = lg[3] === null ? null : (typeof lg[3] === "bigint" ? lg[3] : BigInt(lg[3]));
    var path = board.walk(Bb, lg[0], lg[1], Ba);
    if (!path) { return; }
    path.forEach(function (s, i) {
      var cap = (captions && captions[k]) || ("Traversal " + lg[0] + " → " + lg[1]);
      var pre = i === 0 ? "Enter at " + lg[0] + ". " : (i === path.length - 1 ? "Leave at " + lg[1] + ". " : "");
      frames.push({ rows: board.show(s[1], s[0]), cap: pre + cap, step: (k + 1) + "." + (i + 1) });
    });
  });
  return frames;
}
function stepper(host, frames, label) {
  var i = 0, g = h("div", {}), cap = h("p", { class: "stc", "aria-live": "polite" }), ctr = h("span", { class: "stn" });
  var prev = h("button", { type: "button", class: "btn sm", text: "◀ Back", onclick: function () { show(i - 1); } });
  var next = h("button", { type: "button", class: "btn sm", text: "Step ▶", onclick: function () { show(i + 1); } });
  var rst = h("button", { type: "button", class: "btn sm ghost", text: "Restart", onclick: function () { show(0); } });
  host.appendChild(g); host.appendChild(h("div", { class: "stb" }, [prev, next, rst, ctr])); host.appendChild(cap);
  function show(k) {
    i = Math.max(0, Math.min(frames.length - 1, k));
    drawGrid(g, frames[i].rows, { label: label });
    cap.textContent = frames[i].cap; ctr.textContent = (i + 1) + " / " + frames.length;
    prev.disabled = i === 0; next.disabled = i === frames.length - 1;
  }
  views.push(function () { show(i); });
  show(0);
}
function gallery() {
  $$(".gal-step").forEach(function (host) {
    var key = host.getAttribute("data-g"), kind = host.getAttribute("data-k"), L = LIB[key], b = new Board(L.rows), frames = [];
    if (key === "diode_ck" && kind === "use") {
      /* intended diode use: A -> C (push X east), corridor C..D outside, D -> B (push X west) */
      var C = explore(b), m1 = b.b0, m2 = null;
      var clean = postselect(C, [["A", "C"], ["D", "B"]]).clean;
      C.tr(String(m1), "A").forEach(function (x) { if (x[0] === "C" && clean.has(x[1])) { m2 = BigInt(x[1]); } });
      frames = legsToFrames(b, [["A", "C", m1, m2]], ["Push the boulder one step east (m1 to m2), then drop down to C."])
        .concat([{ rows: b.show(m2, null), cap: "The hero walks the free corridor joining C to D (outside this window). The boulder waits on m2.", step: "" }])
        .concat(legsToFrames(b, [["D", "B", m2, m1]], ["From D step up, push the boulder back west (m2 to m1), and leave at B. Same state as at the start: reusable."]));
    } else if (key === "diode_ck" && kind === "break") {
      var e2 = null;
      explore(b).states.forEach(function (s) { var B = BigInt(s); var xy = b.cells[Math.round(Math.log2(Number(B)))]; if (xy && xy[0] === 4) { e2 = B; } });
      frames = legsToFrames(b, [["A", "B", b.b0, e2], ["B", "A", e2, e2]],
        ["Push east twice: the boulder overshoots to the far end (e2) and is stuck there for good.", "Now the way from B back to A is open: the gadget is BROKEN. Only the final check path notices."]);
    } else if (kind === "static") {
      frames = [{ rows: b.show(b.b0, null), cap: "Initial layout as transcribed (boulders on the track). No verdict yet.", step: "" }];
    } else if (key === "gd") {
      var after = null; explore(b).tr(String(b.b0), "E").forEach(function (x) { if (x[0] === "Q") { after = BigInt(x[1]); } });
      frames = legsToFrames(b, [["E", "Q", b.b0, after], ["Q", "E", after, after]],
        ["Push the boulder east into the pocket and go down to Q.", "Once opened it stays open: from Q the hero can walk back to E. Fine for one use, useless as a reusable diode."]);
    } else {
      var legs = findPair(b, "B", "A");
      if (legs) {
        frames = legsToFrames(b, legs, legs.map(function (lg, k) {
          return k === legs.length - 1 ? "Counterexample: the hero now walks from B back to A, which a diode must never allow." : "Set-up traversal " + lg[0] + " → " + lg[1] + ".";
        }));
      }
    }
    stepper(host, frames, L.name);
  });
  $$("[data-open-lab]").forEach(function (b) {
    b.addEventListener("click", function () {
      if (!Lab) { return; }
      Lab.load(b.getAttribute("data-open-lab"));
      var l = $("#play3"); if (l) { l.scrollIntoView({ behavior: "smooth" }); }
    });
  });
}

/* =====================================================================
   Animated walk-throughs (frames from tools/visual/animate_gadgets.py:
   BFS-shortest walks under A_core's movement model, same as the GIFs
   in media/exptime/anim/). Drawn with drawGrid, so Text/Tiles applies.
   ===================================================================== */
function animRows(A, f) {
  var g = A.rows.map(function (r) { return r.split(""); });
  f.o.forEach(function (c) { g[c[1]][c[0]] = "*"; });
  f.b.forEach(function (c) { g[c[1]][c[0]] = "0"; });
  if (f.h) { g[f.h[1]][f.h[0]] = "@"; }
  return g.map(function (r) { return r.join(""); });
}
function animPlayer(host, A) {
  var n = A.frames.length, i = 0, timer = null, playing = false, userPaused = false, visible = false;
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var ph = h("p", { class: "anp" }), g = h("div", {}), cap = h("p", { class: "stc" }), ctr = h("span", { class: "stn" });
  var play = h("button", { type: "button", class: "btn sm", text: "▶ Play", onclick: function () {
    if (playing) { userPaused = true; stop(); } else { userPaused = false; start(); } } });
  var prev = h("button", { type: "button", class: "btn sm ghost", text: "◀", "aria-label": "Previous step", onclick: function () { userPaused = true; stop(); show(i - 1); } });
  var next = h("button", { type: "button", class: "btn sm ghost", text: "▶", "aria-label": "Next step", onclick: function () { userPaused = true; stop(); show(i + 1); } });
  host.innerHTML = "";
  host.appendChild(ph); host.appendChild(g); host.appendChild(h("div", { class: "stb" }, [play, prev, next, ctr])); host.appendChild(cap);
  function show(k) {
    i = ((k % n) + n) % n;
    var f = A.frames[i], marks = {}, over = {};
    Object.keys(A.labels).forEach(function (key) { over[key] = A.labels[key]; });
    f.b.forEach(function (c) { if (c[2]) { over[c[0] + "," + c[1]] = c[2]; } });
    if (f.n) { marks[f.n[0] + "," + f.n[1]] = "nope"; }
    if (f.f) { marks[f.f[0] + "," + f.f[1]] = "land"; }
    drawGrid(g, animRows(A, f), { label: A.title, marks: marks, over: over, noGoal: true, cls: "ang" });
    var cols = A.rows[0].length, avail = (host.clientWidth || 300) - 10;
    g.style.setProperty("--cs", Math.max(12, Math.min(30, Math.floor(avail / cols))) + "px");
    ph.textContent = f.p;
    cap.textContent = f.c; cap.classList.toggle("bad", !!f.n);
    ctr.textContent = (i + 1) + " / " + n;
  }
  function tick() {
    var d = A.frames[i].d || 220;
    timer = setTimeout(function () { show(i + 1); if (playing) { tick(); } }, d);
  }
  function start() { if (playing) { return; } playing = true; play.textContent = "❚❚ Pause"; tick(); }
  function stop() { playing = false; play.textContent = "▶ Play"; if (timer) { clearTimeout(timer); timer = null; } }
  views.push(function () { show(i); });
  show(0);
  if (!reduce && "IntersectionObserver" in window) {
    new IntersectionObserver(function (es) {
      es.forEach(function (e) {
        visible = e.isIntersecting;
        if (visible && !userPaused) { start(); } else if (!visible) { stop(); }
      });
    }, { threshold: 0.4 }).observe(host);
  }
}
function animCards() {
  var hosts = $$(".gal-anim");
  if (!hosts.length) { return; }
  if (!window.fetch) { hosts.forEach(function (x) { x.textContent = "This browser cannot load the animation data."; }); return; }
  fetch("engine/anims_exptime.json?v=20261030a").then(function (r) { return r.json(); }).then(function (d) {
    var by = {};
    d.anims.forEach(function (a) { by[a.id] = a; });
    hosts.forEach(function (x) { var A = by[x.getAttribute("data-a")]; if (A) { animPlayer(x, A); } else { x.textContent = "Animation missing."; } });
  }).catch(function () { hosts.forEach(function (x) { x.textContent = "Animation data could not be loaded (open the page over http)."; }); });
}

/* =====================================================================
   boot
   ===================================================================== */
var d0 = gdepth();
var v0 = null; try { v0 = localStorage.getItem("exptime-view"); } catch (e) { /* none */ }
setView(v0 === "tiles" || (v0 === null && d0 === "0") ? "tiles" : "text", false);
setGlobal(d0, false);
play1(); play2(); lab(); gallery(); animCards();
loadTiles();
})();
