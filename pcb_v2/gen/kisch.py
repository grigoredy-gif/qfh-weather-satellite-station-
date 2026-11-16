"""
kisch.py - tiny KiCad 10 schematic writer.

I wrote it for another board of mine; this copy was taken on 2026-11-14 for receiver version 2.
Changes for this project: power symbol VCC, pins stacked on one position are wired once, parts marked
do-not-populate are left out of the BOM, and the fields named in SHOW are drawn under the value.

Every pin gets a short wire stub ending in a net label (local label, global label
or power symbol), so connectivity is defined by net names, not by drawn wires.
Symbols are copied verbatim from the installed KiCad 10 libraries and embedded in
each sheet's lib_symbols block. Only rotation 0 is used, so pin positions are
simply (X + px, Y - py).

Run with KiCad's bundled Python (no extra packages needed).
"""
import os
import re
import uuid

KICAD = r"C:\Users\grigo\AppData\Local\Programs\KiCad\10.0"
SYMDIR = os.path.join(KICAD, "share", "kicad", "symbols")
FPDIR = os.path.join(KICAD, "share", "kicad", "footprints")
SCH_VERSION = "20251024"
NS = uuid.UUID("6f1c2a52-6b0e-4c55-9d1a-1d3f6a7b8c90")
GRID = 1.27
REV = "draft"
COMPANY = "Edy Grigore"
ROOT_TITLE = "root"
SHOW = ()   # names of extra fields that are drawn under the value instead of hidden
GLOB_STUB = 7.62   # extra stub length for global labels, so their box clears the text of the neighbouring pins


def uid(*parts):
    return str(uuid.uuid5(NS, "/".join(str(p) for p in parts)))


# ----------------------------------------------------------------- S-expressions
class Q(str):
    """A quoted string atom."""


def parse(text):
    tok = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+')
    stack, cur = [], []
    for m in tok.finditer(text):
        t = m.group(0)
        if t == "(":
            stack.append(cur)
            cur = []
        elif t == ")":
            done = cur
            cur = stack.pop()
            cur.append(done)
        elif t.startswith('"'):
            cur.append(Q(t[1:-1].replace('\\"', '"').replace("\\\\", "\\")))
        else:
            cur.append(t)
    return cur


def dump(x, ind=0):
    if isinstance(x, list):
        if not x:
            return "()"
        simple = all(not isinstance(e, list) for e in x)
        if simple:
            return "(" + " ".join(dump(e) for e in x) + ")"
        out = "(" + dump(x[0])
        for e in x[1:]:
            if isinstance(e, list):
                out += "\n" + "\t" * (ind + 1) + dump(e, ind + 1)
            else:
                out += " " + dump(e)
        return out + "\n" + "\t" * ind + ")"
    if isinstance(x, Q):
        return '"' + x.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return str(x)


def q(s):
    return Q(str(s))


def fmt(v):
    v = round(v, 4)
    s = ("%.4f" % v).rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


# ----------------------------------------------------------------- libraries
_libcache = {}
LIBPATHS = {}  # project libraries: name -> path of the .kicad_sym


def _lib(name):
    if name not in _libcache:
        path = LIBPATHS.get(name) or os.path.join(SYMDIR, name + ".kicad_sym")
        with open(path, encoding="utf-8") as f:
            root = parse(f.read())[0]
        syms = {}
        for e in root:
            if isinstance(e, list) and e and e[0] == "symbol":
                syms[str(e[1])] = e
        _libcache[name] = syms
    return _libcache[name]


def _child(node, key):
    for e in node:
        if isinstance(e, list) and e and e[0] == key:
            return e
    return None


def resolve_symbol(lib_id):
    """Return the full (extends-resolved) symbol node named 'Lib:Name'."""
    lib, name = lib_id.split(":", 1)
    syms = _lib(lib)
    if name not in syms:
        raise KeyError("symbol %s not found" % lib_id)
    node = syms[name]
    ext = _child(node, "extends")
    if ext is None:
        sym = _deep(node)
    else:
        parent = resolve_symbol(lib + ":" + str(ext[1]))
        pname = str(parent[1]).split(":", 1)[1]
        # child properties replace the parent's key by key; the parent's other properties are kept
        child = {str(e[1]): _deep(e) for e in node if isinstance(e, list) and e and e[0] == "property"}
        sym = []
        for e in _deep(parent):
            if isinstance(e, list) and e and e[0] == "property" and str(e[1]) in child:
                sym.append(child.pop(str(e[1])))
            else:
                sym.append(e)
        last = max(i for i, e in enumerate(sym) if isinstance(e, list) and e and e[0] == "property")
        sym = sym[:last + 1] + list(child.values()) + sym[last + 1:]
        for e in sym:
            if isinstance(e, list) and e and e[0] == "symbol":
                e[1] = Q(str(e[1]).replace(pname + "_", name + "_", 1))
    sym[1] = Q(lib_id)
    return sym


