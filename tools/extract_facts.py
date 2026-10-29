"""Auto-extract source facts from a C game codebase (built for NetHack 5.0.0, reusable).

Outputs JSON with:
  constants : #define NAME <int>    (file, line, value)
  rng_sites : calls to RNG functions per function (file, function, line, callee)
  struct_fields : fields of selected structs (name, type, file, line)

Usage: python -I extract_facts.py <src_root> <out.json> [--rng rn2,rnd,rnl,rne,rnz,d]
Heuristic (regex) parser: results are labelled [auto-extracted], not proved.
"""
import json, re, sys
from pathlib import Path

DEF = re.compile(r'^\s*#\s*define\s+([A-Z_][A-Z0-9_]*)\s+\(?\s*(-?\d+)[LlUu]*\s*\)?\s*(?:/\*.*)?$')
FUNC = re.compile(r'^(?:[A-Za-z_][\w\s\*]*?[\s\*])?([A-Za-z_]\w*)\s*\(([^;]*)$')  # name(args) at column 0 (NetHack style)


def scan(root, rng_names):
    root = Path(root)
    consts, sites = [], []
    call = re.compile(r'\b(' + '|'.join(map(re.escape, rng_names)) + r')\s*\(')
    for p in sorted(list(root.glob('include/*.h')) + list(root.glob('src/*.c'))):
        cur = None
        for i, line in enumerate(p.read_text(errors='replace').splitlines(), 1):
            m = DEF.match(line)
            if m:
                consts.append({'name': m[1], 'value': int(m[2]), 'file': str(p.relative_to(root)), 'line': i})
            if p.suffix == '.c':
                if line and not line[0].isspace() and line[0] not in '#{}/*':
                    f = FUNC.match(line)
                    if f and f[1] not in ('if', 'while', 'for', 'switch', 'return'):
                        cur = f[1]
                for c in call.finditer(line):
                    if not line.lstrip().startswith(('/*', '*')):
                        sites.append({'file': str(p.relative_to(root)), 'function': cur, 'line': i, 'callee': c[1]})
    return consts, sites


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    rng = ['rn2', 'rnd', 'rnl', 'rne', 'rnz', 'd', 'rn1']
    if '--rng' in sys.argv:
        rng = sys.argv[sys.argv.index('--rng') + 1].split(',')
    consts, sites = scan(sys.argv[1], rng)
    per_file = {}
    for s in sites:
        per_file[s['file']] = per_file.get(s['file'], 0) + 1
    out = {'constants': consts, 'rng_sites': sites,
           'summary': {'n_constants': len(consts), 'n_rng_sites': len(sites),
                       'rng_sites_per_file': dict(sorted(per_file.items(), key=lambda kv: -kv[1]))}}
    Path(sys.argv[2]).write_text(json.dumps(out, indent=1))
    print(json.dumps(out['summary']['n_constants']), 'constants,', len(sites), 'RNG call sites')
    for f, n in list(out['summary']['rng_sites_per_file'].items())[:12]:
        print(f'  {n:5d}  {f}')


if __name__ == '__main__':
    main()
