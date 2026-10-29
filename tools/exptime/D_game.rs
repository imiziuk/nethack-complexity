//! D_game.rs -- fast exact solver for the hero-vs-nature boulder game exported by `D_game.py --export`
//! (D-model v1). Same rules and state space as D_game.py (see its docstring and proofs/exptime/D-checker.md):
//!   player position = (boulder set, unplugged holes, min node of the hero's free region)
//!   nature position = (boulder set, unplugged holes, trap node)        -> one successor per free landing region
//! The full reachable graph is built (goal-independent), then the hero's attractor (least fixed point) is computed.
//! Build: rustc -C opt-level=3 --edition 2021 -o target/D_game.exe D_game.rs
//! Usage: D_game <model.dmodel> [--start P] [--goal Q] [--state S] [--goal-state S] [--relation]
//!                [--max-states N] [--tree LINES]
use std::collections::HashMap;
use std::hash::{BuildHasherDefault, Hasher};
use std::time::Instant;

/// FxHash-style hasher (fast, deterministic); keys are compared in full, so collisions never merge states
#[derive(Default)]
struct Fx(u64);
impl Hasher for Fx {
    fn write(&mut self, bytes: &[u8]) {
        for c in bytes.chunks(8) {
            let mut b = [0u8; 8];
            b[..c.len()].copy_from_slice(c);
            self.write_u64(u64::from_le_bytes(b));
        }
    }
    fn write_u64(&mut self, x: u64) {
        self.0 = (self.0.rotate_left(5) ^ x).wrapping_mul(0x51_7c_c1_b7_27_22_0a_95);
    }
    fn write_u32(&mut self, x: u32) {
        self.write_u64(x as u64)
    }
    fn finish(&self) -> u64 {
        self.0
    }
}
type FxMap<K, V> = HashMap<K, V, BuildHasherDefault<Fx>>;

const NW: usize = 8; // node bitset words: N <= 512
const DW: usize = 6; // dynamic-cell words: D <= 384
type Bits = [u64; NW];
type DBits = [u64; DW];

#[derive(Clone, Copy, PartialEq, Eq, Hash, Debug)]
struct Key {
    b: DBits, // boulders (dyn index)
    h: u64,   // unplugged holes (hole index)
    t: u32,   // P: min region node; N: 0x8000_0000 | trap node
}
const NAT: u32 = 0x8000_0000;

#[inline]
fn bget<const K: usize>(b: &[u64; K], i: usize) -> bool {
    (b[i >> 6] >> (i & 63)) & 1 == 1
}
#[inline]
fn bset<const K: usize>(b: &mut [u64; K], i: usize) {
    b[i >> 6] |= 1 << (i & 63)
}
#[inline]
fn bclr<const K: usize>(b: &mut [u64; K], i: usize) {
    b[i >> 6] &= !(1 << (i & 63))
}
fn minbit(b: &Bits) -> usize {
    for (w, &x) in b.iter().enumerate() {
        if x != 0 {
            return w * 64 + x.trailing_zeros() as usize;
        }
    }
    usize::MAX
}

#[derive(Clone, Debug)]
enum Act {
    Push(usize, char), // boulder node, dir
    Enter(usize),      // trap node
    Land(Vec<(i64, i64)>),
}

#[allow(dead_code)]
struct M {
    n: usize,
    ns: usize,
    d: usize,
    cell: Vec<(i64, i64)>,
    un: Vec<Bits>,
    co: Vec<Vec<(usize, Vec<usize>)>>, // u -> (v, dyn corner idx list): usable iff some corner free of boulders
    te: Vec<Vec<(usize, Vec<usize>)>>, // u -> (trap node, corners) ; empty corners = always
    pushes: Vec<Vec<(usize, usize, char)>>, // dyn idx -> (hero node, target dyn idx, dir)
    pv: Vec<Vec<(usize, usize, char)>>,     // dyn idx -> (hero node, trap node, dir)  [design violation]
    land: HashMap<usize, Vec<(usize, (i64, i64))>>,
    hole_of: Vec<i32>,
    hole_dyn: Vec<usize>,
    nholes: usize,
    static_all: Bits,
    dyn_all: DBits,
    nw: usize, // node bitset words actually used
    states: Vec<(String, DBits)>,
    ports: Vec<(String, usize)>,
}