def _deep(x):
    return [_deep(e) for e in x] if isinstance(x, list) else x


def symbol_pins(sym):
    """List of dicts: number, name, x, y, angle, unit, type, hidden."""
    base = str(sym[1]).split(":", 1)[1]
    pins = []
    for e in sym:
        if not (isinstance(e, list) and e and e[0] == "symbol"):
            continue
        m = re.match(re.escape(base) + r"_(\d+)_(\d+)$", str(e[1]))
        unit = int(m.group(1)) if m else 0
        style = int(m.group(2)) if m else 1
        if style not in (0, 1):
            continue
        for p in e:
            if isinstance(p, list) and p and p[0] == "pin":
                at = _child(p, "at")
                nm = _child(p, "name")
                nu = _child(p, "number")
                hidden = any(isinstance(z, list) and z and z[0] == "hide" and z[1] == "yes" for z in p) or "hide" in p
                pins.append(dict(number=str(nu[1]), name=str(nm[1]), x=float(at[1]), y=float(at[2]),
                                 angle=int(float(at[3])) if len(at) > 3 else 0, unit=unit,
                                 type=str(p[1]), hidden=hidden))
    return pins


FPLIBS = {}  # project footprint libraries: name -> path of the .pretty folder


def footprint_exists(fp):
    if not fp:
        return True
    lib, name = fp.split(":", 1)
    base = FPLIBS.get(lib) or os.path.join(FPDIR, lib + ".pretty")
    return os.path.exists(os.path.join(base, name + ".kicad_mod"))


OUT = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}  # screen direction away from the body
LABEL_ANGLE = {(-1, 0): 180, (1, 0): 0, (0, 1): 270, (0, -1): 90}


