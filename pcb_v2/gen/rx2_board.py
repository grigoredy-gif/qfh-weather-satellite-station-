"""
rx2_board.py - builds the board of receiver version 2 (KiCad 10 pcbnew).

  rx2_board.py place          netlist + rx2_place.py  ->  ../rx2_receiver.kicad_pcb  (outline, rules, footprints)
  rx2_board.py stats [n]      ratsnest length per net (finds misplaced parts), unplaced parts
  rx2_board.py drc [types]    kicad-cli DRC with schematic parity: summary, and the items of the named types

Run each step in its own process with KiCad's Python (KiCad closed):
  <KiCad 10>\\bin\\python.exe rx2_board.py <step>

Coordinates in rx2_place.py are millimetres on the board: x to the right, y down, (0, 0) = top left corner.
In the board file the corner sits at (OX, OY).
"""
import csv
import json
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pcbnew  # noqa: E402
from kisch import parse  # noqa: E402

OUT = os.path.dirname(HERE)
NAME = "rx2_receiver"
PCB = os.path.join(OUT, NAME + ".kicad_pcb")
NETLIST = os.path.join(OUT, NAME + ".net")
REFS = os.path.join(OUT, "rx2_refs.csv")
KICAD = r"C:\Users\grigo\AppData\Local\Programs\KiCad\10.0"
FPDIR = os.path.join(KICAD, "share", "kicad", "footprints")
PROJ_FP = {"rx2": os.path.join(OUT, "rx2.pretty")}
CLI = os.path.join(KICAD, "bin", "kicad-cli.exe")
FM = pcbnew.FromMM
OX, OY = 100.0, 50.0          # board corner in the KiCad sheet
W, H = 100.0, 100.0           # board size

# name: (track, clearance, via diameter, via drill, nets)
NETCLASSES = {
    "PWR": (0.4, 0.2, 0.8, 0.4, ["v5"]),     # VCC: the trunks are laid by hand, the taps are thin
}
DEFAULT_CLASS = (0.25, 0.2, 0.7, 0.3)     # JLCPCB 2 layers: 0.10 mm track / space, 0.3 mm drill at no extra cost
DIRS = {"E": (1, 0), "W": (-1, 0), "S": (0, 1), "N": (0, -1)}


def V(x, y):
    return pcbnew.VECTOR2I(FM(x + OX), FM(y + OY))


def turn(x, y, a):
    """A point of a footprint (or of a cell) after KiCad rotation a (counter-clockwise on the screen, y down)."""
    c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
    return x * c + y * s, -x * s + y * c


def short(net):
    return net.split("/")[-1]


# ============================================================================ netlist
def read_netlist(path):
    with open(path, encoding="utf-8") as f:
        root = parse(f.read())[0]
    comps, nets = {}, {}

    def kid(node, key):
        for e in node:
            if isinstance(e, list) and e and e[0] == key:
                return e
        return None

    for sec in root:
        if not (isinstance(sec, list) and sec):
            continue
        if sec[0] == "components":
            for c in sec[1:]:
                ref = str(kid(c, "ref")[1])
                fields = {}
                fl = kid(c, "fields")
                for fld in (fl[1:] if fl else []):
                    val = [str(x) for x in fld[1:] if not isinstance(x, list)]
                    fields[str(kid(fld, "name")[1])] = val[0] if val else ""
                props = {}
                for e in c:
                    if isinstance(e, list) and e and e[0] == "property":
                        vv = kid(e, "value")
                        props[str(kid(e, "name")[1])] = str(vv[1]) if vv else ""
                sp = kid(c, "sheetpath")
                tst = str(kid(sp, "tstamps")[1]) if sp else "/"
                comps[ref] = dict(value=str(kid(c, "value")[1]), footprint=str(kid(c, "footprint")[1]),
                                  fields=fields, props=props, path=tst + str(kid(c, "tstamps")[1]),
                                  sheetname=props.get("Sheetname", ""), sheetfile=props.get("Sheetfile", ""))
        elif sec[0] == "nets":
            for n in sec[1:]:
                nets[str(kid(n, "name")[1])] = [(str(kid(e, "ref")[1]), str(kid(e, "pin")[1]))
                                                for e in n if isinstance(e, list) and e and e[0] == "node"]
    return comps, nets