fn parse(path: &str) -> M {
    let txt = std::fs::read_to_string(path).expect("read model");
    let mut lines = txt.lines();
    let h: Vec<String> = lines.next().unwrap().split_whitespace().map(|s| s.to_string()).collect();
    assert!(h[0] == "DMODEL" && h[1] == "1", "not a D-model v1 file");
    let n: usize = h[2].parse().unwrap();
    let ns: usize = h[3].parse().unwrap();
    let d: usize = h[4].parse().unwrap();
    assert!(n <= 64 * NW && d <= 64 * DW, "model too large for NW/DW constants");
    let mut m = M {
        n,
        ns,
        d,
        cell: vec![(0, 0); n],
        un: vec![[0; NW]; n],
        co: vec![vec![]; n],
        te: vec![vec![]; n],
        pushes: vec![vec![]; d],
        pv: vec![vec![]; d],
        land: HashMap::new(),
        hole_of: vec![-1; d],
        hole_dyn: vec![],
        nholes: 0,
        static_all: [0; NW],
        dyn_all: [0; DW],
        nw: (n + 63) / 64,
        states: vec![],
        ports: vec![],
    };
    let nums = |it: std::str::SplitWhitespace| -> Vec<usize> { it.map(|x| x.parse().unwrap()).collect() };
    for l in lines {
        let mut it = l.split_whitespace();
        let tag = match it.next() {
            Some(t) => t,
            None => continue,
        };
        match tag {
            "CELL" => {
                let v = nums(it);
                m.cell[v[0]] = (v[1] as i64, v[2] as i64);
            }
            "H" => {
                for x in nums(it) {
                    m.hole_of[x - ns] = m.nholes as i32;
                    m.hole_dyn.push(x - ns);
                    m.nholes += 1;
                }
            }
            "STATE" => {
                let name = it.next().unwrap().to_string();
                let mut b = [0u64; DW];
                for x in nums(it) {
                    bset(&mut b, x - ns)
                }
                m.states.push((name, b));
            }
            "PORT" => {
                let name = it.next().unwrap().to_string();
                let v: usize = it.next().unwrap().parse().unwrap();
                m.ports.push((name, v));
            }
            "U" => {
                let v = nums(it);
                for &x in &v[1..] {
                    bset(&mut m.un[v[0]], x)
                }
            }
            "C" => {
                let v = nums(it);
                m.co[v[0]].push((v[1], v[2..].iter().map(|x| x - ns).collect()))
            }
            "TE" => {
                let v = nums(it);
                m.te[v[0]].push((v[1], v[2..].iter().map(|x| x - ns).collect()))
            }
            "P" | "PV" => {
                let v: Vec<&str> = it.collect();
                let a: usize = v[0].parse().unwrap();
                let hn: usize = v[1].parse().unwrap();
                let t: usize = v[2].parse().unwrap();
                let dir = v[3].chars().next().unwrap();
                if tag == "P" {
                    m.pushes[a - ns].push((hn, t - ns, dir))
                } else {
                    m.pv[a - ns].push((hn, t, dir))
                }
            }
            "L" => {
                let t: usize = it.next().unwrap().parse().unwrap();
                let mut lst = vec![];
                for e in it {
                    let (nd, xy) = e.split_once(':').unwrap();
                    let (x, y) = xy.split_once(',').unwrap();
                    lst.push((nd.parse().unwrap(), (x.parse().unwrap(), y.parse().unwrap())));
                }
                m.land.insert(t, lst);
            }
            _ => panic!("bad tag {}", tag),
        }
    }
    assert!(m.nholes <= 64 && m.ports.len() <= 64);
    for i in 0..ns {
        bset(&mut m.static_all, i)
    }
    for i in 0..d {
        bset(&mut m.dyn_all, i)
    }
    m
}