# ----------------------------------------------------------------- schematic sheet
class Sheet:
    def __init__(self, project, filename, title, paper="A3"):
        self.project, self.filename, self.title, self.paper = project, filename, title, paper
        self.uuid = uid("sheet", filename)
        self.libsyms = {}
        self.items = []
        self.parts = []      # (ref, lib_id, value, footprint, {pin: net})
        self.texts = []
        self._many = False   # True while connecting a part with more than 3 pins
        self.path = None     # instance path, set by Project
        self.prefix = "%02d" % 0  # unique per sheet, set by Project

    # ---- primitives
    def _lib(self, lib_id):
        if lib_id not in self.libsyms:
            self.libsyms[lib_id] = resolve_symbol(lib_id)
        return self.libsyms[lib_id]

    def wire(self, a, b):
        self.items.append(["wire", ["pts", ["xy", fmt(a[0]), fmt(a[1])], ["xy", fmt(b[0]), fmt(b[1])]],
                           ["stroke", ["width", "0"], ["type", "default"]], ["uuid", q(uid(self.filename, "w", a, b))]])

    def label(self, net, at, d, kind="local", shape="bidirectional"):
        ang = LABEL_ANGLE[d]
        just = ["justify", "left"] if ang in (0, 90) else ["justify", "right"]
        if kind == "global":
            self.items.append(["global_label", q(net), ["shape", shape],
                               ["at", fmt(at[0]), fmt(at[1]), str(ang)], ["fields_autoplaced", "yes"],
                               ["effects", ["font", ["size", "1.27", "1.27"]], just],
                               ["uuid", q(uid(self.filename, "gl", net, at))],
                               ["property", q("Intersheetrefs"), q("${INTERSHEET_REFS}"),
                                ["at", fmt(at[0]), fmt(at[1]), "0"],
                                ["effects", ["font", ["size", "1.27", "1.27"]], just, ["hide", "yes"]]]])
        else:
            jb = ["justify", "left", "bottom"] if ang in (0, 90) else ["justify", "right", "bottom"]
            self.items.append(["label", q(net), ["at", fmt(at[0]), fmt(at[1]), str(ang)],
                               ["effects", ["font", ["size", "1.27", "1.27"]], jb],
                               ["uuid", q(uid(self.filename, "ll", net, at))]])

    def noconnect(self, at):
        self.items.append(["no_connect", ["at", fmt(at[0]), fmt(at[1])], ["uuid", q(uid(self.filename, "nc", at))]])

    def text(self, s, at, size=1.27):
        self.items.append(["text", q(s), ["exclude_from_sim", "no"], ["at", fmt(at[0]), fmt(at[1]), "0"],
                           ["effects", ["font", ["size", fmt(size), fmt(size)]], ["justify", "left", "top"]],
                           ["uuid", q(uid(self.filename, "t", s[:40], at))]])

    def _symbol_instance(self, ref, lib_id, value, footprint, at, unit, props, sym, inbom=True, onboard=True,
                         dnp=False):
        X, Y = at
        node = ["symbol", ["lib_id", q(lib_id)], ["at", fmt(X), fmt(Y), "0"], ["unit", str(unit)],
                ["exclude_from_sim", "no"], ["in_bom", "yes" if inbom else "no"],
                ["on_board", "yes" if onboard else "no"], ["dnp", "yes" if dnp else "no"],
                ["uuid", q(uid(self.filename, "sym", ref, unit))]]
        rpos, vpos = getattr(self, "_textpos", None) or ((X + 3.81, Y - 1.27), (X + 3.81, Y + 1.27))
        self._textpos = None
        allprops = [("Reference", ref, rpos, False), ("Value", value, vpos, False),
                    ("Footprint", footprint or "", (X, Y), True), ("Datasheet", "", (X, Y), True),
                    ("Description", "", (X, Y), True)]
        for k, v in props.items():
            if k in SHOW:
                allprops.append((k, v, (vpos[0], vpos[1] + 2.54), False))
            else:
                allprops.append((k, v, (X, Y), True))
        for k, v, p, hide in allprops:
            eff = ["effects", ["font", ["size", "1.27", "1.27"]]]
            if k in ("Reference", "Value") or k in SHOW:
                eff.append(["justify", "left"])
            if hide:
                eff.append(["hide", "yes"])
            node.append(["property", q(k), q(v), ["at", fmt(p[0]), fmt(p[1]), "0"], eff])
        for p in symbol_pins(sym):
            if p["unit"] in (0, unit):
                node.append(["pin", q(p["number"]), ["uuid", q(uid(self.filename, "pin", ref, unit, p["number"]))]])
        node.append(["instances", ["project", q(self.project),
                                   ["path", q(self.path), ["reference", q(ref)], ["unit", str(unit)]]]])
        self.items.append(node)

    # ---- parts
    def part(self, ref, lib_id, value, at, conns, footprint="", unit=1, props=None, stub=2.54, nc_rest=True,
             glob=(), power=(), dnp=False):
        """conns: {pin number or pin name: net}. Net '~' or None = no-connect flag."""
        sym = self._lib(lib_id)
        if footprint and not footprint_exists(footprint):
            raise FileNotFoundError("footprint %s not found (part %s)" % (footprint, ref))
        X, Y = at
        pins = [p for p in symbol_pins(sym) if p["unit"] in (0, unit)]
        bynum = {}
        for p in pins:
            bynum.setdefault(p["number"], []).append(p)
        byname = {}
        for p in pins:
            byname.setdefault(p["name"], []).append(p)
        used = set()
        netmap = {}
        self._many = len(pins) > 3
        wired = {}   # pin position -> net: pins stacked on one position are wired once
        for key, net in conns.items():
            key = str(key)
            targets = bynum.get(key) or byname.get(key)
            if not targets:
                raise KeyError("%s (%s): no pin %r. Pins: %s" % (ref, lib_id, key,
                               ", ".join("%s/%s" % (p["number"], p["name"]) for p in pins)))
            for p in targets:
                used.add((p["number"], p["x"], p["y"]))
                netmap[p["number"]] = None if net in (None, "~") else net
                if (p["x"], p["y"]) in wired:
                    if wired[(p["x"], p["y"])] != net:
                        raise ValueError("%s: pins stacked on one position get different nets" % ref)
                    continue
                wired[(p["x"], p["y"])] = net
                self._connect(p, X, Y, net, glob, power, stub)
        if nc_rest:
            for p in pins:
                if (p["number"], p["x"], p["y"]) not in used and p["type"] not in ("no_connect",) and not (
                        p["hidden"] and p["type"].startswith("power")):
                    self.noconnect((X + p["x"], Y - p["y"]))
                    netmap.setdefault(p["number"], None)
        self._symbol_instance(ref, lib_id, value, footprint, at, unit, props or {}, sym, dnp=dnp,
                              inbom=not dnp and not ref.startswith(("TP", "H", "NT", "JP")),
                              onboard=True)
        self.parts.append((ref, lib_id, value, footprint, netmap))
        return pins

    # ---- automatic placement (row flow; boxes include stubs and label text)
    def start_layout(self, width=400.0, x0=15.24, y0=22.86):
        self.cur_x, self.cur_y, self.row_h, self.page_w, self.x0 = x0, y0, 0.0, width, x0
        self.max_y = y0

    def block(self, title, notes=()):
        """Start a new row with a heading (and optional note lines)."""
        if self.cur_x > self.x0:
            self.cur_y += self.row_h + 5.08
        self.cur_x, self.row_h = self.x0, 0.0
        self.text(title, (self.cur_x, self.cur_y), size=2.0)
        self.cur_y += 4.5
        for n in notes:
            self.text(n, (self.cur_x, self.cur_y), size=1.27)
            self.cur_y += 2.8
        self.cur_y += 2.0

    def auto(self, ref, lib_id, value, conns, footprint="", props=None, unit=1, glob=(), power=(), dnp=False):
        sym = self._lib(lib_id)
        pins = [p for p in symbol_pins(sym) if p["unit"] in (0, unit)]
        bynum = {p["number"]: p for p in pins}
        byname = {}
        for p in pins:
            byname.setdefault(p["name"], []).append(p)
        net_of = {}
        for k, net in conns.items():
            for p in ([bynum[str(k)]] if str(k) in bynum else byname.get(str(k), [])):
                net_of[(p["number"], p["x"], p["y"])] = net or ""
        xs = [p["x"] for p in pins] or [0]
        ys = [-p["y"] for p in pins] or [0]
        ext = {(-1, 0): 0.0, (1, 0): 0.0, (0, -1): 0.0, (0, 1): 0.0}
        for p in pins:
            net = net_of.get((p["number"], p["x"], p["y"]), "")
            d = OUT[p["angle"] % 360]
            lab = 2.54 + (len(net) * 1.1 + 3.0 if net and net not in power else (3.5 if net else 0.0))
            if net in glob or (len(pins) > 3 and net in power and net != "GND" and d[1] == 0):
                lab += GLOB_STUB
            ext[d] = max(ext[d], lab)
        minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
        textw = max([len(ref), len(value)] + [len(v) for k, v in (props or {}).items() if k in SHOW]) * 1.15 + 1.5
        small = (maxx - minx) <= 5.08 and len(pins) <= 3
        # small parts: ref/value text right of the body; ICs/connectors: ref above, value below
        right = (maxx + 2.54 + textw) if small else maxx
        w = (right - minx) + ext[(-1, 0)] + (0 if small else ext[(1, 0)]) + 10.16
        if small:
            w = max(w, (maxx - minx) + ext[(-1, 0)] + ext[(1, 0)] + 10.16)
        h = (maxy - miny) + ext[(0, -1)] + ext[(0, 1)] + (7.62 if small else 17.78)
        if self.cur_x + w > self.page_w and self.cur_x > self.x0:
            self.cur_y += self.row_h
            self.cur_x, self.row_h = self.x0, 0.0
        snap = lambda v: round(v / 2.54) * 2.54
        X = snap(self.cur_x + ext[(-1, 0)] - minx + 2.54)
        Y = snap(self.cur_y + ext[(0, -1)] - miny + (2.54 if small else 8.89))
        if small:
            tx = X + maxx + 2.54
            self._textpos = ((tx, Y - 1.27), (tx, Y + 1.27))
        else:
            self._textpos = ((X + minx, Y + miny - ext[(0, -1)] - 3.81),
                             (X + minx, Y + maxy + ext[(0, 1)] + 2.54))
        self.part(ref, lib_id, value, (X, Y), conns, footprint, unit, props, glob=glob, power=power, dnp=dnp)
        self.cur_x += w
        self.row_h = max(self.row_h, h)
        self.max_y = max(self.max_y, self.cur_y + h)

    def _connect(self, p, X, Y, net, glob, power, stub):
        a = (X + p["x"], Y - p["y"])
        if net in (None, "~"):
            self.noconnect(a)
            return
        d = OUT[p["angle"] % 360]
        # global labels, and supply symbols on the side pins of connectors/ICs, sit further out than local labels
        if net in glob or (self._many and net in power and net != "GND" and d[1] == 0):
            stub += GLOB_STUB
        b = (a[0] + d[0] * stub, a[1] + d[1] * stub)
        self.wire(a, b)
        if net in power:
            self.power(net, b, d)
        elif net in glob:
            self.label(net, b, d, "global")
        else:
            self.label(net, b, d, "local")

    def power(self, net, at, d):
        lib_id = {"GND": "power:GND", "+5V": "power:+5V", "+3V3": "power:+3V3", "VCC": "power:VCC"}[net]
        sym = self._lib(lib_id)
        self._npwr = getattr(self, "_npwr", 0) + 1
        ref = "#PWR%s%03d" % (self.prefix, self._npwr)
        X, Y = at
        # rotate the symbol so its graphic points away from the pin (KiCad rotation is CCW on screen)
        v = (0, 1) if net == "GND" else (0, -1)
        ang = 0
        while v != tuple(d):
            v, ang = (v[1], -v[0]), ang + 90
            if ang >= 360:
                ang = 0
                break
        off = 2.54 if net == "GND" else -2.54
        tx, ty = X + d[0] * abs(off) * 1.6, Y + d[1] * abs(off) * 1.6
        node = ["symbol", ["lib_id", q(lib_id)], ["at", fmt(X), fmt(Y), str(ang)], ["unit", "1"],
                ["exclude_from_sim", "no"], ["in_bom", "yes"], ["on_board", "yes"], ["dnp", "no"],
                ["uuid", q(uid(self.filename, "pwr", ref))]]
        for k, v2, hide in (("Reference", ref, True), ("Value", net, net == "GND"), ("Footprint", "", True),
                            ("Datasheet", "", True), ("Description", "", True)):
            eff = ["effects", ["font", ["size", "1.27", "1.27"]]]
            if hide:
                eff.append(["hide", "yes"])
            node.append(["property", q(k), q(v2), ["at", fmt(tx), fmt(ty), "0"], eff])
        node.append(["pin", q("1"), ["uuid", q(uid(self.filename, "pwrpin", ref))]])
        node.append(["instances", ["project", q(self.project),
                                   ["path", q(self.path), ["reference", q(ref)], ["unit", "1"]]]])
        self.items.append(node)

    def pwr_flag(self, net, at, glob=(), power=()):
        """PWR_FLAG on a net: tells ERC the net is driven (regulator outputs through inductors, connectors)."""
        sym = self._lib("power:PWR_FLAG")
        self._nflg = getattr(self, "_nflg", 0) + 1
        ref = "#FLG%s%02d" % (self.prefix, self._nflg)
        X, Y = at
        node = ["symbol", ["lib_id", q("power:PWR_FLAG")], ["at", fmt(X), fmt(Y), "0"], ["unit", "1"],
                ["exclude_from_sim", "no"], ["in_bom", "yes"], ["on_board", "yes"], ["dnp", "no"],
                ["uuid", q(uid(self.filename, "flg", ref))]]
        for k, v, hide in (("Reference", ref, True), ("Value", "PWR_FLAG", True), ("Footprint", "", True),
                           ("Datasheet", "", True), ("Description", "", True)):
            eff = ["effects", ["font", ["size", "1.27", "1.27"]]]
            if hide:
                eff.append(["hide", "yes"])
            node.append(["property", q(k), q(v), ["at", fmt(X), fmt(Y - 2.54), "0"], eff])
        node.append(["pin", q("1"), ["uuid", q(uid(self.filename, "flgpin", ref))]])
        node.append(["instances", ["project", q(self.project),
                                   ["path", q(self.path), ["reference", q(ref)], ["unit", "1"]]]])
        self.items.append(node)
        # PWR_FLAG pin is at (0,0) pointing down (angle 270 in lib): stub downwards to the net label
        b = (X, Y + 2.54)
        self.wire((X, Y), b)
        if net in power:
            self.power(net, b, (0, 1))
        elif net in glob:
            self.label(net, b, (0, 1), "global")
        else:
            self.label(net, b, (0, 1), "local")

    def auto_flag(self, net, glob=(), power=()):
        w = len(net) * 1.1 + 8.0
        if self.cur_x + w > self.page_w and self.cur_x > self.x0:
            self.cur_y += self.row_h
            self.cur_x, self.row_h = self.x0, 0.0
        snap = lambda v: round(v / 2.54) * 2.54
        X, Y = snap(self.cur_x + 5.08), snap(self.cur_y + 7.62)
        self.pwr_flag(net, (X, Y), glob=glob, power=power)
        self.cur_x += w
        self.row_h = max(self.row_h, 17.0)
        self.max_y = max(self.max_y, self.cur_y + 17.0)

    # ---- output
    def render(self, sheets_blocks=()):
        root = ["kicad_sch", ["version", SCH_VERSION], ["generator", q("eeschema")],
                ["generator_version", q("10.0")], ["uuid", q(self.uuid)], ["paper", q(self.paper)],
                ["title_block", ["title", q(self.title)], ["rev", q(REV)],
                 ["company", q(COMPANY)]],
                ["lib_symbols"] + list(self.libsyms.values())]
        root += self.items
        root += list(sheets_blocks)
        root.append(["embedded_fonts", "no"])
        return dump(root) + "\n"


