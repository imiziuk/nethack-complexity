/* engine.js: formula input -> Pyodide worker running gen_on_instance.py -> drawing, verdict, playable level,
   stats against the section 4.6 bounds, Lua download. Viewer rules are copied from site/arena.src.html. */
(function () {
"use strict";

// ------------------------------------------------------------------ limits and presets
var MAX_N = 8, MAX_M = 8, MAX_ORDERS = 50000;
var PRESETS = [
  { grp: "Levels from the arena (build/arena)" },
  { id: "warm", f: "x1 ∧ ¬x1", note: "warm-up, UNSAT" },
  { id: "sat1", f: "(x1 ∨ x2) ∧ (¬x1 ∨ ¬x2)", note: "SAT: exactly one true" },
  { id: "sat2", f: "(x1 ∨ x2 ∨ x3) ∧ (¬x1 ∨ ¬x2) ∧ ¬x3", note: "SAT" },
  { id: "o1", f: "x3 ∧ ¬x3 ∧ (x1 ∨ x2 ∨ x3)", note: "UNSAT, checker level" },
  { id: "o2", f: "x1 ∧ ¬x1 ∧ (¬x1 ∨ ¬x2 ∨ ¬x3)", note: "UNSAT, checker level" },
  { id: "o3", f: "x3 ∧ ¬x3 ∧ (¬x1 ∨ ¬x2 ∨ ¬x3)", note: "UNSAT, checker level" },
  { id: "o4", f: "x2 ∧ ¬x2 ∧ (x1 ∨ x2 ∨ x3)", note: "UNSAT, checker level" },
  { id: "o5", f: "x2 ∧ ¬x2 ∧ (¬x1 ∨ ¬x2 ∨ ¬x3)", note: "UNSAT, checker level" },
  { grp: "Other examples" },
  { id: "nest", f: "(x1 ∨ x4) ∧ (x2 ∨ x3) ∧ (¬x1 ∨ ¬x2 ∨ ¬x3) ∧ ¬x4", note: "SAT, nested clauses (level 2)" },
  { id: "four", f: "(x1 ∨ x2 ∨ x3) ∧ (x3 ∨ x4) ∧ (¬x1 ∨ ¬x2) ∧ (¬x3 ∨ ¬x4)", note: "SAT, 4 variables" },
  { id: "unit", f: "(x1 ∨ x2) ∧ ¬x1 ∧ ¬x2", note: "UNSAT, three clauses" },
  { id: "dimacs", f: "1 2 3, -1 -2 -3", note: "DIMACS-style input, SAT" },
  { id: "cross", f: "(x1 ∨ x3) ∧ (x2 ∨ x4)", note: "error: no planar drawing" },
  { id: "mixed", f: "(x1 ∨ ¬x2) ∧ x2", note: "error: not monotone" }
];

// ------------------------------------------------------------------ helpers
function $(id) { return document.getElementById(id); }
function el(tag, attrs, text) {
  var e = document.createElement(tag);
  if (attrs) Object.keys(attrs).forEach(function (k) { e.setAttribute(k, attrs[k]); });
  if (text != null) e.textContent = text;
  return e;
}
function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
function fmt(x) { return x == null ? "—" : typeof x === "number" ? x.toLocaleString("en-US") : String(x); }
function litStr(l, names) { var v = Math.abs(l), nm = names ? names[v - 1] : v; return (l < 0 ? "¬" : "") + "x" + nm; }
function sortedC(c) { return c.slice().sort(function (a, b) { return Math.abs(a) - Math.abs(b); }); }
function clauseStr(c, names) { var s = c.map(function (l) { return litStr(l, names); }).join(" ∨ "); return c.length > 1 ? "(" + s + ")" : s; }
function fact(k) { var r = 1; for (var i = 2; i <= k; i++) r *= i; return r; }

// ------------------------------------------------------------------ parser
function ParseError(list) { this.list = list; }
function parseFormula(src) {
  var errs = [];
  var s = src.replace(/\r/g, "").trim();
  if (!s) throw new ParseError(["Empty input. Type at least one clause, e.g. <code>(x1 ∨ x2) ∧ ¬x1</code>."]);
  var t = s.replace(/[∧⋀]/g, " & ").replace(/&&/g, " & ").replace(/\band\b/gi, " & ")
           .replace(/[∨⋁]/g, " | ").replace(/\|\|/g, " | ").replace(/\bor\b/gi, " | ")
           .replace(/(^|[\s(])v(?=[\s(])/gi, "$1 | ")
           .replace(/[¬~!]/g, " -").replace(/\bnot\b/gi, " -").replace(/-\s+/g, "-");
  var depth = 0;
  for (var i = 0; i < t.length; i++) {
    if (t[i] === "(") { depth++; if (depth > 1) throw new ParseError(["Nested parentheses: a CNF clause is a flat disjunction of literals."]); }
    if (t[i] === ")") { depth--; if (depth < 0) throw new ParseError(["Unbalanced parentheses: a <code>)</code> without a matching <code>(</code>."]); }
  }
  if (depth !== 0) throw new ParseError(["Unbalanced parentheses: a <code>(</code> is never closed."]);
  var groups = [], pieces;
  if (t.indexOf("(") >= 0) {
    var r = t.replace(/\(([^()]*)\)/g, function (_, g) { groups.push(g); return " #" + (groups.length - 1) + " "; });
    pieces = r.split(/[&,;\n]/);
    pieces = pieces.map(function (p) {
      var q = p.trim(), m = q.match(/^#(\d+)$/);
      if (m) return groups[+m[1]];
      if (q.indexOf("#") >= 0) { errs.push("Cannot read <code>" + esc(p.trim().replace(/#(\d+)/g, function (_, k) { return "(" + groups[+k].trim() + ")"; }).replace(/\|/g, "∨").replace(/&/g, "∧")) + "</code>: clauses must be joined by ∧ (or <code>&amp;</code>, <code>,</code>). A <code>∨</code> between two parenthesised clauses is not CNF."); return ""; }
      return q;
    });
  } else {
    pieces = t.split(/[&,;\n]/);
  }
  var clauses = [], texts = [];
  pieces.forEach(function (p) {
    var raw = p.trim();
    if (!raw) return;
    var toks = raw.split(/[\s|,]+/).filter(Boolean);
    if (toks.length > 1 && toks[toks.length - 1] === "0") toks.pop();       // DIMACS clause terminator
    var c = [], bad = false;
    toks.forEach(function (tok) {
      var m = tok.match(/^(-*)(?:x_?)?(\d+)$/i);
      if (!m) { errs.push("Clause " + (clauses.length + 1) + ": cannot read <code>" + esc(tok) + "</code> as a literal (expected <code>x3</code>, <code>¬x3</code>, <code>3</code> or <code>-3</code>)."); bad = true; return; }
      if (m[1].length > 1) { errs.push("Clause " + (clauses.length + 1) + ": <code>" + esc(tok) + "</code> has a repeated negation; write the literal without it."); bad = true; return; }
      var v = +m[2];
      if (v < 1) { errs.push("Clause " + (clauses.length + 1) + ": variables are numbered from 1 (found <code>" + esc(tok) + "</code>)."); bad = true; return; }
      c.push(m[1] ? -v : v);
    });
    clauses.push(c); texts.push(raw); if (bad) c.bad = true;
  });
  if (!clauses.length && !errs.length) errs.push("No clauses found.");
  clauses.forEach(function (c, j) {
    if (c.bad) return;
    var label = "Clause " + (j + 1) + " " + esc(clauseStr(c));
    if (c.length === 0) { errs.push("Clause " + (j + 1) + " is empty."); return; }
    var vars = c.map(Math.abs), uniq = vars.filter(function (v, k) { return vars.indexOf(v) === k; });
    var pos = c.filter(function (l) { return l > 0; }).length;
    var opp = uniq.filter(function (v) { return c.indexOf(v) >= 0 && c.indexOf(-v) >= 0; });
    if (pos && pos < c.length) errs.push(label + " is not monotone: it mixes positive and negative literals" + (opp.length ? " (it even contains both x" + opp[0] + " and ¬x" + opp[0] + ")" : "") + ". In the source problem every clause is all-positive (drawn above the variable line) or all-negative (below).");
    else if (uniq.length < c.length) errs.push(label + " repeats a variable. A clause has 1 to 3 <i>distinct</i> variables; write each once.");
    if (uniq.length > 3) errs.push(label + " has " + uniq.length + " variables; 3-SAT clauses have at most 3.");
  });
  var n = 0; clauses.forEach(function (c) { c.forEach(function (l) { n = Math.max(n, Math.abs(l)); }); });
  if (n > MAX_N) errs.push("Uses x" + n + ": this page allows n ≤ " + MAX_N + " (see “Syntax, conditions and size limits” above).");
  if (clauses.length > MAX_M) errs.push(clauses.length + " clauses: this page allows m ≤ " + MAX_M + " (see “Syntax, conditions and size limits” above).");
  if (errs.length) throw new ParseError(errs);
  // leg-order search size (what Layout's brute force will enumerate)
  var orders = {};
  ["pos", "neg"].forEach(function (s) {
    var k = {};
    clauses.forEach(function (c) { if ((c[0] > 0) === (s === "pos")) c.forEach(function (l) { k[Math.abs(l)] = (k[Math.abs(l)] || 0) + 1; }); });
    orders[s] = Object.keys(k).reduce(function (a, v) { return a * fact(k[v]); }, 1);
  });
  if (orders.pos > MAX_ORDERS || orders.neg > MAX_ORDERS)
    throw new ParseError(["The leg-order search would try " + fmt(Math.max(orders.pos, orders.neg)) + " candidate orders on one side (the product over variables of k<sub>v</sub>!, k<sub>v</sub> = clauses on that side containing x<sub>v</sub>). This page stops at " + fmt(MAX_ORDERS) + ". Spread the clauses over more variables."]);
  return { n: n, clauses: clauses, orders: orders };
}

// ------------------------------------------------------------------ satisfiability (JS, independent of Python)
function bruteSAT(n, clauses) {
  var count = 0, first = null, N = 1 << n;
  for (var idx = 0; idx < N; idx++) {                // same order as itertools.product([False, True], repeat=n)
    var ok = true;
    for (var j = 0; j < clauses.length && ok; j++) {
      var c = clauses[j], sat = false;
      for (var q = 0; q < c.length; q++) { var v = Math.abs(c[q]), b = (idx >> (n - v)) & 1; if ((b === 1) === (c[q] > 0)) { sat = true; break; } }
      ok = sat;
    }
    if (ok) { count++; if (!first) { first = []; for (var v2 = 1; v2 <= n; v2++) first.push(((idx >> (n - v2)) & 1) === 1); } }
  }
  return { count: count, total: N, first: first };
}

// ------------------------------------------------------------------ worker
var worker = null, loadFails = 0, ready = false, runId = 0, pending = null, tStart = 0, tickTimer = null;
function setLoad(state, html) {
  $("loaddot").className = "dot" + (state === "ok" ? " ok" : state === "bad" ? " bad" : " busy");
  $("loadmsg").innerHTML = html;
}
function startWorker() {
  ready = false; $("go").disabled = true;
  setLoad("busy", "Loading Python (Pyodide 0.26.4, about 10 MB on first visit; the browser cache keeps it afterwards)…");
  var t0 = Date.now();
  try { worker = new Worker("engine/worker.js"); }
  catch (e) { setLoad("bad", "Could not start a Web Worker: " + esc(e.message) + ". Open this page through a web server (not file://)."); return; }
  worker.onmessage = function (ev) {
    var m = ev.data;
    if (m.type === "ready") {
      ready = true; $("go").disabled = false;
      setLoad("ok", "Python " + esc(m.python) + " (Pyodide " + esc(m.version) + ") ready in " + ((Date.now() - t0) / 1000).toFixed(1) + " s. Generator loaded: <code>engine/gen_on_instance.py</code>, " + fmt(m.genBytes) + " bytes.");
      if (pending) { var p = pending; pending = null; send(p); }
    } else if (m.type === "fatal") {
      worker.terminate();
      if (++loadFails <= 2) { setLoad("busy", "Pyodide failed to start (" + esc(m.error) + "); retrying…"); setTimeout(startWorker, 1500 * loadFails); return; }
      setLoad("bad", "Pyodide failed to load: " + esc(m.error) + ". The page needs network access to cdn.jsdelivr.net and a few hundred MB of memory; close other heavy tabs and reload.");
    } else if (m.type === "result" && m.id === runId) {
      stopTick(); $("cancel").hidden = true; $("go").disabled = false;
      var res; try { res = JSON.parse(m.json); } catch (e) { res = { ok: false, kind: "JSON", error: String(e) }; }
      res.wallMs = m.ms;
      onResult(res);
    }
  };
  worker.onerror = function (e) { setLoad("bad", "Worker error: " + esc(e.message || "unknown") + "."); };
}
function stopTick() { if (tickTimer) { clearInterval(tickTimer); tickTimer = null; } }
function send(job) {
  runId++; job.id = runId; current = job;
  $("go").disabled = true; $("cancel").hidden = false; tStart = Date.now();
  setLoad("busy", "Running the generator…");
  stopTick();
  tickTimer = setInterval(function () { setLoad("busy", "Running the generator… " + ((Date.now() - tStart) / 1000).toFixed(1) + " s (Layout, Lua, intended play)"); }, 200);
  worker.postMessage({ type: "run", id: runId, instance: { n: job.parsed.n, clauses: job.parsed.clauses } });
}
$("cancel").addEventListener("click", function () {
  stopTick(); runId++; worker.terminate(); $("cancel").hidden = true;
  showErrors(["Cancelled. Python is restarting (the cached download makes this quicker)."], true);
  startWorker();
});

// ------------------------------------------------------------------ input handling
var current = null;
function showErrors(list, soft) {
  var box = $("errors"); box.innerHTML = "";
  if (!list || !list.length) return;
  var d = el("div", { class: soft ? "note" : "err", role: "alert" });
  d.innerHTML = (soft ? "" : "<b>Cannot build a level.</b> ") + (list.length > 1 ? "<ul style='margin:.3rem 0 0;padding-left:1.1rem'>" + list.map(function (x) { return "<li>" + x + "</li>"; }).join("") + "</ul>" : list[0]);
  box.appendChild(d);
}
function generate() {
  var src = $("formula").value, parsed;
  $("parsed").hidden = true;
  try { parsed = parseFormula(src); }
  catch (e) { if (e instanceof ParseError) { showErrors(e.list); $("out").hidden = true; return; } throw e; }
  showErrors([]);
  $("parsed").hidden = false;
  $("parsed").innerHTML = "φ = " + esc(parsed.clauses.map(function (c) { return clauseStr(c); }).join(" ∧ ")) +
    "<br><span style='color:var(--muted)'>n = " + parsed.n + ", m = " + parsed.clauses.length + "; leg orders to search: " + fmt(parsed.orders.pos) + " above, " + fmt(parsed.orders.neg) + " below</span>";
  var job = { src: src, parsed: parsed };
  if (!ready) { pending = job; showErrors(["Queued: generation starts as soon as Python has loaded."], true); return; }
  send(job);
}
$("go").addEventListener("click", generate);
$("formula").addEventListener("keydown", function (e) { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); if (!$("go").disabled || !ready) generate(); } });
PRESETS.forEach(function (p) {
  if (p.grp) { $("presets").appendChild(el("span", { class: "grp" }, p.grp)); return; }
  var b = el("button", { type: "button", "aria-pressed": "false", "data-id": p.id });
  b.textContent = p.id + " · " + p.note;
  b.appendChild(el("small", null, p.f));
  b.addEventListener("click", function () {
    $("formula").value = p.f;
    document.querySelectorAll("#presets button").forEach(function (o) { o.setAttribute("aria-pressed", String(o === b)); });
    generate();
  });
  $("presets").appendChild(b);
});

// ------------------------------------------------------------------ results
var urls = [];
function onResult(res) {
  var job = current;
  if (!res.ok) {
    setLoad("ok", "Generator finished (it rejected the instance).");
    $("out").hidden = true;
    if (/not PMR/.test(res.error))
      showErrors(["The generator found <b>no planar drawing</b>: <code>" + esc(res.error) + "</code>. On that side, every left-to-right order of the clause legs (legs sorted by variable, any order among the legs of one variable) has two clauses X ≠ Y with legs a &lt; b &lt; c &lt; d, a, c ∈ X and b, d ∈ Y (§4.1 P3). Such a formula is not an instance of Planar Monotone Rectilinear 3-SAT, so the reduction does not apply to it."]);
    else
      showErrors(["The generator raised <code>" + esc(res.kind) + "</code>: <code>" + esc(res.error) + "</code>. The input passed this page's checks, so this is an assertion of Lemma 4.1/4.2 failing, i.e. a generator bug. Please report the formula." + (res.trace ? "<pre>" + esc(res.trace) + "</pre>" : "")]);
    return;
  }
  setLoad("ok", "Level generated in " + (res.wallMs / 1000).toFixed(2) + " s (Layout " + res.time_layout + " s; Lua, stats and intended play " + res.time_play + " s).");
  var parsed = job.parsed;
  var bf = bruteSAT(parsed.n, parsed.clauses);
  res.bf = bf; res.parsed = parsed;
  $("out").hidden = false;
  renderDrawing(res);
  renderVerdict(res);
  loadLevel(res);
  renderStats(res);
  renderDownloads(res);
}

// ---- a. drawing
function renderDrawing(res) {
  var n = res.n, names = res.var_names, cl = res.clauses, alpha = res.alpha;
  var LEG = 62, PAD = 24, BOXH = 26, PITCH = 40, RH = 22, LM = 44, GAP = 26;
  var cnt = { pos: {}, neg: {} }, maxLev = { pos: 0, neg: 0 }, legX = {}, legsOf = { pos: {}, neg: {} };
  ["pos", "neg"].forEach(function (s) {
    res.sides[s].seq.forEach(function (p) { cnt[s][p[0]] = (cnt[s][p[0]] || 0) + 1; });
    Object.keys(res.sides[s].level).forEach(function (k) { maxLev[s] = Math.max(maxLev[s], res.sides[s].level[k]); });
  });
  var vx0 = {}, vw = {}, kmax = {}, x = LM;
  for (var v = 1; v <= n; v++) {
    kmax[v] = Math.max(cnt.pos[v] || 0, cnt.neg[v] || 0, 1);
    vw[v] = (kmax[v] - 1) * LEG + 2 * PAD; vx0[v] = x; x += vw[v] + GAP;
  }
  var W = x - GAP + 12;
  var axis = 12 + maxLev.pos * PITCH + BOXH / 2 + (maxLev.pos ? 0 : 8);
  var H = axis + BOXH / 2 + maxLev.neg * PITCH + 12 + (maxLev.neg ? 0 : 8);
  ["pos", "neg"].forEach(function (s) {
    var seen = {};
    res.sides[s].seq.forEach(function (p) {
      var v = p[0], i = p[1], j = seen[v] = (seen[v] || 0), k = cnt[s][v];
      seen[v]++;
      var lx = vx0[v] + PAD + j * LEG + (kmax[v] - k) * LEG / 2;
      (legsOf[s][i] = legsOf[s][i] || []).push({ v: v, x: lx });
    });
  });
  var chosen = {};
  if (alpha) res.chain.forEach(function (c) {
    var s = c[0], i = c[1], legs = legsOf[s][i];
    for (var k = 0; k < legs.length; k++) if (alpha[legs[k].v - 1] === (s === "pos")) { chosen[i] = k; break; }
  });
  var out = [];
  out.push('<svg xmlns="http://www.w3.org/2000/svg" width="' + W + '" height="' + H + '" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="Planar monotone drawing of the formula">');
  out.push('<line x1="' + (LM - 8) + '" y1="' + axis + '" x2="' + (W - 4) + '" y2="' + axis + '" style="stroke:var(--rule);stroke-width:1.5"/>');
  if (maxLev.pos) out.push('<text x="4" y="' + (axis - BOXH / 2 - 6) + '" style="fill:var(--muted);font-size:11px">+ side</text>');
  if (maxLev.neg) out.push('<text x="4" y="' + (axis + BOXH / 2 + 15) + '" style="fill:var(--muted);font-size:11px">− side</text>');
  ["pos", "neg"].forEach(function (s) {
    Object.keys(legsOf[s]).forEach(function (key) {
      var i = +key, legs = legsOf[s][i], lev = res.sides[s].level[key];
      var x0 = legs[0].x - 16, x1 = legs[legs.length - 1].x + 16, w = x1 - x0;
      var top = s === "pos" ? axis - BOXH / 2 - lev * PITCH : axis + BOXH / 2 + lev * PITCH - RH;
      legs.forEach(function (lg, k) {
        var y1 = s === "pos" ? top + RH : axis + BOXH / 2, y2 = s === "pos" ? axis - BOXH / 2 : top;
        var tr = alpha ? (alpha[lg.v - 1] === (s === "pos")) : null;
        var st = tr === null ? "stroke:var(--ink);stroke-width:1.6" : tr ? "stroke:var(--ok);stroke-width:" + (chosen[i] === k ? 4 : 1.8) : "stroke:var(--muted);stroke-width:1.4;stroke-dasharray:4 3";
        out.push('<line x1="' + lg.x + '" y1="' + y1 + '" x2="' + lg.x + '" y2="' + y2 + '" style="' + st + '"/>');
      });
      var full = clauseStr(sortedC(cl[i]), names), cw = full.length * 7 + 10;
      var label = cw <= w ? full : "C" + (i + 1);
      out.push('<g><title>C' + (i + 1) + " = " + esc(full) + " · " + (s === "pos" ? "positive" : "negative") + " side · nesting level " + lev + '</title>');
      out.push('<rect x="' + x0 + '" y="' + top + '" width="' + w + '" height="' + RH + '" rx="2" style="fill:var(--paper);stroke:var(--accent);stroke-width:1.4"/>');
      out.push('<text x="' + (x0 + w / 2) + '" y="' + (top + RH / 2 + 4) + '" text-anchor="middle" style="fill:var(--ink);font-size:12px">' + esc(label) + '</text></g>');
    });
  });
  for (var v2 = 1; v2 <= n; v2++) {
    var val = alpha ? alpha[v2 - 1] : null;
    var stroke = val === null ? "var(--ink)" : val ? "var(--ok)" : "var(--bad)";
    out.push('<g><title>x' + names[v2 - 1] + (val === null ? "" : " = " + (val ? "true" : "false") + " in the generator's assignment") + '</title><rect x="' + vx0[v2] + '" y="' + (axis - BOXH / 2) + '" width="' + vw[v2] + '" height="' + BOXH + '" rx="3" style="fill:var(--sheet);stroke:' + stroke + ';stroke-width:1.6"/>');
    out.push('<text x="' + (vx0[v2] + vw[v2] / 2) + '" y="' + (axis + 4) + '" text-anchor="middle" style="fill:var(--ink);font-size:12.5px;font-weight:600">x' + names[v2 - 1] + (val === null ? "" : val ? "=1" : "=0") + '</text></g>');
  }
  out.push("</svg>");
  var scale = W < 640 ? Math.min(1.5, 640 / W) : 1;
  out[0] = out[0].replace('width="' + W + '" height="' + H + '"', 'width="' + Math.round(W * scale) + '" height="' + Math.round(H * scale) + '"');
  $("drawing").innerHTML = out.join("");
  var dropped = [];
  for (var u = 1; u <= res.parsed.n; u++) if (names.indexOf(u) < 0) dropped.push("x" + u);
  var order = function (s) { return res.sides[s].pre.map(function (i) { return "C" + (i + 1); }).join(", ") || "none"; };
  $("capA").innerHTML = "Variables sit on a horizontal line, left to right. Each clause is an E-shape: a bar above the line (all-positive clause) or below it (all-negative), with one vertical <i>leg</i> to each of its variables. The generator found this drawing by brute force. Among all leg orders whose clause partition is non-crossing (§4.1 P3), it takes the one with the least nesting (sum of levels, then maximum level). " +
    "A bar's height is the clause's <i>nesting level</i> ℓ (1 for a clause with no clause nested between its legs). In the level, ℓ fixes how far the clause gadget sits from the main line: Λ = 7 tile rows per level (§4.3). Clause numbers C1…C" + cl.length + " follow the generator's canonical order (clauses sorted). Pre-order: " + order("pos") + " above, " + order("neg") + " below. The K chain visits the negative side first, then the positive side: " + res.chain.map(function (c) { return "C" + (c[1] + 1); }).join(" → ") + " → G." +
    (alpha ? " Colours show the generator's satisfying assignment: green legs are true literals and dashed legs are false. The thick leg in each clause is the path the intended play takes (the first true leg, left to right)." : " The formula is unsatisfiable, so no assignment is shown.") +
    (dropped.length ? " <b>Deleted by the generator</b> (they occur in no clause): " + dropped.join(", ") + "." : "");
}

// ---- b. verdict
function renderVerdict(res) {
  var bf = res.bf, sat = bf.count > 0, names = res.var_names, pn = res.parsed.n;
  var gen = !!res.alpha;
  var asg = sat ? bf.first.map(function (b, i) { return "x" + (i + 1) + "=" + (b ? 1 : 0); }).join(" ") : "none";
  var agree = sat === gen;
  var genAsg = gen ? names.map(function (v, k) { return "x" + v + "=" + (res.alpha[k] ? 1 : 0); }).join(" ") : "none";
  $("verdict").innerHTML =
    '<div class="vbox"><div class="k">φ is</div><div class="v ' + (sat ? "ok" : "bad") + '">' + (sat ? "satisfiable" : "unsatisfiable") + '</div><div class="assign">' + fmt(bf.count) + " of " + fmt(bf.total) + " assignments satisfy φ</div></div>" +
    '<div class="vbox"><div class="k">first satisfying assignment</div><div class="v assign" style="font-size:1rem">' + esc(asg) + "</div></div>" +
    '<div class="vbox"><div class="k">expected answer for this level</div><div class="v ' + (sat ? "ok" : "bad") + '">' + (sat ? "G reachable" : "G not reachable") + "</div><div class=\"assign\">" + (sat ? "by completeness, §5.1" : "by soundness, §5.2") + "</div></div>";
  $("capB").innerHTML = "This page checks all 2<sup>" + pn + "</sup> assignments of x1…x" + pn + " in JavaScript, separately from the Python generator. The generator runs its own search (<code>satisfying</code>, same enumeration order) on the " + res.n + " variables left after deleting unused ones. Its result: <code>" + esc(genAsg) + "</code>. " +
    (agree ? "The two agree." : "<b style='color:var(--bad)'>The two disagree. This should be impossible; please report it.</b>") + " " +
    (sat ? "The reduction claims G is reachable. The generator has already confirmed one witness: it replays the intended play of §5.1 under this assignment cell by cell with the exact movement rules, asserts that it ends on G, and returns the move string you can watch in panel c." :
      "The reduction claims that no sequence of moves reaches G, under any RNG outcome (Theorem, soundness direction). No solution is shown. If you find a route anyway, the page records your moves.");
}

// ---- d. stats
function renderStats(res) {
  var st = res.stats, m = res.clauses.length, n = res.n;
  var L = res.clauses.reduce(function (a, c) { return a + c.length; }, 0), X = st.crossovers, F = st.floor_cells;
  var rows = [
    ["Map width w (cells)", st.width, "11·W<sub>t</sub> ≤ 132m + 22n + 44", 132 * m + 22 * n + 44, "le"],
    ["Map height h (cells)", st.height, "11·H<sub>t</sub> ≤ 77m + 77", 77 * m + 77, "le"],
    ["Tile columns W<sub>t</sub>", st.tiles_w, "≤ 12m + 2n + 4", 12 * m + 2 * n + 4, "le"],
    ["Tile rows H<sub>t</sub>", st.tiles_h, "≤ 7m + 7", 7 * m + 7, "le"],
    ["Floor cells F", F, "≤ 37·W<sub>t</sub>·H<sub>t</sub> (G_X has the most floor, 37)", 37 * st.tiles_w * st.tiles_h, "le"],
    ["Crossovers #X (G_X tiles)", X, "≤ 1 + 2L(m + 4), L = " + L + " legs", 1 + 2 * L * (m + 4), "le"],
    ["", "", "≤ 6m² + 24m + 1", 6 * m * m + 24 * m + 1, "le"],
    ["Holes", st.holes, "= #X (one hole s1 per crossover)", X, "eq"],
    ["Closing sites (G_C)", st.closing_sites, "= L (one per leg)", L, "eq"],
    ["One-way doors (G_D)", st.doors, "= L (one per leg)", L, "eq"],
    ["Boulders", st.boulders, "= 2L + 2·#X (W, Kd per leg; δ, τ per crossover)", 2 * L + 2 * X, "eq"],
    ["", "", "≤ 12m² + 54m + 2", 12 * m * m + 54 * m + 2, "le"],
    ["Fortune cookies", st.cookies, "= F − #X − 2 (every floor cell except holes, pit, stair pocket)", F - X - 2, "eq"],
    ["Intended play length (turns)", st.solution_moves, "≤ 4F (§4.6)", 4 * F, "le"],
    ["Lowest hunger on that play", st.min_hunger, "> 0 (starts at 900; a cookie is eaten when ≤ 860)", 0, "gt"],
    ["Most visits to one cell", st.max_visits, "≤ 2 (§5.1: only crossover centres S are re-entered)", 2, "le"],
    ["Longest run between cookie cells", st.max_moves_without_cookie, "informational (every floor cell holds a cookie)", null, ""]
  ];
  var h = "<thead><tr><th>Quantity</th><th style='text-align:right'>this level</th><th>bound (§4.6, n = " + n + ", m = " + m + ")</th><th style='text-align:right'>value</th><th></th></tr></thead><tbody>";
  rows.forEach(function (r) {
    var val = r[1], b = r[3], ok = null;
    if (val != null && val !== "" && b != null) ok = r[4] === "le" ? val <= b : r[4] === "eq" ? val === b : r[4] === "gt" ? val > b : null;
    if (val == null && r[0]) { val = "—"; ok = null; }
    h += "<tr><td>" + r[0] + "</td><td class='num'>" + (val === "" ? "" : fmt(val)) + "</td><td class='f'>" + r[2] + "</td><td class='num'>" + (b == null ? "" : fmt(b)) + "</td><td>" + (ok === null ? "" : ok ? "<span class='hold'>holds</span>" : "<span class='fail'>FAILS</span>") + "</td></tr>";
  });
  $("stats").innerHTML = h + "</tbody>";
  $("capD").innerHTML = "Left: the numbers <code>Layout.stats()</code> and the intended-play simulator report for this level. Right: the explicit polynomials of §4.6 and the identities of §4.5, evaluated at n = " + n + " (variables that occur in some clause; the input's n = " + res.parsed.n + " only makes the bounds looser) and m = " + m + ". " +
    (res.alpha ? "The last rows come from the generator replaying the intended play with its hunger model (900 start, one cookie when hunger ≤ 860, 2 turns per meal)." : "The intended-play rows are empty because φ is unsatisfiable.") +
    " Map size grows as O(n + m) by O(m) cells. Crossovers and boulders grow as O(m²). The level has polynomial size, as a Karp reduction needs.";
}

// ---- e. downloads
function renderDownloads(res) {
  urls.forEach(function (u) { URL.revokeObjectURL(u); }); urls = [];
  var tag = res.parsed.clauses.map(function (c) { return c.join("_"); }).join("__").replace(/-/g, "n").slice(0, 60);
  var files = [["level-" + tag + ".lua", res.lua, "Lua level (" + fmt(res.lua.length) + " bytes)"],
               ["level-" + tag + ".txt", res.ascii + "\n", "ASCII board"],
               ["instance-" + tag + ".json", JSON.stringify({ n: res.parsed.n, clauses: res.parsed.clauses }) + "\n", "instance JSON (generator input)"]];
  if (res.moves) files.push(["moves-" + tag + ".txt", res.moves + "\n", "intended move string"]);
  var box = $("dl"); box.innerHTML = "";
  files.forEach(function (f) {
    var u = URL.createObjectURL(new Blob([f[1]], { type: "text/plain" })); urls.push(u);
    box.appendChild(el("a", { href: u, download: f[0] }, f[2]));
  });
  $("luaText").value = res.lua;
  var nl = res.lua.split("\n").length - 1;
  $("capE").innerHTML = "The script <code>lua()</code> emits (" + fmt(nl) + " lines). It is the level for NetHack 3.7's level compiler, restricted to the phase-2 whitelist. It does the following:" +
    " turns off random monster generation; empties the hero's inventory; sets the flags <code>noflip</code>, <code>sokoban</code> (Sokoban boulder rules, no diagonal squeezing) and <code>noteleport</code>; fills the level with stone; draws one <code>des.map</code> of floor (" + res.stats.width + "×" + res.stats.height + ", so it needs the generalized COLNO/ROWNO, not the stock 80×21); makes walls undiggable and non-passable;" +
    " places one boulder per <code>0</code>, one hole trap per crossover and the sentinel pit, and one fortune cookie on every other floor cell (the food that makes hunger faithful, §1.3); puts the DL1 branch stair in a sealed pocket; pins the arrival region to the start cell; and gives the hero a cursed loadstone (the 'heavy hero' of §1.1, who cannot squeeze past boulders). The last comment line gives the target cell g." +
    " The ASCII board is <code>Layout.ascii()</code>: <code>.</code> floor, <code>0</code> boulder, <code>^</code> hole, <code>p</code> pit, <code>b</code> stair pocket, <code>@</code> start, <code>G</code> goal.";
}

// ------------------------------------------------------------------ viewer (rules as in arena.src.html)
var TILE_URI = {}, IMG = {};
fetch("engine/tiles.json").then(function (r) { return r.json(); }).then(function (t) {
  TILE_URI = t;
  Object.keys(t).forEach(function (k) { var i = new Image(); i.onload = function () { draw(); }; i.src = t[k]; IMG[k] = i; });
}).catch(function () { tiles = false; });
var DIRS = { h: [-1, 0], j: [0, 1], k: [0, -1], l: [1, 0], y: [-1, -1], u: [1, -1], b: [-1, 1], n: [1, 1] };
var ARROWS = { ArrowLeft: "h", ArrowDown: "j", ArrowUp: "k", ArrowRight: "l", Home: "y", PageUp: "u", End: "b", PageDown: "n" };
var ROLE = {
  m: ["#5b9bd5", "P · main line"],
  f: ["#9fd3ff", "P · fork / join of a variable"],
  F: ["#e07a5f", "P · branch F (above the line): walking it sets the variable false and closes the paths of its positive literal"],
  T: ["#5fc48f", "P · branch T (below the line): walking it sets the variable true and closes the paths of its negative literal"],
  k: ["#c58cf0", "K · clause gadget: hub column, entry rows, forward row"],
  a: ["#8a7fd6", "K · chain arc (main line → first clause, clause → clause, last clause → G)"],
  c: ["#f2cf4a", "G_C closing site · P part (T-lane through N, U-turn)"],
  q: ["#f2cf4a", "G_C closing site · K part (back segment, Q, C)"],
  d: ["#f08fb0", "G_D one-way door (on the clause path)"],
  x: ["#46c7c7", "G_X crossover · P lane through S"],
  y: ["#46c7c7", "G_X crossover · K part (δ, τ, hole s1)"],
  s: ["#7d8a91", "sentinel pit / sealed stair pocket (never reachable)"],
  "@": ["#ffffff", "start s0"],
  G: ["#f2cf4a", "goal g"]
};
var RGB = {}; Object.keys(ROLE).forEach(function (k) { var h = ROLE[k][0]; RGB[k] = [parseInt(h.substr(1, 2), 16), parseInt(h.substr(3, 2), 16), parseInt(h.substr(5, 2), 16)]; });
var LEGEND = [["m", "main line (P)"], ["f", "fork / join (P)"], ["F", "branch F: x false (P)"], ["T", "branch T: x true (P)"], ["k", "clause paths (K)"], ["a", "chain arcs (K)"], ["c", "closing site G_C"], ["d", "one-way door G_D"], ["x", "crossover G_X"], ["s", "sentinel"]];
var LABN = {
  X: { kin: "k: K entry cell, δ is pushed from here", n2: "n2: holds δ", n1: "n1: holds the token τ", S: "S: crossover centre, shared by P and K", pocket: "p: δ's pocket", s1: "s1: hole, plugged by τ on the K pass" },
  Cl: { Q: "Q: once W is pushed here, σ is closed", N: "N: holds the boulder W", T: "T: the P branch pushes W from here", C: "C: corner of the forward part" },
  door: { e: "e: entry side, Kd is pushed from here", X: "X: holds the door boulder Kd", pocket: "pocket: where Kd goes when the door opens" }
};
var view = $("view"), vx = view.getContext("2d"), mini = $("mini"), mx = mini.getContext("2d");
var R, W, H, solid, wallK, boulders, holes, hero, goal, visited, hist, log, turns, pushes, dead, won, tiles = true, zoom = 1, autoTimer = null, overlay = false, look = null, roleAt, tileInfo, labAt, last = {};
function idx(x, y) { return y * W + x; }
function inb(x, y) { return x >= 0 && y >= 0 && x < W && y < H; }
function isSolid(x, y) { return !inb(x, y) || solid[idx(x, y)]; }
function wallKeyAt(x, y) {
  function nearFloor(a, b) { for (var i = -1; i <= 1; i++) for (var j = -1; j <= 1; j++) { if ((i || j) && !isSolid(a + i, b + j)) return true; } return false; }
  if (!nearFloor(x, y)) return "";
  function w(a, b) { return isSolid(a, b) && inb(a, b) && nearFloor(a, b); }
  var N = w(x, y - 1), S = w(x, y + 1), E = w(x + 1, y), Wd = w(x - 1, y), n = N + S + E + Wd;
  if (n === 4) return "cross"; if (n === 3) return !N ? "td" : !S ? "tu" : !E ? "tlw" : "trw";
  if (N && S) return "v"; if (E && Wd) return "h";
  if (S && E) return "tl"; if (S && Wd) return "tr"; if (N && E) return "bl"; if (N && Wd) return "br";
  return (N || S) ? "v" : "h";
}
function loadLevel(res) {
  stopAuto(); R = res;
  var lines = res.ascii.split("\n");
  W = res.stats.width; H = res.stats.height;
  solid = new Uint8Array(W * H); boulders = new Uint8Array(W * H); holes = new Uint8Array(W * H); visited = new Uint8Array(W * H);
  var glyph = new Array(W * H); roleAt = new Array(W * H);
  for (var y = 0; y < H; y++) for (var x = 0; x < W; x++) {
    var ch = (lines[y] || "")[x] || " ", k = idx(x, y); glyph[k] = ch;
    roleAt[k] = (res.roles[y] || "")[x] || " ";
    if (ch === " " || ch === "p" || ch === "b") solid[k] = 1;
    if (ch === "0") boulders[k] = 1;
    if (ch === "^") holes[k] = 1;
    if (ch === "@") hero = [x, y];
    if (ch === "G") goal = [x, y];
  }
  wallK = new Array(W * H);
  for (var y2 = 0; y2 < H; y2++) for (var x2 = 0; x2 < W; x2++) { var k2 = idx(x2, y2); if (solid[k2]) wallK[k2] = glyph[k2] === "p" ? "pit" : glyph[k2] === "b" ? "stairs" : wallKeyAt(x2, y2); }
  tileInfo = {}; res.tiles.forEach(function (t) { tileInfo[t.c + "," + t.r] = t; });
  labAt = {}; res.labels.forEach(function (l) { labAt[l[0] + "," + l[1]] = l; });
  res.start0 = hero.slice();
  resetPlay();
  mini.width = W; mini.height = H;
  $("auto").hidden = !res.moves;
  renderLegend();
  var sat = res.bf.count > 0;
  $("capC").innerHTML = "The real level, " + W + " × " + H + " cells, on a grid of " + res.stats.tiles_w + " × " + res.stats.tiles_h + " tiles of 11 × 11 cells (§4.2). Tiles touch only at the midpoints of their sides (Lemma 4.1). You start at <b>@</b> on the left end of the <i>main line</i> (P territory). At each variable the line forks into a branch F (up, x = false) and a branch T (down, x = true). Every leg of a clause on that branch's side ends in a <i>closing site</i> G_C. Walking the branch forces you to push its boulder W into Q, which closes that literal's clause path for good. After the last variable the main line passes into K territory: the chain visits every clause gadget. Each gadget has one path per literal. A path is entered through a one-way door G_D, ends at its closing site, and must be open to get through. Wherever a K path crosses a P lane there is a one-shot crossover G_X (boulders δ, τ and a hole). G is reached only after passing every clause. " +
    "<b>Show structure</b> colours every floor cell by the role the generator gave it. The colours come from the generator's own tile table (<code>Layout.tile</code>, <code>occ</code>, <code>arcs</code>, <code>lab</code>), not from a separate model. Point at a cell to read its role, its tile, and which clause or variable it belongs to." +
    (sat ? " <b>Show solution</b> replays the move string the generator verified (§5.1 intended play; the eat commands <code>E</code> are skipped because the viewer ignores hunger)." : " φ is unsatisfiable, so there is no solution to show.");
  $("capC2").innerHTML = "<b>Movement rules (§2, the same as the arena).</b> You step to any of 8 neighbours. You push a boulder by moving orthogonally into it when the cell behind it is free floor. There are no diagonal pushes, and you cannot move diagonally between two blocked cells (Sokoban rule plus the loadstone). A boulder pushed into a hole plugs it and leaves floor. Stepping into an unplugged hole drops you off the level, which counts as a loss here (Undo is allowed). This viewer ignores hunger. That only gives the player more power, so a route to G on an unsatisfiable formula found here would still be a counterexample to the reduction's soundness, provided it also replays in NetHack.";
  fit();
  say(sat ? "φ is satisfiable: G should be reachable. Walk right from @ along the main line." : "φ is unsatisfiable: the proof says G cannot be reached.");
}
function resetPlay() {
  stopAuto();
  var lines = R.ascii.split("\n");
  boulders = new Uint8Array(W * H); holes = new Uint8Array(W * H); visited = new Uint8Array(W * H);
  for (var y = 0; y < H; y++) for (var x = 0; x < W; x++) { var ch = (lines[y] || "")[x]; if (ch === "0") boulders[idx(x, y)] = 1; if (ch === "^") holes[idx(x, y)] = 1; }
  hero = R.start0.slice(); hist = []; log = []; turns = 1; pushes = 0; dead = false; won = false; look = null;
  visited[idx(hero[0], hero[1])] = 1; $("wonbox").innerHTML = "";
}
function renderLegend() {
  var lg = $("legend"); lg.innerHTML = "";
  if (!overlay) {
    lg.innerHTML = '<span><i style="background:#fff"></i>you @</span><span><i style="background:#f2cf4a"></i>goal G</span><span><i style="background:#f0a35e"></i>boulder</span><span><i style="background:#c78bf0"></i>hole</span><span><i style="background:#4c7a86"></i>visited</span>';
    return;
  }
  LEGEND.forEach(function (e) { var s = el("span"); var i = el("i"); i.style.background = ROLE[e[0]][0]; s.appendChild(i); s.appendChild(document.createTextNode(e[1])); lg.appendChild(s); });
}
// Undo records only what a move changes (hero, and for a push the two cells' boulder/hole bits): full-array
// snapshots cost W*H bytes per move, which on an m = 8 level (~6*10^5 cells, ~1.5*10^4 moves) exhausts memory.
function snap(cells) { var ch = []; (cells || []).forEach(function (k) { ch.push([k, boulders[k], holes[k]]); }); return { hero: hero.slice(), ch: ch, turns: turns, pushes: pushes, dead: dead, won: won, n: log.length }; }
function undo() { stopAuto(); var s = hist.pop(); if (!s) return; hero = s.hero; for (var i = s.ch.length - 1; i >= 0; i--) { boulders[s.ch[i][0]] = s.ch[i][1]; holes[s.ch[i][0]] = s.ch[i][2]; } turns = s.turns; pushes = s.pushes; dead = s.dead; won = s.won; log.length = s.n; look = null; $("wonbox").innerHTML = ""; say("Undone."); draw(); }
function bad(x, y) { return isSolid(x, y) || boulders[idx(x, y)]; }
function say(m) { $("msg").textContent = m; }
function move(key, quiet, nodraw) {
  if (dead || won) { if (!quiet) say(dead ? "You fell through a hole. Undo or reset." : "You already reached G."); return false; }
  look = null;
  if (key === ".") { hist.push(snap()); turns++; log.push("."); if (!nodraw) draw(); return true; }
  var d = DIRS[key]; if (!d) return false;
  var ux = hero[0], uy = hero[1], dx = d[0], dy = d[1], x = ux + dx, y = uy + dy, diag = dx && dy, k = idx(x, y);
  if (isSolid(x, y)) return false;
  if (diag && bad(ux, y) && bad(x, uy)) { if (!quiet) say("You cannot pass that way."); return false; }
  if (boulders[k]) {
    var rx = x + dx, ry = y + dy, rk = idx(rx, ry);
    if (isSolid(rx, ry) || boulders[rk]) { if (!quiet) say("You try to move the boulder, but in vain."); return false; }
    if (diag) { if (!quiet) say("The boulder won't roll diagonally on this floor."); return false; }
    hist.push(snap([k, rk])); boulders[k] = 0; pushes++;
    if (holes[rk]) { holes[rk] = 0; if (!quiet) say("The boulder falls into and plugs a hole in the floor!"); }
    else { boulders[rk] = 1; if (!quiet) say("With great effort you move the boulder."); }
  } else {
    hist.push(snap()); if (!quiet) say("");
  }
  hero = [x, y]; turns++; visited[k] = 1; log.push(key);
  if (holes[k]) { dead = true; say("There's a gaping hole under you! You fall through… (you left the level, which counts as a loss; Undo to go back)"); }
  else if (x === goal[0] && y === goal[1]) { won = true; onWin(); }
  if (!nodraw) draw(); return true;
}
function onWin() {
  var sat = R.bf.count > 0, box = $("wonbox"), mv = log.join("");
  box.innerHTML = "";
  var d = el("div", { class: sat ? "won good" : "won", role: "alert" });
  if (sat) {
    say("You reached G.");
    d.innerHTML = "<b>G reached.</b> This is consistent with completeness: φ is satisfiable. Your move list (" + log.length + " moves):";
  } else {
    say("You reached G on an UNSAT formula.");
    d.innerHTML = "<b>You reached G, but φ is unsatisfiable. This contradicts the Theorem (soundness, §5.2). Please report the formula and the move list below.</b> (" + log.length + " moves; vi-keys, <code>.</code> = wait)";
  }
  var ta = el("textarea", { readonly: "", "aria-label": "Move list" }); ta.value = (sat ? "" : "formula: " + $("formula").value.trim() + "\nmoves: ") + mv;
  d.appendChild(ta); box.appendChild(d);
}
function run(key) {
  for (var i = 0; i < 400; i++) {
    var before = pushes; if (!move(key, true, true)) break; if (pushes !== before || dead || won) break;
    var x = hero[0], y = hero[1], open = 0; for (var dd in DIRS) { if (DIRS[dd][0] && DIRS[dd][1]) continue; if (!isSolid(x + DIRS[dd][0], y + DIRS[dd][1])) open++; }
    if (open > 2) break;
  }
  draw();
}
var CELL = 24, ZOOMS = [1, 0.5, 0.25, 0.125];
function viewDims() { var c = Math.max(2, Math.round(CELL * zoom)); return { c: c, cols: Math.floor(view.width / c), rows: Math.floor(view.height / c) }; }
var TXT = { floor: "#5c6970", wall: "#93a8b3", boulder: "#f0a35e", hole: "#c78bf0", hero: "#ffffff", goal: "#f2cf4a" };
function textWall(x, y) { var k = wallK[idx(x, y)]; if (!k) return ""; if (k === "pit") return "^"; if (k === "stairs") return "<"; return (k === "v" || k === "tlw" || k === "trw") ? "|" : "-"; }
function draw() {
  if (!R) return;
  var v = viewDims(), c = v.c, ctr = look || hero;
  var ox = Math.max(0, Math.min(W - v.cols, ctr[0] - (v.cols >> 1))), oy = Math.max(0, Math.min(H - v.rows, ctr[1] - (v.rows >> 1)));
  last = { ox: ox, oy: oy, c: c };
  vx.fillStyle = "#000"; vx.fillRect(0, 0, view.width, view.height); vx.imageSmoothingEnabled = false;
  vx.font = Math.round(c * 0.95) + "px VT323, monospace"; vx.textAlign = "center"; vx.textBaseline = "middle";
  var useTiles = tiles && c >= 6;
  for (var j = 0; j <= v.rows; j++) for (var i = 0; i <= v.cols; i++) {
    var x = ox + i, y = oy + j; if (!inb(x, y)) continue; var k = idx(x, y), px = i * c, py = j * c, t, col, ch;
    if (solid[k]) { t = wallK[k]; ch = textWall(x, y); col = t === "pit" ? TXT.hole : TXT.wall; }
    else if (x === hero[0] && y === hero[1]) { t = "hero"; ch = "@"; col = TXT.hero; }
    else if (boulders[k]) { t = "boulder"; ch = "0"; col = TXT.boulder; }
    else if (holes[k]) { t = "hole"; ch = "^"; col = TXT.hole; }
    else if (x === goal[0] && y === goal[1]) { t = "goal"; ch = "G"; col = TXT.goal; }
    else { t = "floor"; ch = "."; col = TXT.floor; }
    if (useTiles) { if (t && IMG[t] && IMG[t].complete) { if (t === "hero" || t === "boulder" || t === "goal") vx.drawImage(IMG.floor, px, py, c, c); vx.drawImage(IMG[t], px, py, c, c); } }
    else if (c < 6) { if (!solid[k] || t) { vx.fillStyle = solid[k] ? "#2a3237" : col; vx.fillRect(px, py, c, c); } }
    else if (ch) { vx.fillStyle = col; vx.fillText(ch, px + c / 2, py + c / 2 + 1); }
    if (overlay && !solid[k]) { var ro = ROLE[roleAt[k]]; if (ro) { vx.globalAlpha = (t === "floor") ? 0.5 : 0.3; vx.fillStyle = ro[0]; vx.fillRect(px, py, c, c); vx.globalAlpha = 1; } }
    if (x === goal[0] && y === goal[1]) { vx.strokeStyle = TXT.goal; vx.lineWidth = 2; vx.strokeRect(px + 1, py + 1, c - 2, c - 2); }
  }
  if (overlay) {   // tile boundaries
    vx.strokeStyle = "rgba(255,255,255,.16)"; vx.lineWidth = 1; vx.beginPath();
    for (var gx = Math.ceil(ox / 11) * 11; gx <= ox + v.cols + 1; gx += 11) { var X = (gx - ox) * c + .5; vx.moveTo(X, 0); vx.lineTo(X, view.height); }
    for (var gy = Math.ceil(oy / 11) * 11; gy <= oy + v.rows + 1; gy += 11) { var Y = (gy - oy) * c + .5; vx.moveTo(0, Y); vx.lineTo(view.width, Y); }
    vx.stroke();
  }
  var img = mx.createImageData(W, H), d = img.data;
  for (var p = 0; p < W * H; p++) {
    var r = 0, g = 0, b = 0;
    if (!solid[p]) {
      if (overlay && RGB[roleAt[p]]) { var rgb = RGB[roleAt[p]]; r = rgb[0]; g = rgb[1]; b = rgb[2]; if (visited[p]) { r = r * .6 + 102; g = g * .6 + 102; b = b * .6 + 102; } }
      else { r = 48; g = 58; b = 64; if (visited[p]) { r = 76; g = 122; b = 134; } }
    } else if (wallK[p]) { r = 24; g = 30; b = 34; }
    if (boulders[p]) { r = 240; g = 163; b = 94; } if (holes[p]) { r = 199; g = 139; b = 240; }
    d[p * 4] = r; d[p * 4 + 1] = g; d[p * 4 + 2] = b; d[p * 4 + 3] = 255;
  }
  mx.putImageData(img, 0, 0);
  var rad = Math.max(3, W / 90);
  mx.fillStyle = "#f2cf4a"; mx.beginPath(); mx.arc(goal[0] + .5, goal[1] + .5, rad, 0, 7); mx.fill();
  mx.fillStyle = "#fff"; mx.beginPath(); mx.arc(hero[0] + .5, hero[1] + .5, rad, 0, 7); mx.fill();
  mx.strokeStyle = "rgba(255,255,255,.7)"; mx.lineWidth = Math.max(1, W / 300); mx.strokeRect(ox, oy, v.cols, v.rows);
  $("stat").textContent = "T:" + turns + "  pushes:" + pushes + "  moves:" + log.length + "  @ " + hero[0] + "," + hero[1] + (dead ? "  FELL" : won ? "  ON G" : "");
}
function describe(x, y) {
  if (!inb(x, y)) return "";
  var k = idx(x, y), tc = Math.floor(x / 11), tr = Math.floor(y / 11), ti = tileInfo[tc + "," + tr];
  var s = "cell (" + x + ", " + y + ") · tile (" + tc + ", " + tr + ")";
  if (solid[k]) return s + (wallK[k] === "pit" ? " · sentinel pit (sealed)" : wallK[k] === "stairs" ? " · sealed pocket for the DL1 branch stair" : " · stone");
  var ro = ROLE[roleAt[k]]; if (ro) s += " · " + ro[1];
  if (ti) {
    if (ti.clause != null) { var c = R.clauses[ti.clause]; s += " · clause C" + (ti.clause + 1) + " = " + clauseStr(sortedC(c), R.var_names) + ", leg " + (ti.leg + 1) + " (literal " + (ti.side === "pos" ? "" : "¬") + "x" + ti.var + ")"; }
    else if (ti.var != null) s += " · variable x" + ti.var;
  }
  var lb = labAt[x + "," + y]; if (lb && LABN[lb[3]] && LABN[lb[3]][lb[2]]) s += " · " + LABN[lb[3]][lb[2]];
  if (boulders[k]) s += " · boulder"; if (holes[k]) s += " · hole";
  return s;
}
function evCell(ev, cv) {   // canvas pixel under the pointer (content box: borders excluded)
  var r = cv.getBoundingClientRect(), sx = r.width / cv.offsetWidth || 1, sy = r.height / cv.offsetHeight || 1;
  return [(ev.clientX - r.left - cv.clientLeft * sx) * cv.width / (cv.clientWidth * sx), (ev.clientY - r.top - cv.clientTop * sy) * cv.height / (cv.clientHeight * sy)];
}
view.addEventListener("mousemove", function (ev) { if (!R) return; var p = evCell(ev, view); $("hover").textContent = describe(last.ox + Math.floor(p[0] / last.c), last.oy + Math.floor(p[1] / last.c)); });
mini.addEventListener("click", function (ev) { if (!R) return; var p = evCell(ev, mini); look = [Math.floor(p[0]), Math.floor(p[1])]; $("hover").textContent = describe(look[0], look[1]); draw(); });
function stopAuto() { if (autoTimer) { clearInterval(autoTimer); autoTimer = null; $("auto").textContent = "Show solution"; } }
$("auto").addEventListener("click", function () {
  if (autoTimer) { stopAuto(); return; }
  resetPlay(); draw();
  var seq = R.moves.replace(/E/g, ""), i = 0, t0 = performance.now(), dur = Math.min(15000, Math.max(4000, seq.length * 12));
  this.textContent = "Stop";
  say("Replaying the generator's intended play (" + seq.length + " moves, about " + Math.round(dur / 1000) + " s)…");
  autoTimer = setInterval(function () {
    var target = Math.min(seq.length, Math.ceil(seq.length * (performance.now() - t0) / dur));
    while (i < target) { if (!move(seq[i++], true, true)) { stopAuto(); say("Replay stopped: move " + i + " (" + seq[i - 1] + ") was refused. This should not happen."); draw(); return; } }
    draw();
    if (i >= seq.length) { stopAuto(); }
  }, 16);
});
document.querySelectorAll(".pad button").forEach(function (b) { b.addEventListener("click", function () { stopAuto(); move(b.getAttribute("data-k")); }); });
$("undo").addEventListener("click", undo);
$("reset").addEventListener("click", function () { resetPlay(); say("Reset to the initial level."); draw(); });
$("zoom").addEventListener("click", function () { zoom = ZOOMS[(ZOOMS.indexOf(zoom) + 1) % ZOOMS.length]; this.textContent = "Zoom " + (zoom >= 1 ? "1×" : "1/" + Math.round(1 / zoom) + "×"); draw(); });
$("overlay").addEventListener("click", function () { overlay = !overlay; this.setAttribute("aria-pressed", String(overlay)); renderLegend(); draw(); });
document.querySelectorAll("#viewmode button").forEach(function (b) {
  b.addEventListener("click", function () {
    tiles = b.getAttribute("data-v") === "tiles";
    document.querySelectorAll("#viewmode button").forEach(function (o) { o.setAttribute("aria-pressed", String(o === b)); });
    try { localStorage.setItem("arena-view", tiles ? "tiles" : "text"); } catch (e) {}
    draw();
  });
});
try { if (localStorage.getItem("arena-view") === "text") { tiles = false; document.querySelectorAll("#viewmode button").forEach(function (o) { o.setAttribute("aria-pressed", String(o.getAttribute("data-v") === "text")); }); } } catch (e) {}
view.addEventListener("click", function () { view.focus({ preventScroll: true }); });
view.addEventListener("keydown", function (e) {
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  var k = ARROWS[e.key] || e.key, low = k.toLowerCase();
  if (DIRS[low]) { e.preventDefault(); stopAuto(); if (e.shiftKey) run(low); else move(low); }
  else if (k === ".") { e.preventDefault(); move("."); }
  else if (e.key === "Backspace") { e.preventDefault(); undo(); }
});
function fit() { var w = Math.min(960, Math.max(260, view.parentNode.clientWidth)); view.width = w; view.height = Math.round(w * 0.62); draw(); }
window.addEventListener("resize", fit);

// test hook (read-only): lets an automated check compare outputs
window.__engine = { result: function () { return R; }, log: function () { return log.join(""); }, won: function () { return won; },
  replayNow: function () { resetPlay(); var s = R.moves.replace(/E/g, ""); for (var i = 0; i < s.length; i++) if (!move(s[i], true, true)) { draw(); return { refused: i, key: s[i], at: hero.slice() }; } draw(); return { won: won, moves: log.length }; } };

startWorker();
})();