impl M {
    #[inline]
    fn blocked(&self, k: &Key, di: usize) -> bool {
        bget(&k.b, di) || (self.hole_of[di] >= 0 && (k.h >> self.hole_of[di]) & 1 == 1)
    }
    #[inline]
    fn passable(&self, k: &Key, v: usize) -> bool {
        v < self.ns || (v < self.ns + self.d && !self.blocked(k, v - self.ns))
    }
    /// free cells (node bitset) of position k: static nodes + dynamic nodes without boulder / unplugged hole
    fn passable_bits(&self, k: &Key) -> Bits {
        let mut blk = k.b;
        let mut h = k.h;
        while h != 0 {
            let i = h.trailing_zeros() as usize;
            h &= h - 1;
            bset(&mut blk, self.hole_dyn[i]);
        }
        let mut p = self.static_all;
        let (q, r) = (self.ns / 64, self.ns % 64);
        for w in 0..DW {
            let x = self.dyn_all[w] & !blk[w];
            if x == 0 {
                continue;
            }
            if q + w < NW {
                p[q + w] |= x << r;
            }
            if r != 0 && q + w + 1 < NW {
                p[q + w + 1] |= x >> (64 - r);
            }
        }
        p
    }
    fn region(&self, s: usize, k: &Key) -> Bits {
        self.region_base(s, k, &[0; NW])
    }
    /// flood from s; `base` = cells already known to be in the region (exact when the only change is that s was
    /// freed and a cell outside the old region was blocked, as after a push: see check_small.py)
    fn region_base(&self, s: usize, k: &Key, base: &Bits) -> Bits {
        let pass = self.passable_bits(k);
        let nw = self.nw;
        let mut seen = *base;
        bset(&mut seen, s);
        let mut fr = [0u64; NW];
        bset(&mut fr, s);
        loop {
            let mut acc = [0u64; NW];
            for w in 0..nw {
                let mut x = fr[w];
                while x != 0 {
                    let u = w * 64 + x.trailing_zeros() as usize;
                    x &= x - 1;
                    let un = &self.un[u];
                    for j in 0..nw {
                        acc[j] |= un[j];
                    }
                    for (v, cs) in &self.co[u] {
                        if cs.iter().any(|&c| !bget(&k.b, c)) {
                            bset(&mut acc, *v);
                        }
                    }
                }
            }
            let mut any = 0;
            for j in 0..nw {
                fr[j] = acc[j] & pass[j] & !seen[j];
                seen[j] |= fr[j];
                any |= fr[j];
            }
            if any == 0 {
                return seen;
            }
        }
    }
    fn pkey(&self, b: DBits, h: u64, s: usize) -> (Key, Bits) {
        self.pkey_base(b, h, s, &[0; NW])
    }
    fn pkey_base(&self, b: DBits, h: u64, s: usize, base: &Bits) -> (Key, Bits) {
        let mut k = Key { b, h, t: 0 };
        let r = self.region_base(s, &k, base);
        k.t = minbit(&r) as u32;
        (k, r)
    }
    fn port_mask(&self, r: &Bits) -> u64 {
        let mut m = 0u64;
        for (i, (_, n)) in self.ports.iter().enumerate() {
            if bget(r, *n) {
                m |= 1 << i;
            }
        }
        m
    }
    /// successors with actions; violations pushed into `vio`
    /// successors with actions and, for player successors, the mask of ports inside the hero's region
    fn expand(&self, k: &Key, vio: &mut Vec<String>) -> Vec<(Key, Act, u64)> {
        let mut out: Vec<(Key, Act, u64)> = vec![];
        if k.t & NAT == 0 {
            let reg = self.region(k.t as usize, k);
            for w in 0..DW {
                let mut x = k.b[w];
                while x != 0 {
                    let bi = w * 64 + x.trailing_zeros() as usize;
                    x &= x - 1;
                    for &(hn, ti, dir) in &self.pushes[bi] {
                        if !bget(&reg, hn) || bget(&k.b, ti) {
                            continue;
                        }
                        let mut nb = k.b;
                        bclr(&mut nb, bi);
                        let mut nh = k.h;
                        let ho = self.hole_of[ti];
                        if ho >= 0 && (nh >> ho) & 1 == 1 {
                            nh &= !(1u64 << ho);
                        } else {
                            bset(&mut nb, ti);
                        }
                        let base = if bget(&reg, self.ns + ti) { [0u64; NW] } else { reg };
                        let (nk, r) = self.pkey_base(nb, nh, self.ns + bi, &base);
                        out.push((nk, Act::Push(self.ns + bi, dir), self.port_mask(&r)));
                    }
                    for &(hn, tn, dir) in &self.pv[bi] {
                        if bget(&reg, hn) {
                            vio.push(format!(
                                "boulder-onto-trap: boulder {:?} pushed {} onto trap {:?}",
                                self.cell[self.ns + bi], dir, self.cell[tn]
                            ));
                        }
                    }
                }
            }
            let mut seen_t: Vec<usize> = vec![];
            for w in 0..NW {
                let mut x = reg[w];
                while x != 0 {
                    let u = w * 64 + x.trailing_zeros() as usize;
                    x &= x - 1;
                    for (t, cs) in &self.te[u] {
                        if seen_t.contains(t) {
                            continue;
                        }
                        if !cs.is_empty() && !cs.iter().any(|&c| !bget(&k.b, c)) {
                            continue;
                        }
                        seen_t.push(*t);
                        out.push((Key { b: k.b, h: k.h, t: NAT | *t as u32 }, Act::Enter(*t), 0));
                    }
                }
            }
        } else {
            let t = (k.t & !NAT) as usize;
            let mut groups: Vec<(Key, Vec<(i64, i64)>, u64)> = vec![];
            for &(ln, c) in &self.land[&t] {
                if ln >= self.ns && ln < self.ns + self.d && self.blocked(k, ln - self.ns) {
                    continue;
                }
                let (nk, r) = self.pkey(k.b, k.h, ln);
                match groups.iter_mut().find(|g| g.0 == nk) {
                    Some(g) => g.1.push(c),
                    None => groups.push((nk, vec![c], self.port_mask(&r))),
                }
            }
            if groups.is_empty() {
                vio.push(format!("empty-landing-set at trap {:?}", self.cell[t]));
            }
            for (nk, cs, pm) in groups {
                out.push((nk, Act::Land(cs), pm));
            }
        }
        let mut ded: Vec<(Key, Act, u64)> = vec![];
        for (kk, a, pm) in out {
            if !ded.iter().any(|(k2, _, _)| *k2 == kk) {
                ded.push((kk, a, pm));
            }
        }
        ded
    }
    fn port(&self, name: &str) -> usize {
        self.ports.iter().find(|p| p.0 == name).unwrap_or_else(|| panic!("no port {}", name)).1
    }
    fn port_index(&self, name: &str) -> usize {
        self.ports.iter().position(|p| p.0 == name).unwrap_or_else(|| panic!("no port {}", name))
    }
    fn state(&self, name: &str) -> DBits {
        self.states.iter().find(|p| p.0 == name).unwrap_or_else(|| panic!("no state {}", name)).1
    }
    fn bcells(&self, b: &DBits) -> Vec<(i64, i64)> {
        (0..self.d).filter(|&i| bget(b, i)).map(|i| self.cell[self.ns + i]).collect()
    }
    fn fmt(&self, a: &Act) -> String {
        match a {
            Act::Push(n, d) => format!("push boulder {:?} {}", self.cell[*n], d),
            Act::Enter(t) => format!("step onto trap {:?}", self.cell[*t]),
            Act::Land(cs) => format!(
                "nature lands hero on {}",
                cs.iter().map(|c| format!("{:?}", c)).collect::<Vec<_>>().join(" or ")
            ),
        }
    }
}