class Project:
    def __init__(self, name, outdir):
        self.name, self.outdir = name, outdir
        self.root = Sheet(name, name + ".kicad_sch", ROOT_TITLE, "A4")
        self.root.path = "/" + self.root.uuid
        self.sheets = []

    def sheet(self, filename, title, paper="A3"):
        s = Sheet(self.name, filename, title, paper)
        s.block_uuid = uid("block", filename)
        s.path = "/" + self.root.uuid + "/" + s.block_uuid
        self.sheets.append(s)
        s.prefix = "%02d" % len(self.sheets)
        return s

    def write(self):
        os.makedirs(self.outdir, exist_ok=True)
        blocks = []
        for i, s in enumerate(self.sheets):
            x, y = 20 + (i % 3) * 60, 30 + (i // 3) * 45
            blocks.append(["sheet", ["at", fmt(x), fmt(y)], ["size", "50.8", "25.4"],
                           ["exclude_from_sim", "no"], ["in_bom", "yes"], ["on_board", "yes"], ["dnp", "no"],
                           ["stroke", ["width", "0"], ["type", "solid"]],
                           ["fill", ["color", "0", "0", "0", "0.0000"]],
                           ["uuid", q(s.block_uuid)],
                           ["property", q("Sheetname"), q(s.title), ["at", fmt(x), fmt(y - 0.7), "0"],
                            ["effects", ["font", ["size", "1.524", "1.524"]], ["justify", "left", "bottom"]]],
                           ["property", q("Sheetfile"), q(s.filename), ["at", fmt(x), fmt(y + 26.1), "0"],
                            ["effects", ["font", ["size", "1.27", "1.27"]], ["justify", "left", "top"]]],
                           ["instances", ["project", q(self.name),
                                          ["path", q("/" + self.root.uuid), ["page", q(str(i + 2))]]]]])
        sheet_inst = ["sheet_instances", ["path", q("/"), ["page", q("1")]]]
        with open(os.path.join(self.outdir, self.root.filename), "w", encoding="utf-8", newline="\n") as f:
            f.write(self.root.render(blocks + [sheet_inst]))
        for s in self.sheets:
            with open(os.path.join(self.outdir, s.filename), "w", encoding="utf-8", newline="\n") as f:
                f.write(s.render())

    def intended_nets(self):
        """{net: set((ref, pin))} from every part on every sheet (for checking the exported netlist)."""
        nets = {}
        for s in [self.root] + self.sheets:
            for ref, lib_id, value, fp, netmap in s.parts:
                for pin, net in netmap.items():
                    if net:
                        nets.setdefault(net, set()).add((ref, pin))
        return nets