def sim_refs():
    with open(REFS, encoding="utf-8") as f:
        return {r["sim"]: r["ref"] for r in csv.DictReader(f)}


# ============================================================================ step 1: place
def setup_rules(board):
    ds = board.GetDesignSettings()
    for attr, val in (("m_MinClearance", 0.15), ("m_TrackMinWidth", 0.15), ("m_ViasMinSize", 0.6),
                      ("m_MinThroughDrill", 0.3), ("m_CopperEdgeClearance", 0.3), ("m_HoleClearance", 0.25),
                      ("m_HoleToHoleMin", 0.5), ("m_ViasMinAnnularWidth", 0.15)):
        if hasattr(ds, attr):
            setattr(ds, attr, FM(val))
    if hasattr(ds, "m_MinResolvedSpokes"):
        ds.m_MinResolvedSpokes = 1      # every ground pad also has its own via
    ns = ds.m_NetSettings
    dflt = ns.GetDefaultNetclass()
    tw, cl, vd, vdr = DEFAULT_CLASS
    dflt.SetTrackWidth(FM(tw))
    dflt.SetClearance(FM(cl))
    dflt.SetViaDiameter(FM(vd))
    dflt.SetViaDrill(FM(vdr))
    ns.ClearNetclassPatternAssignments()
    for name, (tw, cl, vd, vdr, nets) in NETCLASSES.items():
        nc = pcbnew.NETCLASS(name)
        nc.SetTrackWidth(FM(tw))
        nc.SetClearance(FM(cl))
        nc.SetViaDiameter(FM(vd))
        nc.SetViaDrill(FM(vdr))
        ns.SetNetclass(name, nc)
        for nn in nets:
            ns.SetNetclassPatternAssignment(nn, name)
            ns.SetNetclassPatternAssignment("*/" + nn, name)


def load_fp(fpid):
    lib, name = fpid.split(":", 1)
    fp = pcbnew.FootprintLoad(PROJ_FP.get(lib) or os.path.join(FPDIR, lib + ".pretty"), name)
    if fp is None:
        raise RuntimeError("footprint not found: " + fpid)
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


def dress(fp, ref, c):
    fp.SetReference(ref)
    fp.SetValue(c["value"])
    for k in ("LCSC", "MPN", "Sim", "Assembly"):
        if c["fields"].get(k):
            fp.SetField(k, c["fields"][k])
    for f in fp.GetFields():
        if f.GetName() != "Reference":
            f.SetVisible(False)
    r = fp.Reference()
    r.SetVisible(True)
    r.SetTextSize(pcbnew.VECTOR2I(FM(0.7), FM(0.7)))
    r.SetTextThickness(FM(0.12))
    fp.SetPath(pcbnew.KIID_PATH(c["path"]))
    fp.SetSheetname(c["sheetname"])
    fp.SetSheetfile(c["sheetfile"])
    fp.SetDNP("dnp" in c["props"])
    fp.SetExcludedFromBOM("exclude_from_bom" in c["props"])
    # JLCPCB places neither the connectors (soldered by hand) nor the empty spare positions
    fp.SetExcludedFromPosFiles(ref.startswith("J") or "dnp" in c["props"])