struct Graph {
    keys: Vec<Key>,
    idx: FxMap<Key, u32>,
    pm: Vec<u64>, // P node: ports inside the hero's region (bit = port index)
    off: Vec<u64>,
    succ: Vec<u32>,
    starts: Vec<u32>,
    vio: Vec<String>,
    nvio: usize,
}

fn explore(m: &M, starts: &[Key], cap: usize) -> Graph {
    let mut g = Graph {
        keys: vec![],
        idx: FxMap::default(),
        pm: vec![],
        off: vec![0],
        succ: vec![],
        starts: vec![],
        vio: vec![],
        nvio: 0,
    };
    for k in starts {
        let len = g.keys.len() as u32;
        let i = *g.idx.entry(*k).or_insert(len);
        if i == len {
            g.keys.push(*k);
            g.pm.push(m.port_mask(&m.region(k.t as usize, k)));
        }
        g.starts.push(i);
    }
    let t0 = Instant::now();
    let mut i = 0;
    let mut vio = vec![];
    while i < g.keys.len() {
        let k = g.keys[i];
        vio.clear();
        for (nk, _, pm) in m.expand(&k, &mut vio) {
            let len = g.keys.len() as u32;
            let j = *g.idx.entry(nk).or_insert(len);
            if j == len {
                g.keys.push(nk);
                g.pm.push(pm);
            }
            g.succ.push(j);
        }
        if !vio.is_empty() {
            g.nvio += vio.len();
            if g.vio.len() < 10 {
                g.vio.push(format!("at position {}: {}", i, vio[0]));
            }
        }
        g.off.push(g.succ.len() as u64);
        i += 1;
        if g.keys.len() > cap {
            println!("RESULT capped states={} secs={:.1}", g.keys.len(), t0.elapsed().as_secs_f64());
            std::process::exit(2);
        }
        if i % 1_000_000 == 0 {
            eprintln!("expanded {} stored {} {:.0}s", i, g.keys.len(), t0.elapsed().as_secs_f64());
        }
    }
    g
}

