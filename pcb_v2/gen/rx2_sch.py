"""
rx2_sch.py - builds the KiCad 10 schematic of receiver version 2 from the simulation blocks.

Reads   ../../fm_receiver_v2/simulations/rx2_blk_*.inc   the circuit: eleven SPICE blocks
        ../../fm_receiver_v2/rx2_parts.csv               value, package and LCSC number of every part
Writes  ../rx2_receiver.kicad_pro, ../rx2_receiver.kicad_sch (root) and one sheet per block,
        ../rx2.kicad_sym and ../sym-lib-table (one project symbol), ../rx2_refs.csv (netlist name ->
        schematic reference), then runs kicad-cli: ERC (../erc.json), netlist (../rx2_receiver.net)
        and PDF (../rx2_receiver.pdf).
Run     <KiCad 10>\\bin\\python.exe rx2_sch.py     and then     <KiCad 10>\\bin\\python.exe rx2_check.py

How a line of a block becomes a symbol (rx2_check.py codes the same rules a second time, on its own):
 - R, C, L, Q, D lines and the crystals Xq25 / Xq14 are parts. Node 0 is ground, vcc the 3.3 V rail.
 - A name ending in _x is a layout estimate, not a part: a capacitor is left out, an inductor is a short
   (its two nodes are one net), and an X..._x line is the SOT-23 package model: its first three nodes are
   the collector, base and emitter of the transistor whose die sits on its last three nodes.
 - Voq is a zero-volt source: its two nodes are one net.
 - Two DBAV99 diodes back to back are one BAV99 package.
Every pin gets a short wire with a net label (the node name of the simulation), so the connections are
made by name. Nothing is edited by hand: change the blocks or the tables below and run again.
"""
import csv
import glob
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kisch  # noqa: E402

OUT = os.path.dirname(HERE)
REPO = os.path.dirname(OUT)
SIM = os.path.join(REPO, "fm_receiver_v2", "simulations")
PARTS = os.path.join(REPO, "fm_receiver_v2", "rx2_parts.csv")
NAME = "rx2_receiver"
CLI = os.path.join(kisch.KICAD, "bin", "kicad-cli.exe")
POWER = ("GND", "VCC")

kisch.REV = "schematic of 2026-11-14"
kisch.COMPANY = "Edy Grigore"
kisch.ROOT_TITLE = "QFH 137 MHz receiver, version 2"
kisch.SHOW = ("Sim",)