def angle_for(pads, spec):
    """pads: [(number, short net, fx, fy)] of the footprint at angle 0. spec: an angle, 'net:D' or '#pad:D'
    (the pads on that net, or that pad, point to D = N, E, S or W)."""
    if isinstance(spec, (int, float)):
        return float(spec)
    key, d = spec.split(":")
    sel = [p for p in pads if (p[0] == key[1:] if key.startswith("#") else p[1] == key)]
    if not sel:
        raise KeyError("no pad for '%s' (pads: %s)" % (spec, ", ".join("%s=%s" % (p[0], p[1]) for p in pads)))
    fx = sum(p[2] for p in sel) / len(sel) - sum(p[2] for p in pads) / len(pads)
    fy = sum(p[3] for p in sel) / len(sel) - sum(p[3] for p in pads) / len(pads)
    dx, dy = DIRS[d]
    return max((0.0, 90.0, 180.0, 270.0), key=lambda a: turn(fx, fy, a)[0] * dx + turn(fx, fy, a)[1] * dy)


def place():
    import rx2_place
    comps, nets = read_netlist(NETLIST)
    ref_of = sim_refs()
    if os.path.exists(PCB):
        os.remove(PCB)
    board = pcbnew.NewBoard(PCB)
    board.SetCopperLayerCount(2)
    ds = board.GetDesignSettings()
    ds.SetBoardThickness(FM(1.6))
    setup_rules(board)
    tb = board.GetTitleBlock()
    tb.SetTitle("QFH 137 MHz receiver, version 2")
    tb.SetRevision("board of 2026-11-14")
    tb.SetCompany("Edy Grigore")
    for a, b in (((0, 0), (W, 0)), ((W, 0), (W, H)), ((W, H), (0, H)), ((0, H), (0, 0))):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(V(*a))
        s.SetEnd(V(*b))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(FM(0.1))
        board.Add(s)
    netinfo = {}
    for name in nets:
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netinfo[name] = ni
    net_of_pad = {(ref, pin): name for name, nodes in nets.items() for ref, pin in nodes}
    # where every part goes: sim name -> (x, y, angle spec, cell angle)
    where = {}
    for cname, cell in rx2_place.CELLS.items():
        ox, oy = cell["at"]
        rot = cell.get("rot", 0)
        for sim, lx, ly, spec in cell["parts"]:
            if sim in where:
                raise KeyError("placed twice: " + sim)
            gx, gy = turn(lx, ly, rot)
            where[sim] = (ox + gx, oy + gy, spec, rot, cname)
    unknown = sorted(set(where) - set(ref_of))
    if unknown:
        raise KeyError("rx2_place.py names parts that are not in the schematic: %s" % unknown)
    sim_of = {ref: sim for sim, ref in ref_of.items()}
    parked = 0
    for ref, c in sorted(comps.items()):
        fp = load_fp(c["footprint"])
        dress(fp, ref, c)
        board.Add(fp)
        pads = [(p.GetNumber(), short(net_of_pad.get((ref, p.GetNumber()), "")),
                 pcbnew.ToMM(p.GetPosition().x - fp.GetPosition().x), pcbnew.ToMM(p.GetPosition().y - fp.GetPosition().y))
                for p in fp.Pads()]
        sim = sim_of[ref]
        if sim in where:
            x, y, spec, rot, _cell = where[sim]
            fp.SetOrientationDegrees((angle_for(pads, spec) + rot) % 360)
            fp.SetPosition(V(x, y))
        else:                                   # not placed yet: parked right of the board
            fp.SetPosition(V(W + 6 + (parked % 12) * 5.0, 4 + (parked // 12) * 5.0))
            parked += 1
        for p in fp.Pads():
            nn = net_of_pad.get((ref, p.GetNumber()))
            if nn:
                p.SetNet(netinfo[nn])
    for i, (x, y) in enumerate(getattr(rx2_place, "FIDUCIALS", []), 1):
        fp = load_fp("Fiducial:Fiducial_1mm_Mask2mm")
        fp.SetReference("FID%d" % i)
        fp.Reference().SetVisible(False)
        fp.SetBoardOnly(True)
        fp.SetExcludedFromBOM(True)
        board.Add(fp)
        fp.SetPosition(V(x, y))
    pcbnew.SaveBoard(PCB, board)
    print("place: %d parts, %d placed from rx2_place.py, %d parked, %d nets" % (
        len(comps), len(comps) - parked, parked, len(nets)))
    sys.stdout.flush()
    os._exit(0)


# ============================================================================ step 2: ratsnest statistics
def stats(top=25):
    board = pcbnew.LoadBoard(PCB)
    ref_sim = {}
    pads = {}
    for fp in board.GetFootprints():
        sim = fp.GetFieldText("Sim") if fp.HasField("Sim") else fp.GetReference()
        ref_sim[fp.GetReference()] = sim
        px = pcbnew.ToMM(fp.GetPosition().x) - OX
        if px > W:
            continue                            # parked
        for p in fp.Pads():
            n = p.GetNetname()
            if n:
                pads.setdefault(short(n), []).append((pcbnew.ToMM(p.GetPosition().x) - OX,
                                                      pcbnew.ToMM(p.GetPosition().y) - OY, sim + "." + p.GetNumber()))
    rows = []
    for net, pp in pads.items():
        if len(pp) < 2 or net in ("GND",):
            continue
        done, rest, total, worst = [pp[0]], pp[1:], 0.0, (0.0, "")
        while rest:                              # minimum spanning tree, Prim
            d, a, b = min((math.hypot(a[0] - b[0], a[1] - b[1]), a, b) for a in done for b in rest)
            total += d
            if d > worst[0]:
                worst = (d, "%s - %s" % (a[2], b[2]))
            done.append(b)
            rest.remove(b)
        rows.append((total, net, len(pp), worst))
    rows.sort(reverse=True)
    print("net                 pads  length   longest link")
    for total, net, n, worst in rows[:top]:
        print("%-18s %4d  %6.1f   %5.1f  %s" % (net, n, total, worst[0], worst[1]))
    print("sum of all nets without GND: %.0f mm" % sum(r[0] for r in rows))


# ============================================================================ step 3: DRC summary
def drc(show=()):
    out = os.path.join(OUT, "drc.json")
    subprocess.run([CLI, "pcb", "drc", "--format", "json", "--severity-all", "--schematic-parity", "-o", out, PCB],
                   capture_output=True)
    with open(out, encoding="utf-8") as f:
        rep = json.load(f)
    counts = {}
    for v in rep.get("violations", []):
        counts[(v["severity"], v["type"])] = counts.get((v["severity"], v["type"]), 0) + 1
    for k, n in sorted(counts.items()):
        print("DRC %-8s %-34s %d" % (k[0], k[1], n))
    print("unconnected items: %d | schematic parity: %d" % (len(rep.get("unconnected_items", [])),
                                                            len(rep.get("schematic_parity", []))))
    for v in rep.get("schematic_parity", [])[:12]:
        print("  PARITY %s: %s" % (v["type"], "; ".join(i.get("description", "") for i in v.get("items", []))[:200]))
    n = 0
    for v in rep.get("violations", []):
        if (v["type"] in show or "all" in show) and n < 60:
            n += 1
            pos = v.get("items", [{}])[0].get("pos", {})
            print("  %-22s (%.2f, %.2f) %s" % (v["type"], pos.get("x", 0) - OX, pos.get("y", 0) - OY,
                                               "; ".join(i.get("description", "") for i in v.get("items", []))[:200]))
    if "unconnected" in show:
        for v in rep.get("unconnected_items", [])[:60]:
            pos = v.get("items", [{}])[0].get("pos", {})
            print("  unconnected (%.2f, %.2f) %s" % (pos.get("x", 0) - OX, pos.get("y", 0) - OY,
                                                     "; ".join(i.get("description", "") for i in v.get("items", []))[:200]))
    return rep


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        if cmd == "place":
            place()
        elif cmd == "stats":
            stats(int(sys.argv[2]) if len(sys.argv) > 2 else 25)
        elif cmd == "drc":
            drc(sys.argv[2:])
        else:
            print(__doc__)
        sys.stdout.flush()
        os._exit(0)
    except Exception:
        import traceback
        traceback.print_exc()
        sys.stderr.flush()
        os._exit(1)