const LOSE: u32 = u32::MAX;

fn attractor(g: &Graph, goal_port: usize, gstate: Option<(DBits, u64)>, pred: &(Vec<u64>, Vec<u32>)) -> Vec<u32> {
    let n = g.keys.len();
    let mut rank = vec![LOSE; n];
    let mut cnt: Vec<u32> = (0..n).map(|i| (g.off[i + 1] - g.off[i]) as u32).collect();
    let mut q: Vec<u32> = vec![];
    for (i, k) in g.keys.iter().enumerate() {
        if k.t & NAT == 0
            && (g.pm[i] >> goal_port) & 1 == 1
            && gstate.map_or(true, |(b, h)| b == k.b && h == k.h)
        {
            rank[i] = 0;
            q.push(i as u32);
        }
    }
    let mut head = 0;
    while head < q.len() {
        let j = q[head] as usize;
        head += 1;
        for p in pred.0[j]..pred.0[j + 1] {
            let i = pred.1[p as usize] as usize;
            if rank[i] != LOSE {
                continue;
            }
            if g.keys[i].t & NAT == 0 {
                rank[i] = rank[j] + 1;
                q.push(i as u32);
            } else {
                cnt[i] -= 1;
                if cnt[i] == 0 {
                    rank[i] = rank[j] + 1;
                    q.push(i as u32);
                }
            }
        }
    }
    rank
}

fn preds(g: &Graph) -> (Vec<u64>, Vec<u32>) {
    let n = g.keys.len();
    let mut deg = vec![0u64; n + 1];
    for &j in &g.succ {
        deg[j as usize + 1] += 1;
    }
    for i in 0..n {
        deg[i + 1] += deg[i];
    }
    let mut fill = deg.clone();
    let mut p = vec![0u32; g.succ.len()];
    for i in 0..n {
        for e in g.off[i]..g.off[i + 1] {
            let j = g.succ[e as usize] as usize;
            p[fill[j] as usize] = i as u32;
            fill[j] += 1;
        }
    }
    (deg, p)
}