# block file, sheet title (no colon), layout rules that apply to the sheet
SHEETS = [
    ("fe", "1 Front end 137.9 MHz", [
        "Rule 6: every tuned circuit has a spare 0603 capacitor position next to its inductor (value 'spare', not fitted)."]),
    ("lo1osc", "2 Oscillator 25 MHz", []),
    ("lo1mul", "3 Multiplier to 125 MHz", [
        "Rule 4: node 'eq' (the two squarer emitters and Rqs) as small as possible, under 1 pF.",
        "Rule 6: spare capacitor positions on TA and TB (value 'spare', not fitted).",
        "Rule 8: the collector of Qq1 reaches Cfq2 within about 4 mm of track (8 nH there makes the pair oscillate)."]),
    ("mix1", "4 Mixer 1", []),
    ("if1", "5 First IF 12.9 MHz", [
        "Rule 1: the strip runs in a straight line, T1 at one end and T4 at the other; nothing from the output side runs back along it.",
        "Rule 2: T2 and T4 at least 15 to 20 mm apart; neighbouring inductors at right angles; ground pour and vias between the stages;",
        "        input and output of each pair apart (0.5 pF across pair 2 is fine, 1 pF oscillates).",
        "        The strip tolerates 0.1 pF from T4 back to T2 and a coupling factor of 0.002 between Lt2 and Lt4.",
        "Ground: unbroken under the whole strip (the board has 2 layers).",
        "Rule 6: spare capacitor positions on T1 to T4 (value 'spare', not fitted).",
        "Rule 7: the pump driver and the detector of the second IF (sheet 8) stay 50 mm or more from T1 to T4."]),
    ("lo2", "6 Oscillator 14.318 MHz", []),
    ("mix2", "7 Mixer 2", []),
    ("if2", "8 Second IF 1.418 MHz and detector", [
        "Rule 1: the strip runs in a straight line, T5 / L5 at one end, the pump driver (pair C) and the detector at the other.",
        "Rule 3: node 'c2' carries a 1.65 V square wave and 0.005 pF from 'c2' to T5 closes the loop: keep pair C and the detector",
        "        25 mm or more from T5 / L5, solid ground under and between, 'c2' and 'x' as short as possible,",
        "        L5 and L6 apart and at right angles (coupling factor under 0.007), T6 to T5 under 1 pF.",
        "Ground: unbroken under the whole strip (the board has 2 layers).",
        "Rule 6: spare capacitor positions on T5 and T6 (value 'spare', not fitted).",
        "Rule 7: pair C and the detector 50 mm or more from the first-IF tuned circuits (sheet 5), unbroken ground between:",
        "        the 9th harmonic of c2 lies in the first IF, and the second IF can lock itself at LO2 / 10 = 1.4318 MHz."]),
    ("audio", "9 Audio chain", [
        "Rule 5: Cadc sits at the DevKitC pin (GPIO36 = pin 3 of the left socket, sheet 10), away from T6 and node 'c2'."]),
    ("reg", "10 Regulator and DevKitC", [
        "Rule 5: Cadc (sheet 9) sits at pin 3 of the left DevKitC socket."]),
    ("bias", "11 Bias references", []),
]

MODEL = {"QN": "MMBT3904", "QP": "MMBT3906", "QRF": "2SC3356", "QIF": "S9018", "DBAS70": "BAS70",
         "DBAV99": "BAV99", "XTAL25": "25MHz", "XTAL14": "14.31818MHz"}
# part type -> symbol; the pin numbers used are in build() below and in ../README.md
SYMBOL = {"resistor": "Device:R", "capacitor": "Device:C", "inductor": "Device:L",
          "crystal": "Device:Crystal_GND24", "NPN": "Transistor_BJT:Q_NPN_BEC", "PNP": "Transistor_BJT:Q_PNP_BEC",
          "BAS70": "rx2:D_Schottky_A1_K3", "BAV99": "Device:D_Dual_Series_AKC"}
FOOTPRINT = {("resistor", "0603"): "Resistor_SMD:R_0603_1608Metric",
             ("capacitor", "0603"): "Capacitor_SMD:C_0603_1608Metric",
             ("capacitor", "1206"): "Capacitor_SMD:C_1206_3216Metric",
             ("inductor", "0603"): "rx2:L_0603_LQW18A",
             ("inductor", "1008"): "rx2:L_1008_AHW2520C",
             ("inductor", "1210"): "rx2:L_1210_NLV32",
             ("transistor", "SOT-23"): "Package_TO_SOT_SMD:SOT-23",
             ("diode", "SOT-23"): "Package_TO_SOT_SMD:SOT-23",
             ("crystal", "3225"): "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm"}
