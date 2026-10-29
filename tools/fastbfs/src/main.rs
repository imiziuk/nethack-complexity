//! fastbfs: exact exhaustive push-level BFS for one level exported by `check_small.py --only ... --export DIR`.
//! Same state space and transition rules as check_small.py Model.solve (no pruning, no hashing shortcuts:
//! every state is stored in full and compared in full).
//!   state = (boulder set, unplugged-hole set, min node of the hero's free region)
//! Usage: fastbfs <model.txt> [--max-states N] [--max-seconds S]
//! Output: one line "RESULT reach=<true|false|capped> states=<n> expanded=<n> secs=<t>".
use std::io::{BufRead, Write};
use std::time::Instant;

const W: usize = 6; // node bitset words: N <= 384
type Bits = [u64; W];
const KW: usize = 3;
/// Lossless mixed-radix code of (boulder set, hole mask, min node). Dynamic cells are split into push-components
/// (connected under 'a boulder on c can be pushed to t'); a boulder never leaves its component, so the boulder set
/// is the tuple of per-component subsets, each of size <= its initial count (sizes only drop, by plugging). Each
/// subset is ranked exactly (offset by size + colex rank), so distinct states get distinct keys.
type Key = [u64; KW];

#[inline]
fn has(b: &Bits, i: usize) -> bool {
    (b[i >> 6] >> (i & 63)) & 1 == 1
}
#[inline]
fn set(b: &mut Bits, i: usize) {
    b[i >> 6] |= 1 << (i & 63);
}
#[inline]
fn clr(b: &mut Bits, i: usize) {
    b[i >> 6] &= !(1 << (i & 63));
}

struct M {
    un: Vec<Bits>,                     // unconditional adjacency
    co: Vec<Vec<(usize, Vec<usize>)>>, // conditional edge u -> v with corner nodes; usable iff some corner is not a boulder
    pushes: Vec<Vec<(usize, usize)>>,  // per boulder node: (hero node, target node)
    hole_of: Vec<i32>,                 // node -> compact hole index or -1
    holes: Vec<usize>,
    static_all: Bits,
    dyn_all: Bits,
    ns: usize,
    nbits: usize, // number of dynamic cells D
    start: usize,
    goal: usize,
    b0: Bits,
    comp_of: Vec<(usize, usize)>,     // dynamic node -> (component, local index)
    comps: Vec<(Vec<usize>, usize, u64)>, // (cells, initial boulder count k, radix = sum_{j<=k} C(n,j))
    binom: Vec<Vec<u64>>,
}