fn coop(g: &Graph, s: usize, rank: &[u32]) -> bool {
    let mut seen = vec![false; g.keys.len()];
    let mut st = vec![s];
    seen[s] = true;
    while let Some(i) = st.pop() {
        if rank[i] == 0 {
            return true;
        }
        for e in g.off[i]..g.off[i + 1] {
            let j = g.succ[e as usize] as usize;
            if !seen[j] {
                seen[j] = true;
                st.push(j);
            }
        }
    }
    false
}

fn tree(m: &M, g: &Graph, s: usize, rank: &[u32], max: usize) -> Vec<String> {
    let mut out = vec![];
    let mut label: HashMap<usize, usize> = HashMap::new();
    let mut dummy = vec![];
    fn go(m: &M, g: &Graph, i: usize, ind: String, rank: &[u32], max: usize, out: &mut Vec<String>,
          label: &mut HashMap<usize, usize>, dummy: &mut Vec<String>) {
        if out.len() >= max {
            return;
        }
        if let Some(l) = label.get(&i) {
            out.push(format!("{}(same as [{}])", ind, l));
            return;
        }
        let l = label.len();
        label.insert(i, l);
        if rank[i] == 0 {
            out.push(format!("{}[{}] goal reachable on foot", ind, l));
            return;
        }
        let k = g.keys[i];
        let succ = m.expand(&k, dummy);
        if k.t & NAT == 0 {
            let (j, a) = succ
                .iter()
                .map(|(kk, a, _)| (g.idx[kk] as usize, a))
                .filter(|(j, _)| rank[*j] < rank[i])
                .min_by_key(|(j, _)| rank[*j])
                .unwrap();
            out.push(format!("{}[{}] {}", ind, l, m.fmt(a)));
            go(m, g, j, ind, rank, max, out, label, dummy);
        } else {
            out.push(format!("{}[{}] nature: {} choice(s)", ind, l, succ.len()));
            for (kk, a, _) in &succ {
                out.push(format!("{}  - {}", ind, m.fmt(a)));
                go(m, g, g.idx[kk] as usize, format!("{}    ", ind), rank, max, out, label, dummy);
            }
        }
    }
    go(m, g, s, String::new(), rank, max, &mut out, &mut label, &mut dummy);
    if out.len() >= max {
        out.push(format!("... (truncated at {} lines)", max));
    }
    out
}