SOCKET = "Connector_PinSocket_2.54mm:PinSocket_1x19_P2.54mm_Vertical"
# parts that are not in the simulation:
# block -> (heading, notes, [(name, symbol, value, footprint, {pin: node}, fields)])
EXTRA = {
    "fe": ("Antenna connector (not in the simulation)",
           ["SMA jack LCSC C496549 (BWSMA-KE-Z001). Its data sheet shows a vertical through-hole jack, not an edge type:",
            "four legs on a 5.08 mm square and a centre pin, five holes of 1.4 mm. Soldered by hand; not placed by JLCPCB."],
           [("ant_sma", "Connector:Conn_Coaxial", "SMA", "rx2:SMA_BWSMA-KE-Z001_Vertical",
             {1: "ant", 2: "0"}, {"LCSC": "C496549", "MPN": "BWSMA-KE-Z001", "Assembly": "by hand"})]),
    "reg": ("ESP32 DevKitC, 38 pins (not in the simulation)",
            ["Two 1x19 sockets, 2.54 mm, soldered by hand (LCSC C2932678); the DevKitC plugs in. Rows 25.4 mm apart, as on version 1.",
             "Pins used (Espressif's pin table of the DevKitC V4): left row J2 pin 1 = 3V3 (v3ref), pin 3 = GPIO36 / VP (adc), pin 14 = GND,",
             "pin 19 = 5V (v5); right row J3 pins 1 and 7 = GND. Pin 1 is at the antenna end of the module. All other pins stay free."],
            [("devkitc_left", "Connector:Conn_01x19_Socket", "DevKitC_left", SOCKET,
              {1: "v3ref", 3: "adc", 14: "0", 19: "v5"},
              {"LCSC": "C2932678", "MPN": "KH-2.54FH-1X19P-H8.5", "Assembly": "by hand"}),
             ("devkitc_right", "Connector:Conn_01x19_Socket", "DevKitC_right", SOCKET, {1: "0", 7: "0"},
              {"LCSC": "C2932678", "MPN": "KH-2.54FH-1X19P-H8.5", "Assembly": "by hand"})]),
}
# one spare capacitor position per tuned circuit: (inductor, part whose two nodes the position shares)
SPARE = [("Lr1", "Cr1b"), ("Lr2", "Lr2"), ("Lr3", "Lr3"), ("Lta", "Cta2"), ("Ltb", "Ctb2"), ("Lt1", "Ct1b"),
         ("Lt2", "Ct2b"), ("Lt3", "Ct3b"), ("Lt4", "Ct4b"), ("L5", "C5b"), ("L6", "C6b")]
MULT = {"p": 1e-12, "n": 1e-9, "u": 1e-6, "k": 1e3, "M": 1e6}


def num(s):
    m = re.match(r"([0-9.]+)([a-zA-Z]?)", s)
    return float(m.group(1)) * MULT.get(m.group(2), 1.0)


def plain(v):
    """'{tolv(68n,tolLr)}' -> '68n', '{6.8p+strv(0.25p)*tolS}' -> '6.8p'"""
    m = re.match(r"\{tolv\(([^,]+),", v) or re.match(r"\{([^+{}]+)\+strv", v)
    return m.group(1) if m else v


