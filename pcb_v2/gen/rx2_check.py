"""
rx2_check.py - proves that the schematic is the simulated circuit.

It does not use the generator's reading of the blocks: it reads the eleven blocks again with its own code,
reads the netlist that kicad-cli exported from the schematic (../rx2_receiver.net) and compares
 1. the set of parts: every part of the blocks is exactly one symbol (found through the symbol's field Sim);
 2. the value of every part: the text against rx2_parts.csv, the number (or the type) against the block;
 3. the connections: the nets of the schematic and the nodes of the blocks must split the pins into the
    same groups, after the _x inductors and Voq are replaced by shorts and the package lines are resolved;
 4. footprint and LCSC number of every part against rx2_parts.csv, and the totals;
 5. the parts outside the simulation (connectors, spare capacitor positions) against the tables below.
Every difference is printed; the last line is "DIFFERENCES: n". Exit code 1 if n is not 0.
Run: <KiCad 10>\\bin\\python.exe rx2_check.py    (after rx2_sch.py)
"""
import csv
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from kisch import parse  # noqa: E402   (only the S-expression reader is shared with the generator)

OUT = os.path.dirname(HERE)
REPO = os.path.dirname(OUT)
SIM = os.path.join(REPO, "fm_receiver_v2", "simulations")
PARTS = os.path.join(REPO, "fm_receiver_v2", "rx2_parts.csv")
NET = os.path.join(OUT, "rx2_receiver.net")

TYPE = {"QN": "MMBT3904", "QP": "MMBT3906", "QRF": "2SC3356", "QIF": "S9018", "DBAS70": "BAS70",
        "DBAV99": "BAV99", "XTAL25": "25MHz", "XTAL14": "14.31818MHz"}
FOOT = {"resistor 0603": "Resistor_SMD:R_0603_1608Metric", "capacitor 0603": "Capacitor_SMD:C_0603_1608Metric",
        "capacitor 1206": "Capacitor_SMD:C_1206_3216Metric", "inductor 0603": "rx2:L_0603_LQW18A",
        "inductor 1008": "rx2:L_1008_AHW2520C", "inductor 1210": "rx2:L_1210_NLV32",
        "transistor SOT-23": "Package_TO_SOT_SMD:SOT-23", "diode SOT-23": "Package_TO_SOT_SMD:SOT-23",
        "crystal 3225": "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm"}
# parts outside the simulation: Sim field -> {pin: node of the blocks, None = must stay unconnected}
FREE = {str(i): None for i in range(1, 20)}
EXTRA = {"ant_sma": {"1": "ant", "2": "0"},
         "devkitc_left": dict(FREE, **{"1": "v3ref", "3": "adc", "14": "0", "19": "v5"}),
         "devkitc_right": dict(FREE, **{"1": "0", "7": "0"})}
SPARE = {"Lr1": ("r1", "0"), "Lr2": ("r2", "0"), "Lr3": ("m1in", "0"), "Lta": ("ta", "0"), "Ltb": ("lo1", "0"),
         "Lt1": ("t1", "cm12"), "Lt2": ("t2", "cm12"), "Lt3": ("t3", "vft3"), "Lt4": ("m2in", "vft4"),
         "L5": ("t5", "vf5"), "L6": ("t6", "vfa")}
ndiff = 0


def diff(msg):
    global ndiff
    ndiff += 1
    if ndiff <= 60:
        print("DIFF " + msg)


def number(s):
    m = re.match(r"\{?(?:tolv\()?([0-9.]+)([a-zA-Z]?)", s)
    return float(m.group(1)) * {"p": 1e-12, "n": 1e-9, "u": 1e-6, "k": 1e3, "M": 1e6}.get(m.group(2), 1.0)


def child(n, k):
    for e in n:
        if isinstance(e, list) and e and e[0] == k:
            return e
    return None


def val(n, k):
    c = child(n, k)
    return str(c[1]) if c is not None and len(c) > 1 and not isinstance(c[1], list) else ""


# ---------------------------------------------------------------- the blocks
alias, inner, sim = {}, {}, {}


def root(n):
    while n in alias:
        n = alias[n]
    return n


def short(a, b):
    a, b = root(a), root(b)
    if a != b:
        alias[a] = b


files = sorted(glob.glob(os.path.join(SIM, "rx2_blk_*.inc")))
if len(files) != 11:
    diff("expected 11 block files, found %d" % len(files))