fn parse(path: &str) -> M {
    let f = std::io::BufReader::new(std::fs::File::open(path).expect("open"));
    let mut lines = f.lines().map(|l| l.unwrap());
    let h: Vec<usize> = lines.next().unwrap().split_whitespace().map(|x| x.parse().unwrap()).collect();
    let (n, ns, start, goal) = (h[0], h[1], h[2], h[3]);
    assert!(n <= 64 * W, "too many nodes");
    let mut m = M {
        un: vec![[0; W]; n],
        co: vec![vec![]; n],
        pushes: vec![vec![]; n],
        hole_of: vec![-1; n],
        holes: vec![],
        static_all: [0; W],
        dyn_all: [0; W],
        ns,
        nbits: n - ns,
        start,
        goal,
        b0: [0; W],
        comp_of: vec![(usize::MAX, 0); n],
        comps: vec![],
        binom: vec![],
    };
    for i in 0..n {
        if i < ns {
            set(&mut m.static_all, i)
        } else {
            set(&mut m.dyn_all, i)
        }
    }
    for l in lines {
        let mut it = l.split_whitespace();
        let tag = it.next().unwrap();
        let v: Vec<usize> = it.map(|x| x.parse().unwrap()).collect();
        match tag {
            "B" => {
                for &x in &v {
                    set(&mut m.b0, x)
                }
            }
            "H" => {
                for &x in &v {
                    m.hole_of[x] = m.holes.len() as i32;
                    m.holes.push(x)
                }
            }
            "U" => {
                for &x in &v[1..] {
                    set(&mut m.un[v[0]], x)
                }
            }
            "C" => m.co[v[0]].push((v[1], v[2..].to_vec())),
            "P" => m.pushes[v[0]].push((v[1], v[2])),
            _ => panic!("bad tag"),
        }
    }
    assert_eq!(h[4], m.holes.len());
    assert!(m.holes.len() <= 32);
    // push-components
    let mut par: Vec<usize> = (0..n).collect();
    fn find(p: &mut Vec<usize>, mut a: usize) -> usize {
        while p[a] != a {
            p[a] = p[p[a]];
            a = p[a];
        }
        a
    }
    for i in ns..n {
        for &(_, t) in &m.pushes[i].clone() {
            assert!(t >= ns, "push target must be dynamic");
            let (a, b) = (find(&mut par, i), find(&mut par, t));
            par[a] = b;
        }
    }
    m.binom = vec![vec![0u64; 400]; 400];
    for a in 0..400 {
        m.binom[a][0] = 1;
        for b in 1..=a {
            m.binom[a][b] = m.binom[a - 1][b - 1].saturating_add(m.binom[a - 1][b]);
        }
    }
    let mut root_comp = std::collections::HashMap::new();
    for i in ns..n {
        let r = find(&mut par, i);
        let c = *root_comp.entry(r).or_insert_with(|| {
            m.comps.push((vec![], 0, 0));
            m.comps.len() - 1
        });
        m.comp_of[i] = (c, m.comps[c].0.len());
        m.comps[c].0.push(i);
        if has(&m.b0, i) {
            m.comps[c].1 += 1;
        }
    }
    let mut lg = 0.0f64;
    for c in m.comps.iter_mut() {
        let nn = c.0.len();
        c.2 = (0..=c.1).map(|j| m.binom[nn][j]).sum();
        lg += (c.2 as f64).log2();
    }
    lg += m.holes.len() as f64 + (n as f64).log2();
    eprintln!("components {} key bits {:.1} (limit {})", m.comps.len(), lg, 64 * KW);
    assert!(lg < (64 * KW) as f64 - 1.0, "key does not fit");
    m
}

fn mul_add(k: &mut Key, r: u64, a: u64) {
    let mut carry = a as u128;
    for w in 0..KW {
        let v = k[w] as u128 * r as u128 + carry;
        k[w] = v as u64;
        carry = v >> 64;
    }
    assert!(carry == 0, "key overflow");
}
fn div_mod(k: &mut Key, r: u64) -> u64 {
    let mut rem: u128 = 0;
    for w in (0..KW).rev() {
        let cur = (rem << 64) | k[w] as u128;
        k[w] = (cur / r as u128) as u64;
        rem = cur % r as u128;
    }
    rem as u64
}

impl M {
    /// free region of the hero on node s (bitset), seeded with `base` (nodes known to be in the region)
    fn region(&self, s: usize, bm: &Bits, hm: u32, base: &Bits) -> Bits {
        let mut hb = [0u64; W];
        for (k, &x) in self.holes.iter().enumerate() {
            if (hm >> k) & 1 == 1 {
                set(&mut hb, x)
            }
        }
        let mut pass = [0u64; W];
        for w in 0..W {
            pass[w] = self.static_all[w] | (self.dyn_all[w] & !(bm[w] | hb[w]));
        }
        let mut seen = *base;
        set(&mut seen, s);
        let mut frontier = [0u64; W];
        set(&mut frontier, s);
        loop {
            let mut acc = [0u64; W];
            for w in 0..W {
                let mut f = frontier[w];
                while f != 0 {
                    let u = w * 64 + f.trailing_zeros() as usize;
                    f &= f - 1;
                    let a = &self.un[u];
                    for k in 0..W {
                        acc[k] |= a[k];
                    }
                    for (v, cs) in &self.co[u] {
                        if !cs.iter().all(|&c| has(bm, c)) {
                            set(&mut acc, *v);
                        }
                    }
                }
            }
            let mut any = 0;
            for w in 0..W {
                frontier[w] = acc[w] & pass[w] & !seen[w];
                seen[w] |= frontier[w];
                any |= frontier[w];
            }
            if any == 0 {
                return seen;
            }
        }
    }
}