def read_blocks():
    """-> {block: [("note", text) or ("part", dict)]}; the nodes of the parts are schematic net names."""
    alias, inner, blocks = {}, {}, {}

    def find(n):
        while n in alias:
            n = alias[n]
        return n

    def short(a, b):
        a, b = find(a), find(b)
        if a != b:
            alias[a] = b

    for key, _title, _rules in SHEETS:
        items = []
        with open(os.path.join(SIM, "rx2_blk_%s.inc" % key), encoding="utf-8", errors="replace") as f:
            for raw in f:
                line = raw.rstrip()
                if not line.strip():
                    continue
                if line[0] == "*":
                    items.append(("note", line[1:]))
                    continue
                w = line.split()
                name, k = w[0], w[0][0].upper()
                if name.endswith("_x"):
                    if k == "L":
                        short(w[1], w[2])
                    elif k == "X" and w[7] == "SOT23X":
                        inner.update(zip(w[4:7], w[1:4]))
                    elif k != "C":
                        raise SystemExit("do not know the estimate line: " + line)
                    continue
                if k == "V" and name == "Voq":
                    short(w[1], w[2])
                    continue
                if k in "RCL":
                    p = dict(kind=k, nodes=w[1:3], val=plain(w[3]))
                elif k == "Q" and w[4] == "0":
                    p = dict(kind="Q", nodes=w[1:4], val=w[5])
                elif k == "D":
                    p = dict(kind="D", nodes=w[1:3], val=w[3])
                elif k == "X" and w[3] in ("XTAL25", "XTAL14"):
                    p = dict(kind="Y", nodes=w[1:3], val=w[3])
                else:
                    raise SystemExit("do not know the line: " + line)
                p.update(name=name, block=key)
                items.append(("part", p))
        blocks[key] = items
    # package-internal nodes -> pins; shorted nodes -> one name per group
    seen = []
    for items in blocks.values():
        for kind, p in items:
            if kind == "part":
                p["nodes"] = [inner.get(n, n) for n in p["nodes"]]
                seen.extend(p["nodes"])
    first = {}
    for i, n in enumerate(seen):
        first.setdefault(n, i)
    group = {}
    for n in list(first) + list(alias):
        group.setdefault(find(n), set()).add(n)
    name_of = {}
    for members in group.values():
        best = min(members, key=lambda n: (0 if n == "0" else 1 if n == "vcc" else 2, first.get(n, 10 ** 9), n))
        for n in members:
            name_of[n] = {"0": "GND", "vcc": "VCC"}.get(best, best)
    for key, items in blocks.items():
        out, hold = [], None
        for kind, p in items:
            if kind == "part":
                p["nodes"] = [name_of[n] for n in p["nodes"]]
                if p["kind"] == "D" and p["val"] == "DBAV99":
                    if hold is None:
                        hold = p
                        out.append((kind, p))
                    else:   # second diode of the pair: join it with the first
                        a, b = hold["nodes"], p["nodes"]
                        if a[0] != b[1] or a[1] != b[0]:
                            raise SystemExit("BAV99 diodes not back to back: %s %s" % (hold["name"], p["name"]))
                        hold.update(kind="DD", name=hold["name"] + "+" + p["name"], nodes=[a[0], a[1], b[0]])
                        hold = None
                    continue
            out.append((kind, p))
        if hold is not None:
            raise SystemExit("single BAV99 diode in block " + key)
        blocks[key] = out
    return blocks, name_of


def tidy(lines, first):
    """Comment lines of a block -> text lines for the sheet (the notes about deck parameters are left out)."""
    out, skip = [], False
    for t in lines:
        if "deck must define" in t:
            skip = True
            continue
        if skip and t.startswith("   "):
            continue
        skip = False
        if t.strip():
            out.append(t.strip())
    if first and out:
        out[0] = re.sub(r"^rx2_blk_\w+\.inc - ", "", out[0])
        out[0] = out[0][:1].upper() + out[0][1:]
    return out