for path in files:
    with open(path, encoding="utf-8", errors="replace") as f:
        for raw in f:
            w = raw.split()
            if not w or w[0][0] in "*.":
                continue
            n, k = w[0], w[0][0].upper()
            if n.endswith("_x"):
                if k == "X":
                    inner.update(zip(w[4:7], w[1:4]))      # die node -> package pin (collector, base, emitter)
                elif k == "L":
                    short(w[1], w[2])
                elif k != "C":
                    diff("unknown estimate line " + n)
            elif k == "V":
                short(w[1], w[2])                           # Voq
            elif n in sim:
                diff("name used twice in the blocks: " + n)
            elif k in "RCL":
                sim[n] = (k, w[1:3], w[3])
            elif k == "Q":
                sim[n] = ("Q", [w[2], w[3], w[1]], w[5])   # kept as base, emitter, collector = pins 1, 2, 3
            elif k == "D":
                sim[n] = ("D", w[1:3], w[3])               # anode, cathode
            elif k == "X":
                sim[n] = ("X", w[1:3], w[3])
            else:
                diff("unknown line " + n)


def node(x):
    return root(inner.get(x, x))


members = {}
for k, t, v in sim.values():
    for x in t:
        members.setdefault(node(x), set()).update((x, inner.get(x, x)))
for x in alias:
    members.setdefault(root(x), set()).add(x)
members.setdefault(node("0"), set()).add("GND")
members.setdefault(node("vcc"), set()).add("VCC")

# ---------------------------------------------------------------- the schematic's netlist
with open(NET, encoding="utf-8") as f:
    tree = parse(f.read())[0]
comps, pin_net = {}, {}
for e in tree:
    if isinstance(e, list) and e and e[0] == "components":
        for c in e[1:]:
            fields = {}
            for fld in (child(c, "fields") or [])[1:]:
                fields[val(fld, "name")] = fld[-1] if isinstance(fld[-1], str) else ""
            props = {val(p, "name") for p in c if isinstance(p, list) and p and p[0] == "property"}
            comps[val(c, "ref")] = dict(value=val(c, "value"), fp=val(c, "footprint"), fields=fields,
                                        dnp="dnp" in props)
    if isinstance(e, list) and e and e[0] == "nets":
        for n in e[1:]:
            for x in n:
                if isinstance(x, list) and x and x[0] == "node":
                    pin_net[(val(x, "ref"), val(x, "pin"))] = val(n, "name")
with open(PARTS, encoding="utf-8", newline="") as f:
    rows = {r["designator"]: r for r in csv.DictReader(f)}


def label(kn):
    return kn.rsplit("/", 1)[-1] if kn else None


def pick(ref, alts):
    """Resistors, capacitors and inductors have no direction: take the way round that matches the net names."""
    score = [sum(1 for pin, nd in a.items() if label(pin_net.get((ref, pin))) in members.get(nd, ())) for a in alts]
    return alts[score.index(max(score))]