fn minbit(b: &Bits) -> usize {
    for w in 0..W {
        if b[w] != 0 {
            return w * 64 + b[w].trailing_zeros() as usize;
        }
    }
    usize::MAX
}

impl M {
    fn mkkey(&self, bm: &Bits, hm: u32, mn: usize) -> Key {
        // per-component ranks
        let nc = self.comps.len();
        let mut sz = vec![0usize; nc];
        let mut rk = vec![0u64; nc];
        for w in 0..W {
            let mut b = bm[w];
            while b != 0 {
                let i = w * 64 + b.trailing_zeros() as usize;
                b &= b - 1;
                let (c, l) = self.comp_of[i];
                assert!(c != usize::MAX, "boulder on a static node");
                sz[c] += 1; // bits come in increasing local order
                rk[c] += self.binom[l][sz[c]];
            }
        }
        let mut k = [0u64; KW];
        for c in 0..nc {
            let (cells, kk, rad) = &self.comps[c];
            assert!(sz[c] <= *kk, "component gained a boulder");
            let off: u64 = (0..sz[c]).map(|j| self.binom[cells.len()][j]).sum();
            let r = off + rk[c];
            debug_assert!(r < *rad);
            mul_add(&mut k, *rad, r);
        }
        mul_add(&mut k, 1u64 << self.holes.len(), hm as u64);
        mul_add(&mut k, 1u64 << 16, mn as u64);
        k
    }
    fn unkey(&self, k0: &Key) -> (Bits, u32, usize) {
        let mut k = *k0;
        let mn = div_mod(&mut k, 1u64 << 16) as usize;
        let hm = div_mod(&mut k, 1u64 << self.holes.len()) as u32;
        let mut bm = [0u64; W];
        for c in (0..self.comps.len()).rev() {
            let (cells, _, rad) = &self.comps[c];
            let mut r = div_mod(&mut k, *rad);
            let n = cells.len();
            let mut j = 0;
            while r >= self.binom[n][j] {
                r -= self.binom[n][j];
                j += 1;
            }
            // colex unrank of a j-subset
            let mut hi = n;
            for t in (1..=j).rev() {
                let mut x = t - 1;
                while x + 1 < hi && self.binom[x + 1][t] <= r {
                    x += 1;
                }
                r -= self.binom[x][t];
                set(&mut bm, cells[x]);
                hi = x;
            }
        }
        debug_assert!(k == [0u64; KW]);
        (bm, hm, mn)
    }
}

#[inline]
fn hash(k: &Key) -> u64 {
    let mut h: u64 = 0x9E3779B97F4A7C15;
    for &x in k {
        h = (h ^ x).wrapping_mul(0xff51afd7ed558ccd);
        h ^= h >> 29;
    }
    h
}

