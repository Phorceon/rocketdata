"""Family grouping for .ork files.

A FAMILY is a set of files that are versions/variants of the same underlying
rocket. Two signals are combined (union):

  1. STEM family - the filename stem, after stripping version/date/sim suffixes,
     is equal. e.g. `APEX`, `ASTRA`, `Siruis_O3800`, `Argonia_2p242OD_K250`,
     `NASA_Rocket`, `RocketV1`.

  2. GEOMETRY family - the airframe signature matches within a ~5% relative
     tolerance on body diameter, total length and fin dimensions. This catches
     files with unrelated names that are nonetheless the same airframe.

Signals 1 and 2 are merged by union-find so overlapping signals collapse into a
single family. Family id is the lexicographically smallest member path.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from ork_design import build_design  # noqa: E402

TOL = 0.05

# ---------------------------------------------------------------- stem family

# version / date / sim / copy suffixes to strip, applied repeatedly from the end.
_SUFFIX_PATTERNS = [
    r"\s*\(\d+\)",                                   # " (1)"
    r"[_\-\s]*sim[_\-\s]*\d.*$",                     # "_SIM_9-15-24"
    r"[_\-\s]*v\d+(\.\d+)*([_\-\s].*)?$",            # "_V2", "_v1.2_NOSECONE"
    r"[_\-\s]*\d{1,2}[.\-/]\d{1,2}([.\-/]\d{2,4})?", # " 29.08.2021", "_04:21"
    r"[_\-\s]*(updated|final|unretuned|dry|actualmass|cadmasses|"
    r"noscone|nosecone|scad|mt|pt)$",
    r"[_\-\s]*\d{1,2}$",                             # trailing _1, _2 (not ids)
]

# Authoritative leading-prefix families (case-insensitive). Any file whose
# basename starts with one of these shares the family, regardless of suffix.
PREFIX_FAMILIES = [
    "APEX", "ASTRA", "Siruis", "Argonia", "NASA_Rocket", "2024_IREC",
    "RocketV1", "IREK", "DarkMatter", "falconHeavey", "ASCENSION",
    "Scale_model_Nasa", "FRED", "organic_G", "candidate_", "osifog",
    "best_candidate", "base_",
]


def stem_family(path):
    """Reduce a filename to a version-independent stem key."""
    stem = os.path.basename(path)
    if stem.lower().endswith(".ork"):
        stem = stem[:-4]
    # 1) authoritative prefix match (keeps APEX_* together even with odd suffixes)
    low = stem.lower()
    for pre in PREFIX_FAMILIES:
        if low.startswith(pre.lower()):
            return "pfx:" + pre.lower()
    # 2) strip version/date/detail suffixes repeatedly
    prev = None
    s = stem
    changed = True
    while changed and s != prev:
        prev = s
        for pat in _SUFFIX_PATTERNS:
            new = re.sub(pat + r"$", "", s, flags=re.IGNORECASE).strip(" _-.")
            if new and new != s:
                s = new
                changed = True
    s = re.sub(r"[_\s]+", " ", s).strip().lower()
    return s


# ----------------------------------------------------------- geometry family


STRUCT = ("nosecone", "bodytube", "transition", "trapezoidfin",
          "freeformfinset", "ellipticalfin", "tubefin")


def _dims(comps):
    """Return an ordered structural profile: a tuple of
    (type, dim1, dim2, ...) for every structural component, in order.
    Two airframes match only if the type sequence is identical AND every dim is
    within TOL. This keeps equal-sized-but-different rockets apart."""
    rows = []

    def num(c, *keys):
        for k in keys:
            if c.get(k):
                return c[k]
        return 0.0

    def walk(c):
        t = c["type"]
        if t in STRUCT:
            if t == "nosecone":
                d = (num(c, "length_m"), num(c, "base_radius_m") * 2)
            elif t == "bodytube":
                d = (num(c, "length_m"), num(c, "outer_d_m"))
            elif t == "transition":
                d = (num(c, "length_m"), num(c, "fore_d_m"), num(c, "aft_d_m"))
            elif t == "tubefin":
                d = (num(c, "outer_d_m") * 2, num(c, "length_m"))
            else:  # fin sets
                d = (num(c, "root_chord_m"), num(c, "tip_chord_m"),
                     num(c, "span_m"), num(c, "sweep_m"),
                     float(c.get("fin_count") or 0))
            rows.append((t,) + d)
        for ch in c.get("contains", []):
            walk(ch)

    for c in comps:
        walk(c)
    return tuple(rows)


def _close(a, b):
    # a value of 0/None means the field is absent in the .ork -> unknown, so it
    # does not block a match (e.g. a bodytube with no stored outer diameter).
    if not a or not b:
        return True
    return abs(a - b) / max(a, b) <= TOL


def geometry_close(d1, d2):
    if d1 is None or d2 is None or len(d1) != len(d2):
        return False
    for r1, r2 in zip(d1, d2):
        if r1[0] != r2[0] or len(r1) != len(r2):
            return False
        if not all(_close(x, y) for x, y in zip(r1[1:], r2[1:])):
            return False
    return True


# --------------------------------------------------------------- union find


class _UF:
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[max(ra, rb)] = min(ra, rb)


def compute_families(paths, dims_by_path):
    """Return dict path -> family_id (smallest member path).

    Stem-family links use union-find. Geometry links are ANCHORED (a file joins
    a geometry family only if it is within tolerance of that family's anchor),
    so similar-but-distinct airframes never chain into one giant family.
    """
    uf = _UF()
    for p in paths:
        uf.find(p)

    # stem links
    by_stem = {}
    for p in paths:
        by_stem.setdefault(stem_family(p), []).append(p)
    for members in by_stem.values():
        for p in members[1:]:
            uf.union(members[0], p)

    # geometry links: anchored to a per-family representative. We only merge two
    # files that are directly close; then a *representative* check keeps chains
    # from forming (compare against the family anchor, not any member).
    items = [(p, dims_by_path.get(p)) for p in paths]
    items = [(p, d) for p, d in items if d]
    anchors = []  # list of (anchor_path, dims)
    for p, d in sorted(items):
        for ap, ad in anchors:
            if geometry_close(ad, d):
                uf.union(ap, p)
                break
        else:
            anchors.append((p, d))

    fam = {}
    for p in paths:
        fam[p] = uf.find(p)
    members = {}
    for p, f in fam.items():
        members.setdefault(f, []).append(p)
    remap = {f: min(ms) for f, ms in members.items()}
    return {p: remap[f] for p, f in fam.items()}, members


def build_all(paths):
    dims = {}
    for p in paths:
        try:
            comps, _ = build_design(p)
            dims[p] = _dims(comps)
        except Exception:
            dims[p] = None
    return compute_families(paths, dims)


if __name__ == "__main__":
    ORK = os.path.join(REPO, "ork")
    paths = sorted("ork/" + f for f in os.listdir(ORK) if f.lower().endswith(".ork"))
    fam, members = build_all(paths)
    multi = {f: ms for f, ms in members.items() if len(ms) > 1}
    print(f"files: {len(paths)}  families: {len(members)}  multi-file families: {len(multi)}")
    print(f"files in multi-file families: {sum(len(v) for v in multi.values())}")
    for f in sorted(multi, key=lambda x: -len(multi[x])):
        print(f"  {len(multi[f]):2d}  {os.path.basename(f):40s} -> {[os.path.basename(m) for m in sorted(multi[f])]}")