def build(P, i, key, title, rules, blocks, name_of, rows, GLOB, paper, width):
    s = P.sheet("rx2_%02d_%s.kicad_sch" % (i, key), title, paper)
    s.start_layout(width=width)
    count, placed = {}, []
    byname = {p["name"]: p for items in blocks.values() for kind, p in items if kind == "part"}

    def put(prefix, sim, lib_id, value, conns, fp, props, dnp=False):
        count[prefix] = count.get(prefix, 0) + 1
        ref = "%s%d" % (prefix, i * 100 + count[prefix])
        s.auto(ref, lib_id, value, conns, fp, dict(props, Sim=sim), glob=GLOB, power=POWER, dnp=dnp)
        placed.append((sim, ref, str(i), value, fp, props.get("LCSC", ""), "no" if dnp else "yes"))

    def two(a, b):   # resistors, capacitors, inductors have no direction: ground goes down, the rail up
        if (a == "GND" and b != "GND") or (b == "VCC" and a != "VCC"):
            a, b = b, a
        return {1: a, 2: b}

    if rules:
        s.block("Layout rules for this sheet (from the design log)", rules)
    pending, first = [], True
    for kind, p in blocks[key]:
        if kind == "note":
            pending.append(p)
            continue
        lines = tidy(pending, first)
        if lines:
            s.block(lines[0], lines[1:])
        pending, first = [], False
        row = rows[p["name"]]
        n, fp = p["nodes"], FOOTPRINT[(row["type"], row["package"])]
        props = {"LCSC": row["lcsc"], "MPN": row["mpn"], "Assembly": "JLCPCB"}
        if p["kind"] in ("R", "C", "L"):
            if abs(num(p["val"]) - num(row["value"])) > 1e-6 * num(row["value"]):
                raise SystemExit("%s: block says %s, parts list says %s" % (p["name"], p["val"], row["value"]))
            put(p["kind"], p["name"], SYMBOL[row["type"]], row["value"], two(*n), fp, props)
            continue
        if MODEL[p["val"]] != row["value"]:
            raise SystemExit("%s: block says %s, parts list says %s" % (p["name"], p["val"], row["value"]))
        if p["kind"] == "Q":     # SPICE order collector, base, emitter -> pins 3, 1, 2
            pnp = p["val"] == "QP"
            if (row["spec"] == "PNP") != pnp:
                raise SystemExit("%s: NPN / PNP differs between block and parts list" % p["name"])
            put("Q", p["name"], SYMBOL["PNP" if pnp else "NPN"], row["value"], {3: n[0], 1: n[1], 2: n[2]}, fp, props)
        elif p["kind"] == "D":   # BAS70: anode pin 1, cathode pin 3
            put("D", p["name"], SYMBOL["BAS70"], row["value"], {1: n[0], 3: n[1]}, fp, props)
        elif p["kind"] == "DD":  # BAV99: common pin 3 to the node, pins 1 and 2 to the other side
            put("D", p["name"], SYMBOL["BAV99"], row["value"], {3: n[0], 2: n[1], 1: n[2]}, fp, props)
        else:                    # crystal: pads 1 and 3, pads 2 and 4 (the can) to ground
            put("Y", p["name"], SYMBOL["crystal"], row["value"], {1: n[0], 3: n[1], "G": "GND"}, fp, props)
    lines = tidy(pending, False)
    if lines:
        s.block(lines[0], lines[1:])
    if key in EXTRA:
        head, notes, parts = EXTRA[key]
        s.block(head, notes)
        for sim, lib_id, value, fp, conns, props in parts:
            put("J", sim, lib_id, value, {pin: name_of[nd] for pin, nd in conns.items()}, fp, props)
    spare = [(ind, like) for ind, like in SPARE if byname[ind]["block"] == key]
    if spare:
        s.block("Spare capacitor positions, not fitted (not in the simulation)",
                ["One empty 0603 position per tuned circuit, across the same two nodes as %s:" %
                 ", ".join("%s (%s)" % (like, ind) for ind, like in spare),
                 "a place for a correction capacitor if a tuned circuit comes out off frequency. "
                 "Marked do-not-populate; not in the BOM."])
        for ind, like in spare:
            a, b = byname[like]["nodes"]
            put("C", "spare_" + ind, "Device:C", "spare", two(a, b), FOOTPRINT[("capacitor", "0603")],
                {"Assembly": "not fitted"}, dnp=True)
    if key == "reg":
        s.block("Power flags (they only tell the electrical rules check that GND and VCC are driven)")
        s.auto_flag("GND", power=POWER)
        s.auto_flag("VCC", power=POWER)
    return s, placed