triples, covered, kinds, nextra, nspare = [], [], {}, 0, 0
for ref, c in sorted(comps.items()):
    s = c["fields"].get("Sim", "")
    if s in EXTRA:
        nextra += 1
        triples += [(ref, pin, None if nd is None else node(nd)) for pin, nd in EXTRA[s].items()]
        if not c["fp"]:
            diff("%s (%s) has no footprint" % (ref, s))
        continue
    if s.startswith("spare_") and s[6:] in SPARE:
        nspare += 1
        a, b = (node(x) for x in SPARE[s[6:]])
        triples += [(ref, pin, nd) for pin, nd in pick(ref, [{"1": a, "2": b}, {"1": b, "2": a}]).items()]
        if not c["dnp"] or c["fp"] != FOOT["capacitor 0603"]:
            diff("%s (%s) must be a do-not-populate 0603 capacitor position" % (ref, s))
        if s[6:] not in sim:
            diff("%s: no inductor %s in the blocks" % (ref, s[6:]))
        continue
    names = s.split("+")
    if not s or any(x not in sim for x in names) or s not in rows:
        diff("%s: field Sim '%s' is not a part of the blocks / the parts list" % (ref, s))
        continue
    covered += names
    row = rows[s]
    k, t, v = sim[names[0]]
    t = [node(x) for x in t]
    if len(names) == 2:                                    # BAV99 = two diodes back to back
        k2, t2, v2 = sim[names[1]]
        t2 = [node(x) for x in t2]
        if not (v == v2 == "DBAV99" and t[0] == t2[1]):
            diff("%s: %s is not a pair of BAV99 diodes that share pin 3" % (ref, s))
        exp, k = {"3": t[0], "2": t[1], "1": t2[0]}, "D"
    elif k in "RCL":
        exp = pick(ref, [{"1": t[0], "2": t[1]}, {"1": t[1], "2": t[0]}])
        if abs(number(v) - number(row["value"])) > 1e-6 * number(row["value"]):
            diff("%s (%s): value in the block %s, in the parts list %s" % (ref, s, v, row["value"]))
    elif k == "Q":
        exp = {"1": t[0], "2": t[1], "3": t[2]}
    elif k == "D":
        exp = {"1": t[0], "3": t[1]}
    else:
        exp = {"1": t[0], "3": t[1], "2": node("0"), "4": node("0")}
    kinds[k] = kinds.get(k, 0) + 1
    if k not in "RCL" and TYPE.get(v) != row["value"]:
        diff("%s (%s): model %s in the block, %s in the parts list" % (ref, s, v, row["value"]))
    if c["value"] != row["value"]:
        diff("%s (%s): value '%s' in the schematic, '%s' in the parts list" % (ref, s, c["value"], row["value"]))
    if c["fp"] != FOOT.get(row["type"] + " " + row["package"], "?"):
        diff("%s (%s): footprint '%s' does not fit %s %s" % (ref, s, c["fp"], row["type"], row["package"]))
    if not re.match(r"C\d+$", row["lcsc"]) or c["fields"].get("LCSC") != row["lcsc"]:
        diff("%s (%s): LCSC '%s' in the schematic, '%s' in the parts list" % (
            ref, s, c["fields"].get("LCSC"), row["lcsc"]))
    if c["dnp"]:
        diff("%s (%s) is marked do-not-populate" % (ref, s))
    triples += [(ref, pin, nd) for pin, nd in exp.items()]

for x in sorted(set(sim) - set(covered)):
    diff("part of the blocks without a symbol: " + x)
if len(covered) != len(set(covered)):
    diff("a part of the blocks has more than one symbol")
for x in sorted(set(rows) - {c["fields"].get("Sim") for c in comps.values()}):
    diff("row of the parts list without a symbol: " + x)

# ---------------------------------------------------------------- connections: same split of the pins
n2k, k2n = {}, {}
for ref, pin, nd in triples:
    kn = pin_net.get((ref, pin))
    free = kn is None or kn.startswith("unconnected-")
    if nd is None:
        if not free:
            diff("%s pin %s must stay unconnected, is on net %s" % (ref, pin, kn))
    elif free:
        diff("%s pin %s is not connected (node %s in the blocks)" % (ref, pin, nd))
    else:
        n2k.setdefault(nd, set()).add(kn)
        k2n.setdefault(kn, set()).add(nd)
for nd, ks in sorted(n2k.items()):
    if len(ks) != 1:
        diff("node %s of the blocks is split into the nets %s" % (nd, sorted(ks)))
for kn, ns in sorted(k2n.items()):
    if len(ns) != 1:
        diff("net %s joins the nodes %s of the blocks" % (kn, sorted(ns)))
known = {(r, p) for r, p, nd in triples}
for (r, p), kn in sorted(pin_net.items()):
    if (r, p) not in known:
        diff("pin %s.%s (net %s) is not expected from the blocks" % (r, p, kn))

want = {"R": 104, "C": 92, "L": 11, "Q": 38, "D": 5, "X": 2}
if kinds != want or sum(kinds.values()) != len(rows):
    diff("totals: %s, expected %s and %d rows in the parts list" % (kinds, want, len(rows)))
if nextra != 3 or nspare != 11:
    diff("parts outside the simulation: %d connectors (3 expected), %d spare positions (11 expected)" % (nextra, nspare))
print("parts of the blocks with a symbol: %d (%s); parts list rows: %d" % (
    sum(kinds.values()), ", ".join("%s %d" % (k, kinds.get(k, 0)) for k in "RCLQDX"), len(rows)))
print("outside the simulation: %d connectors, %d spare capacitor positions; symbols in all: %d" % (
    nextra, nspare, len(comps)))
print("connections: %d pins compared, %d nodes in the blocks, %d nets in the schematic" % (
    len([t for t in triples if t[2] is not None]), len(n2k), len(k2n)))
print("DIFFERENCES: %d" % ndiff)
sys.exit(1 if ndiff else 0)