/// exact set of keys: keys live in `store` (also the BFS queue), the table holds index+1 (0 = empty);
/// membership uses full-key comparison, so no state is ever dropped by a hash collision.
const CH: usize = 1 << 20;
struct Store {
    chunks: Vec<Vec<Key>>,
    n: usize,
}
impl Store {
    fn len(&self) -> usize {
        self.n
    }
    fn push(&mut self, k: Key) {
        if self.n % CH == 0 {
            self.chunks.push(Vec::with_capacity(CH));
        }
        self.chunks.last_mut().unwrap().push(k);
        self.n += 1;
    }
    fn iter(&self) -> impl Iterator<Item = &Key> {
        self.chunks.iter().flat_map(|c| c.iter())
    }
}
impl std::ops::Index<usize> for Store {
    type Output = Key;
    fn index(&self, i: usize) -> &Key {
        &self.chunks[i / CH][i % CH]
    }
}
struct Set {
    tab: Vec<u32>,
    mask: usize,
    store: Store,
}
impl Set {
    fn new() -> Self {
        Set { tab: vec![0; 1 << 20], mask: (1 << 20) - 1, store: Store { chunks: vec![], n: 0 } }
    }
    fn insert(&mut self, k: Key) -> bool {
        if (self.store.len() + 1) * 10 > self.tab.len() * 7 {
            self.grow();
        }
        let mut i = hash(&k) as usize & self.mask;
        loop {
            let e = self.tab[i];
            if e == 0 {
                self.store.push(k);
                self.tab[i] = self.store.len() as u32;
                return true;
            }
            if self.store[(e - 1) as usize] == k {
                return false;
            }
            i = (i + 1) & self.mask;
        }
    }
    fn grow(&mut self) {
        let nl = self.tab.len() * 2;
        let mut t = vec![0u32; nl];
        let mask = nl - 1;
        for (j, k) in self.store.iter().enumerate() {
            let mut i = hash(k) as usize & mask;
            while t[i] != 0 {
                i = (i + 1) & mask;
            }
            t[i] = j as u32 + 1;
        }
        self.tab = t;
        self.mask = mask;
    }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let m = parse(&args[1]);
    let mut max_states: usize = 4_000_000_000;
    let mut max_secs: f64 = f64::INFINITY;
    let mut i = 2;
    while i < args.len() {
        match args[i].as_str() {
            "--max-states" => {
                max_states = args[i + 1].parse().unwrap();
                i += 2
            }
            "--max-seconds" => {
                max_secs = args[i + 1].parse().unwrap();
                i += 2
            }
            _ => panic!("bad arg"),
        }
    }
    let t0 = Instant::now();
    let h0: u32 = ((1u64 << m.holes.len()) - 1) as u32;
    let zero = [0u64; W];
    let r0 = m.region(m.start, &m.b0, h0, &zero);
    let mut st = Set::new();
    st.insert(m.mkkey(&m.b0, h0, minbit(&r0)));
    let mut head = 0usize;
    let mut last_report = 0.0;
    let reach;
    loop {
        if head >= st.store.len() {
            reach = "false";
            break;
        }
        let k = st.store[head];
        head += 1;
        let (bm, hm, mn) = m.unkey(&k);
        let reg = m.region(mn, &bm, hm, &zero);
        if has(&reg, m.goal) {
            reach = "true";
            break;
        }
        if head & 0xfff == 0 {
            let el = t0.elapsed().as_secs_f64();
            if el > max_secs || st.store.len() > max_states {
                reach = "capped";
                break;
            }
            if el - last_report > 60.0 {
                last_report = el;
                eprintln!("{:.0}s expanded {} stored {}", el, head, st.store.len());
            }
        }
        for w in 0..W {
            let mut bb = bm[w];
            while bb != 0 {
                let b = w * 64 + bb.trailing_zeros() as usize;
                bb &= bb - 1;
                for &(hn, tn) in &m.pushes[b] {
                    if !has(&reg, hn) || has(&bm, tn) {
                        continue;
                    }
                    let mut nb = bm;
                    let mut nh = hm;
                    clr(&mut nb, b);
                    let hi = m.hole_of[tn];
                    if hi >= 0 && (hm >> hi) & 1 == 1 {
                        nh &= !(1 << hi); // boulder plugs the hole: both vanish
                    } else {
                        set(&mut nb, tn);
                    }
                    // if t was outside the region it is not orthogonally adjacent to it, hence no corner of a
                    // diagonal inside it: the old region stays connected and seeds the new flood (as in Python)
                    let base = if has(&reg, tn) { zero } else { reg };
                    let r2 = m.region(b, &nb, nh, &base);
                    let key = m.mkkey(&nb, nh, minbit(&r2));
                    debug_assert!(m.unkey(&key) == (nb, nh, minbit(&r2)), "key round trip");
                    st.insert(key);
                }
            }
        }
    }
    println!(
        "RESULT reach={} states={} expanded={} secs={:.1}",
        reach,
        st.store.len(),
        head,
        t0.elapsed().as_secs_f64()
    );
    std::io::stdout().flush().unwrap();
}