def project_symbol():
    """rx2:D_Schottky_A1_K3 = Device:D_Schottky with the pins numbered as in a single SOT-23 diode."""
    sym = kisch.resolve_symbol("Device:D_Schottky")
    QT, name = type(sym[1]), "D_Schottky_A1_K3"
    sym[1] = QT(name)
    for e in sym:
        if isinstance(e, list) and e and e[0] == "symbol":
            e[1] = QT(str(e[1]).replace("D_Schottky", name, 1))
            for p in e:
                if isinstance(p, list) and p and p[0] == "pin":
                    nu, nm = kisch._child(p, "number"), kisch._child(p, "name")
                    nu[1] = QT({"A": "1", "K": "3"}[str(nm[1])])
        if isinstance(e, list) and e and e[0] == "property" and str(e[1]) == "Description":
            e[2] = QT("Schottky diode in SOT-23: pin 1 anode, pin 3 cathode, pin 2 not connected")
    with open(os.path.join(kisch.SYMDIR, "Device.kicad_sym"), encoding="utf-8") as f:
        ver = re.search(r"\(version (\d+)\)", f.read(600)).group(1)
    path = os.path.join(OUT, "rx2.kicad_sym")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write('(kicad_symbol_lib\n\t(version %s)\n\t(generator "rx2_sch")\n\t(generator_version "10.0")\n%s\n)\n'
                % (ver, kisch.dump(sym, 1)))
    with open(os.path.join(OUT, "sym-lib-table"), "w", encoding="utf-8", newline="\n") as f:
        f.write('(sym_lib_table\n  (version 7)\n  (lib (name "rx2")(type "KiCad")(uri "${KIPRJMOD}/rx2.kicad_sym")'
                '(options "")(descr "receiver version 2: project symbols"))\n)\n')
    kisch.LIBPATHS["rx2"] = path
    kisch.FPLIBS["rx2"] = os.path.join(OUT, "rx2.pretty")       # written by rx2_fp.py
    with open(os.path.join(OUT, "fp-lib-table"), "w", encoding="utf-8", newline="\n") as f:
        f.write('(fp_lib_table\n  (version 7)\n  (lib (name "rx2")(type "KiCad")(uri "${KIPRJMOD}/rx2.pretty")'
                '(options "")(descr "receiver version 2: project footprints"))\n)\n')


def cli(*args):
    r = subprocess.run([CLI] + list(args), capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-600:], r.stderr[-600:])
        raise SystemExit("kicad-cli failed: " + " ".join(args[:3]))


ROOT_TEXT = [
    (2.2, "QFH 137 MHz weather-satellite receiver, version 2: all discrete, assembled by JLCPCB"),
    (1.5, "Signal: antenna 137.9 MHz -> 1 front end -> 4 mixer 1 (LO 125 MHz from 2 and 3) -> 5 first IF 12.9 MHz"),
    (1.5, "-> 7 mixer 2 (LO 14.318 MHz from 6) -> 8 second IF 1.418 MHz, limiter, detector -> 9 audio -> ESP32 DevKitC, GPIO36."),
    (1.5, "Power: 10 regulator (rail VCC, 3.3 V: copies the DevKitC's 3V3 pin, fed from its 5V pin), 11 the bias references vb and vbd."),
    (1.5, ""),
    (1.5, "This schematic is generated by pcb_v2/gen/rx2_sch.py from the simulation blocks fm_receiver_v2/simulations/rx2_blk_*.inc."),
    (1.5, "Net names are the node names of the simulation. Under each value stands the part's name in the simulation (field Sim)."),
    (1.5, "Reference numbers: sheet number x 100 + running number, in the order of the block file."),
    (1.5, "pcb_v2/gen/rx2_check.py compares the exported netlist with the blocks: parts, values, connections, footprints, LCSC numbers."),
    (1.5, ""),
    (1.5, "Board: 2 layers, at most 100 x 100 mm, all parts on the top side, unbroken ground under both IF strips."),
    (1.5, "Layout rules from the design log (each one is repeated on the sheet it applies to):"),
    (1.5, "1  each IF strip in a straight line, input at one end, output at the other"),
    (1.5, "2  first IF: T2 and T4 15 to 20 mm apart, neighbouring inductors at right angles, ground and vias between stages"),
    (1.5, "3  second IF: node c2 and the detector 25 mm or more from T5 / L5; c2 and x short; L5 and L6 apart and at right angles"),
    (1.5, "4  squarer: node eq as small as possible, under 1 pF"),
    (1.5, "5  Cadc at the DevKitC pin, away from T6 and c2"),
    (1.5, "6  a spare capacitor position on every tuned circuit (11 in all, not fitted)"),
    (1.5, "7  pump driver and detector 50 mm or more from the first-IF tuned circuits (self-lock at LO2 / 10)"),
    (1.5, "8  squarer: the collector of Qq1 within about 4 mm of its bypass capacitor Cfq2"),
]