fn counter(m: &M, g: &Graph, s: usize, rank: &[u32], max: usize) -> Vec<String> {
    let mut seen = vec![false; g.keys.len()];
    let mut st = vec![s];
    seen[s] = true;
    let mut out = vec![];
    let mut nat = 0;
    let mut dummy = vec![];
    while let Some(i) = st.pop() {
        let k = g.keys[i];
        let mut next = vec![];
        if k.t & NAT != 0 {
            nat += 1;
            let succ = m.expand(&k, &mut dummy);
            let pick = succ.iter().find(|(kk, _, _)| rank[g.idx[kk] as usize] == LOSE);
            if out.len() < max {
                let alts: Vec<String> = succ
                    .iter()
                    .map(|(_, a, _)| match a {
                        Act::Land(cs) => cs.iter().map(|c| format!("{:?}", c)).collect::<Vec<_>>().join("/"),
                        _ => String::new(),
                    })
                    .collect();
                out.push(format!(
                    "boulders {:?}, trap {:?}: {}   (options: {})",
                    m.bcells(&k.b),
                    m.cell[(k.t & !NAT) as usize],
                    pick.map_or("EMPTY LANDING SET".to_string(), |p| m.fmt(&p.1)),
                    alts.join(" | ")
                ));
            }
            if let Some((kk, _, _)) = pick {
                next.push(g.idx[kk] as usize);
            }
        } else {
            for e in g.off[i]..g.off[i + 1] {
                next.push(g.succ[e as usize] as usize);
            }
        }
        for j in next {
            if !seen[j] {
                seen[j] = true;
                st.push(j);
            }
        }
    }
    let reach = seen.iter().filter(|&&x| x).count();
    let mut r = vec![format!("nature nodes reachable under its counter-strategy: {} (positions {})", nat, reach)];
    r.extend(out);
    r
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let path = &args[1];
    let mut opt: HashMap<String, String> = HashMap::new();
    let mut relation = false;
    let mut i = 2;
    while i < args.len() {
        if args[i] == "--relation" {
            relation = true;
            i += 1;
        } else {
            opt.insert(args[i].trim_start_matches("--").to_string(), args[i + 1].clone());
            i += 2;
        }
    }
    let cap: usize = opt.get("max-states").map_or(50_000_000, |s| s.parse().unwrap());
    let tlines: usize = opt.get("tree").map_or(60, |s| s.parse().unwrap());
    let m = parse(path);
    let h0: u64 = if m.nholes == 64 { u64::MAX } else { (1u64 << m.nholes) - 1 };
    let t0 = Instant::now();
    if relation {
        let mut starts = vec![];
        let mut labels = vec![];
        for (sn, sb) in &m.states {
            for (pn, pnode) in &m.ports {
                let probe = Key { b: *sb, h: h0, t: 0 };
                if *pnode >= m.ns + m.d || !m.passable(&probe, *pnode) {
                    continue;
                }
                starts.push(m.pkey(*sb, h0, *pnode).0);
                labels.push((sn.clone(), pn.clone()));
            }
        }
        let g = explore(&m, &starts, cap);
        let pr = preds(&g);
        println!("positions {} violations {} secs {:.2}", g.keys.len(), g.nvio, t0.elapsed().as_secs_f64());
        for v in &g.vio {
            println!("VIOLATION {}", v);
        }
        for (qi, (qn, _)) in m.ports.iter().enumerate() {
            let mut targets: Vec<(String, Option<(DBits, u64)>)> = vec![("*".into(), None)];
            for (sn, sb) in &m.states {
                targets.push((sn.clone(), Some((*sb, h0))));
            }
            for (en, gs) in targets {
                let rank = attractor(&g, qi, gs, &pr);
                for ((sn, pn), &si) in labels.iter().zip(&g.starts) {
                    if pn != qn {
                        let w = rank[si as usize] != LOSE;
                        println!(
                            "{:<6} {} -> {} exit={:<6} {}{}",
                            sn, pn, qn, en,
                            if w { "WIN " } else { "lose" },
                            if !w && coop(&g, si as usize, &rank) { "  (coop-reachable: nature blocks)" } else { "" }
                        );
                    }
                }
            }
        }
        return;
    }
    let sname = opt.get("start").cloned().unwrap_or("@".into());
    let gname = opt.get("goal").cloned().unwrap_or("G".into());
    let st = m.state(opt.get("state").map_or("init", |s| s.as_str()));
    let gs = opt.get("goal-state").map(|s| (m.state(s), h0));
    let (sk, _) = m.pkey(st, h0, m.port(&sname));
    let g = explore(&m, &[sk], cap);
    let tex = t0.elapsed().as_secs_f64();
    let pr = preds(&g);
    let rank = attractor(&g, m.port_index(&gname), gs, &pr);
    let s = g.starts[0] as usize;
    let np = g.keys.iter().filter(|k| k.t & NAT == 0).count();
    println!(
        "RESULT result={} player_nodes={} nature_nodes={} winning_nodes={} rank={} coop_reach={} violations={} edges={} secs_explore={:.2} secs={:.2}",
        if rank[s] != LOSE { "WIN" } else { "LOSE" },
        np,
        g.keys.len() - np,
        rank.iter().filter(|&&r| r != LOSE).count(),
        if rank[s] == LOSE { "None".to_string() } else { rank[s].to_string() },
        if coop(&g, s, &rank) { "True" } else { "False" },
        g.nvio,
        g.succ.len(),
        tex,
        t0.elapsed().as_secs_f64()
    );
    for v in &g.vio {
        println!("VIOLATION {}", v);
    }
    let lines = if rank[s] != LOSE { tree(&m, &g, s, &rank, tlines) } else { counter(&m, &g, s, &rank, 40) };
    for l in lines {
        println!("{}", l);
    }
}