def main():
    with open(PARTS, encoding="utf-8", newline="") as f:
        rows = {r["designator"]: r for r in csv.DictReader(f)}
    blocks, name_of = read_blocks()
    project_symbol()
    use = {}
    for key, items in blocks.items():
        for kind, p in items:
            if kind == "part":
                for n in p["nodes"]:
                    use.setdefault(n, set()).add(key)
    for key, (_h, _n, parts) in EXTRA.items():
        for part in parts:
            for nd in part[4].values():
                use.setdefault(name_of[nd], set()).add(key)
    GLOB = tuple(sorted(n for n, ks in use.items() if len(ks) > 1 and n not in POWER))
    print("nets shared between sheets (global labels): " + " ".join(GLOB))
    for old in glob.glob(os.path.join(OUT, "rx2_??_*.kicad_sch")):
        os.remove(old)
    P = kisch.Project(NAME, OUT)
    P.root.paper = "A3"
    refs = []
    for i, (key, title, rules) in enumerate(SHEETS, 1):
        s, placed = build(P, i, key, title, rules, blocks, name_of, rows, GLOB, "A3", 395.0)
        if s.max_y > 268:   # does not fit above the title block: one paper size larger
            P.sheets.pop()
            s, placed = build(P, i, key, title, rules, blocks, name_of, rows, GLOB, "A2", 570.0)
        print("sheet %-36s %3d symbols, %s, used height %3.0f mm" % (title, len(placed), s.paper, s.max_y))
        refs += placed
    sims = [x for r in refs for x in r[0].split("+")]
    missing = sorted(set(rows) - {r[0] for r in refs})
    if missing or len(sims) != len(set(sims)):
        raise SystemExit("parts list rows without a symbol: %s" % missing)
    y = 30.0
    for size, line in ROOT_TEXT:
        if line:
            P.root.text(line, (205.0, y), size=size)
        y += size * 2.4
    P.write()
    pro = os.path.join(OUT, NAME + ".kicad_pro")
    if not os.path.exists(pro):
        shutil.copy(os.path.join(kisch.KICAD, "share", "kicad", "template", "kicad.kicad_pro"), pro)
    with open(os.path.join(OUT, "rx2_refs.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sim", "ref", "sheet", "value", "footprint", "lcsc", "fitted"])
        w.writerows(refs)
    print("written: %d symbols on %d sheets, rx2_refs.csv" % (len(refs), len(P.sheets)))
    sch = os.path.join(OUT, NAME + ".kicad_sch")
    erc = os.path.join(OUT, "erc.json")
    cli("sch", "erc", "--format", "json", "--severity-all", "-o", erc, sch)
    cli("sch", "export", "netlist", "-o", os.path.join(OUT, NAME + ".net"), sch)
    cli("sch", "export", "pdf", "-o", os.path.join(OUT, NAME + ".pdf"), sch)
    with open(erc, encoding="utf-8") as f:
        rep = json.load(f)
    count, example = {}, {}
    for sh in rep.get("sheets", []):
        for v in sh.get("violations", []):
            k = (v.get("severity", "?"), v.get("type", "?"))
            count[k] = count.get(k, 0) + 1
            example.setdefault(k, "%s | %s | %s" % (sh.get("path", ""), v.get("description", ""),
                                                   "; ".join(x.get("description", "") for x in v.get("items", []))))
    for k in sorted(count):
        print("ERC %-8s %-26s x%-3d e.g. %s" % (k[0], k[1], count[k], example[k][:210]))
    print("ERC: %d errors, %d warnings" % (sum(c for k, c in count.items() if k[0] == "error"),
                                           sum(c for k, c in count.items() if k[0] == "warning")))


if __name__ == "__main__":
    main()
