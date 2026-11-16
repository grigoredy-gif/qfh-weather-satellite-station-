"""
rx2_route.py - copper for the board of receiver version 2 (KiCad 10 pcbnew).

  rx2_route.py hand      tracks laid by rule, locked: the emitter links of the pairs, the supply and bias trunks;
                         and the rule areas that keep the bottom layer free of tracks under the RF and IF parts
  rx2_route.py auto [m]  Freerouting on all other nets (GND is left to the pours), at most m minutes
  rx2_route.py merge     add the autorouter's wires and vias to the board (hand-laid copper stays as it is)
  rx2_route.py clean     remove the autorouter's dangling leftovers that the last DRC run reported
  rx2_route.py finish    ground vias and the ground pours on both layers
  rx2_route.py silk      silkscreen texts and the outline of the DevKitC; part references hidden

Run each step in its own process with KiCad's Python (KiCad closed), after rx2_board.py place.
Coordinates are board millimetres as in rx2_place.py.
The mounting holes come last, from rx2_holes.py: it moves the corner of the VCC trunk at the top right, two
fiducial marks and the text "< USB", so the tables in this file and in rx2_place.py still hold their first places.
After it rx2_ant.py moves the antenna track under the SMA jack to the bottom layer and cuts the first rule
area of NO_BOTTOM back to x = 11.
"""
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pcbnew  # noqa: E402
import frhelp  # noqa: E402
import rx2_place  # noqa: E402
from rx2_board import PCB, OUT, OX, OY, W, H, FM, V, turn, short  # noqa: E402

F, B = pcbnew.F_Cu, pcbnew.B_Cu
DSN = os.path.join(OUT, "rx2_receiver.dsn")
SES = os.path.join(OUT, "rx2_receiver.ses")
FRLOG = os.path.join(OUT, "freerouting.log")

# cells built with rx2_place.pair(): cell -> net of the two emitters
PAIRS = {"if1_p1": "ei1", "if1_p2": "ei2", "if2_pa": "ea", "if2_pb": "eb", "if2_pc": "ec", "lo1mul": "eq"}
# supply and bias trunks and two long signal lines: (net, width, [points])
TRUNKS = [
    # regulator output, up between two socket pins, then east under the second-IF row (thin where Cuo and Rup1
    # bridge it), north along the east edge (first-IF column) and west along the top edge (mixer 1, front end)
    ("VCC", 0.4, [(16.9, 75.725), (16.51, 75.3), (16.51, 69.2)]),
    ("VCC", 0.4, [(16.51, 69.2), (16.51, 67.5)]),
    ("VCC", 0.25, [(16.51, 67.5), (21.8, 67.5)]),
    ("VCC", 0.5, [(21.8, 67.5), (83.2, 67.5)]),
    ("VCC", 0.25, [(83.2, 67.5), (84.8, 67.5)]),       # Cd2
    ("VCC", 0.5, [(84.8, 67.5), (97.4, 67.5), (97.4, 2.6), (31.0, 2.6), (31.0, 6.3)]),
    # west feeder for the audio supply and the 125 MHz chain
    ("VCC", 0.5, [(16.51, 67.5), (3.0, 67.5), (3.0, 26.0), (48.375, 26.0), (48.375, 28.2)]),
    # supply for the vb reference and the squarer's bias divider in the middle of the board: down the gap
    # between mixer 1 and T1 (on the bottom layer where it passes under the t1 link and the vb feed: HOPS)
    ("VCC", 0.4, [(66.0, 2.6), (66.0, 8.0)]),
    ("VCC", 0.3, [(66.0, 19.7), (66.0, 33.0), (69.425, 36.425), (69.425, 39.5)]),
    ("VCC", 0.3, [(66.0, 33.0), (60.4, 33.0), (60.4, 38.3), (59.625, 39.1)]),
    # supply for the vbd reference: down the gap between the 25 MHz oscillator and the follower
    # (on the bottom layer where the 25 MHz line osc25 crosses it: HOPS)
    ("VCC", 0.3, [(34.6, 26.0), (34.6, 33.0)]), ("VCC", 0.3, [(34.6, 39.6), (34.6, 41.0)]),
    # bias line vb: north side of the second-IF row, west side of the first-IF column
    ("vb", 0.3, [(46.075, 47.4), (78.2, 47.4), (78.2, 18.6)]),
    ("vb", 0.25, [(49.35, 45.525), (49.35, 47.4)]),          # Rqt of the 125 MHz chain
    ("vb", 0.3, [(65.94, 39.5), (65.94, 47.4)]),
    # ... to mixer 1: west along y = 18.6, passing between the pads of Clo1 and of Rex2 (no bottom-layer hop)
    ("vb", 0.2, [(78.2, 18.6), (51.0, 18.6), (50.6, 19.0), (46.6, 19.0), (46.175, 18.575), (46.175, 16.7)]),
    # ... to mixer 2
    ("vb", 0.3, [(78.2, 40.4), (94.625, 40.4), (94.625, 41.2)]),
    # audio output down the gap east of the filter to Cuo, and the ADC line along the socket row to pin 3
    ("cg", 0.25, [(11.14, 43.225), (12.0, 42.7), (19.0, 42.7), (19.0, 66.2), (20.4, 66.2), (21.0, 66.725)]),
    ("adc", 0.25, [(17.8, 68.325), (17.8, 68.85), (42.25, 68.85), (43.18, 69.78), (43.18, 70.8)]),
    ("adc", 0.25, [(21.0, 68.275), (21.0, 68.85)]),
]
# mixer 2, in the coordinates of its cell (see rx2_place.py): everything that makes it fit on one layer
MIX2 = [
    ("lo2", [(-0.95, 0.94), (-2.2, 0.94), (-2.2, -8.525), (15.2, -8.525), (15.2, 0.96), (13.75, 0.96)]),
    ("vfm", [(0.0, -0.94), (0.0, -2.8), (9.2, -2.8), (9.2, -0.94)]),
    ("vfm", [(0.0, -2.8), (0.0, -7.7)]),
    ("em1", [(0.95, 0.94), (2.65, 0.96)]), ("em1", [(1.8, 0.95), (1.8, 11.06)]),
    ("em2", [(10.15, 0.94), (11.85, 0.96)]), ("em2", [(11.0, 0.95), (11.0, 4.86)]),
    ("bsb", [(4.55, 0.96), (8.25, 0.94)]), ("bsb", [(6.4, -1.975), (6.4, 1.825)]),
    ("t5", [(3.6, 2.84), (3.6, 14.0), (12.8, 14.0), (12.8, 2.84)]),
    ("e1", [(2.75, 12.94), (2.75, 16.0), (11.95, 16.0), (11.95, 14.825)]),
    ("et", [(11.95, 10.125), (11.95, 13.175)]), ("et", [(11.95, 11.175), (10.4, 11.175)]),
    ("bm2", [(10.05, 6.74), (8.175, 6.74), (8.6, 7.3), (8.6, 8.475)]),
    ("e2", [(11.95, 6.74), (11.95, 8.475)]),
    ("vbs", [(6.4, -3.625), (6.4, -6.875)]), ("vbs", [(5.525, -5.4), (7.725, -5.4)]),
    ("vbs", [(6.4, -6.875), (4.4, -7.7)]),
    ("vb", [(8.6, 10.125), (8.6, 11.35)]),
]
# cells with two collector lines (x = 0: supply-filter node, x = 5.4: output node) and parts between them:
# cell: (supply-filter net, output net, parts between or beside the lines)
LADDERS = {
    "if1_p1": ("vft3", "t3", ["Ct3b", "Ct3a", "spare_Lt3", "Lt3", "Cft3", "Rft3"]),
    "if1_p2": ("vft4", "m2in", ["Ct4b", "Ct4a", "spare_Lt4", "Lt4", "Cft4", "Rft4"]),
    "if2_t5": ("vf5", "t5", ["C5b", "C5a", "spare_L5", "L5", "Cf5", "Rf5"]),
    "if2_pa": ("vfa", "t6", ["C6b", "C6a", "spare_L6", "L6", "Cfa", "Rfa"]),
    "if2_pb": ("vfb", "cb", ["Rcb", "Cfb", "Rfb"]),
    "if2_pc": ("vfc", "c2", ["Rcc", "Cfc", "Rfc"]),
    "lo1mul": ("vfq", "ta", ["Lta", "Cfq2", "Rfq", "Cta2", "spare_Lta", "Cta"]),
}
# bias taps of the pairs: cell -> y of the bias trunk in the cell
VB_TAPS = {"if1_p1": 8.2, "if1_p2": 8.2, "if2_pa": 8.0, "if2_pb": 8.0}
# short links that the autorouter left open in some runs: (cell, net, [points in the cell])
LINKS = [
    ("fe", "cm23", [(27.875, 0.95), (30.625, 0.95)]), ("fe", "cm23", [(29.25, 0.95), (29.25, 2.525)]),
    # first IF, T1 and T2: the node lines of the two capacitor groups, the inductors and the supply filter
    ("if1_t12", "t1", [(0.8, 0.0), (4.8, 0.0)]), ("if1_t12", "t2", [(8.8, 0.0), (12.8, 0.0)]),
    ("if1_t12", "cm12", [(0.8, 1.55), (12.8, 1.55)]),
    ("if1_t12", "t1", [(1.5, -1.555), (1.5, 0.0)]), ("if1_t12", "t1", [(4.0, -1.875), (4.0, 0.0)]),
    ("if1_t12", "t2", [(10.355, -2.5), (10.355, 0.0)]),
    ("if1_t12", "vft1", [(1.5, -5.775), (1.5, -3.845), (4.0, -3.6), (5.625, -3.7)]),
    # 125 MHz chain: the bias node vbq goes from the divider around the current source to Rbq1,
    # passing between the pads of Rqe and Rqt (it cannot cross the emitter link or the eqc track)
    ("lo1mul", "vbq", [(4.425, 5.775), (4.425, 7.425), (3.5, 7.425), (3.5, 8.4), (1.2, 8.4), (1.2, 11.5),
                       (-5.7, 11.5), (-5.7, 4.025), (-2.5, 4.025)]),          # under Csnq, Rqe and Rqt
    # audio: output of the first filter into the second follower (the autorouter once shorted it to va here)
    ("audio", "ea2", [(16.7, 57.675), (13.5, 57.675), (12.96, 57.45), (12.96, 58.875)]),
    ("audio", "ea2", [(12.96, 58.0), (11.175, 58.0)]),
    ("lo2", "oe", [(-2.7, 0.775), (-0.94, 0.95), (-0.94, 2.425), (-2.9, 2.425)]),
    ("lo1osc", "o25e", [(-2.7, 0.775), (-0.94, 0.95), (-0.94, 2.425), (-2.9, 2.425)]),
]
# the one hop to the bottom layer: bias for Rbm2, under the t5 bus and the emitter track of Qm1
MIX2_HOP = ("vb", (8.6, 11.35), (8.6, 17.0))
# the regulator under the DevKitC, laid by hand (the autorouter left one of its nets open in most runs):
# (net, width, [points]) in board coordinates. The sense node pe has one hop under the two PNP transistors.
REG = [
    ("v5", 0.4, [(2.54, 70.8), (2.54, 72.9), (3.2, 73.825), (6.4, 73.825)]),
    ("v5", 0.4, [(5.3, 73.825), (5.3, 77.5), (7.5, 77.5), (8.56, 76.95)]),
    ("pe", 0.4, [(6.4, 75.375), (7.4, 75.375), (8.56, 75.05), (8.56, 73.95)]),
    ("pe", 0.4, [(13.45, 77.95), (12.56, 76.95)]), ("pe", 0.3, [(12.56, 76.95), (12.325, 78.6)]),
    ("pe", 0.3, [(15.9, 81.1), (14.44, 81.1)]),
    ("pb", 0.25, [(10.44, 76.0), (11.6, 75.6), (12.56, 75.05)]),
    ("pb", 0.25, [(10.44, 76.0), (10.44, 78.0), (10.675, 78.6), (10.44, 80.2), (10.44, 81.1)]),
    ("VCC", 0.4, [(14.44, 76.0), (16.0, 75.725), (16.9, 75.725)]),
    ("VCC", 0.25, [(14.44, 76.0), (14.44, 79.3), (13.6, 80.15), (12.56, 80.15)]),
    ("ret", 0.25, [(8.56, 82.05), (9.4, 83.2), (10.6, 83.575), (11.8, 83.2), (12.56, 82.05)]),
    ("vref", 0.25, [(6.0, 80.125), (8.56, 80.15)]),
    ("vref", 0.25, [(6.0, 83.575), (7.2, 82.4), (7.2, 80.6), (6.75, 80.15)]),
    ("v3ref", 0.25, [(6.0, 85.225), (6.0, 86.5), (45.8, 86.5), (48.26, 84.0), (48.26, 70.8)]),
]
REG_HOP = [("pe", (8.56, 73.95), (13.45, 77.95)), ("pe", (13.45, 77.95), (15.9, 81.1))]
# hops to the bottom layer in board coordinates: (net, from, to)
HOPS = [("VCC", (66.0, 8.0), (66.0, 19.7)), ("VCC", (34.6, 33.0), (34.6, 39.6))]
# bottom layer: no tracks inside these rectangles (solid ground under the RF and IF parts)
NO_BOTTOM = [
    ("front end and mixer 1", (0.0, 0.0, 65.2, 21.0)),
    ("T1 and T2", (66.8, 0.0, 100.0, 21.0)),
    ("first-IF column", (76.0, 21.0, 100.0, 39.8)),
    ("second-IF row and detector", (19.0, 46.0, 79.0, 69.0)),
    ("squarer and 125 MHz tuned circuits", (47.0, 21.0, 63.0, 46.0)),
]


def find_net(board, name):
    n = board.FindNet(name)
    if n:
        return n
    for full, net in board.GetNetsByName().items():
        if str(full).split("/")[-1] == name:
            return net
    raise KeyError("net not found: " + name)


class Router:
    def __init__(self, board):
        self.board = board
        self.n = {"tracks": 0, "vias": 0}

    def track(self, net, layer, w, pts, lock=True):
        ni = find_net(self.board, net)
        for a, b in zip(pts, pts[1:]):
            if math.hypot(a[0] - b[0], a[1] - b[1]) < 1e-6:
                continue
            t = pcbnew.PCB_TRACK(self.board)
            t.SetStart(V(*a))
            t.SetEnd(V(*b))
            t.SetWidth(FM(w))
            t.SetLayer(layer)
            t.SetNet(ni)
            t.SetLocked(lock)
            self.board.Add(t)
            self.n["tracks"] += 1

    def via(self, net, x, y, d=0.7, drill=0.3, lock=True):
        v = pcbnew.PCB_VIA(self.board)
        v.SetPosition(V(x, y))
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetLayerPair(F, B)
        v.SetDrill(FM(drill))
        v.SetWidth(F, FM(d))
        v.SetNet(find_net(self.board, net))
        v.SetLocked(lock)
        self.board.Add(v)
        self.n["vias"] += 1


def cell_pt(cell, lx, ly):
    c = rx2_place.CELLS[cell]
    gx, gy = turn(lx, ly, c.get("rot", 0))
    return c["at"][0] + gx, c["at"][1] + gy


def rule_area(board, name, layers, box, no_tracks=True, no_vias=False):
    x0, y0, x1, y1 = box
    z = pcbnew.ZONE(board)
    ls = pcbnew.LSET()
    for l in layers:
        ls.AddLayer(l)
    z.SetLayerSet(ls)
    ol = z.Outline()
    ol.NewOutline()
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        ol.Append(FM(x + OX), FM(y + OY))
    z.SetIsRuleArea(True)
    z.SetDoNotAllowTracks(no_tracks)
    z.SetDoNotAllowVias(no_vias)
    z.SetDoNotAllowZoneFills(False)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False)
    z.SetZoneName(name)
    board.Add(z)


# ============================================================================ step 1: tracks laid by rule
def hand():
    board = pcbnew.LoadBoard(PCB)
    r = Router(board)
    for cell, net in PAIRS.items():
        # the U that joins the two emitters, under the second base (see rx2_place.pair)
        u = [(0.95, 0.94), (0.95, 4.95), (6.35, 4.95), (6.35, 0.94)]
        r.track(net, F, 0.25, [cell_pt(cell, x, y) for x, y in u])
        if cell != "lo1mul":                       # down to the pad of the tail resistor
            r.track(net, F, 0.25, [cell_pt(cell, 0.95, 4.95), cell_pt(cell, 0.95, 5.175)])
    sim_fp = {fp.GetFieldText("Sim"): fp for fp in board.GetFootprints() if fp.HasField("Sim")}

    def local_pads(cell, sim):
        """pads of a part in the coordinates of its cell: [(x, y, short net name)]"""
        c = rx2_place.CELLS[cell]
        out = []
        for q in sim_fp[sim].Pads():
            bx = pcbnew.ToMM(q.GetPosition().x) - OX - c["at"][0]
            by = pcbnew.ToMM(q.GetPosition().y) - OY - c["at"][1]
            lx, ly = turn(bx, by, -c.get("rot", 0))
            out.append((round(lx, 3), round(ly, 3), short(q.GetNetname())))
        return out

    for cell, (vft, tnet, parts) in LADDERS.items():
        ends = {vft: [-0.94] if cell != "if2_t5" else [], tnet: [-0.94] if cell != "if2_t5" else []}
        for sim in parts:
            for lx, ly, net in local_pads(cell, sim):
                if net not in (vft, tnet):
                    continue
                x0 = 0.0 if net == vft else 5.4
                ends[net].append(ly)
                if abs(lx - x0) > 0.01:
                    r.track(net, F, 0.25, [cell_pt(cell, x0, ly), cell_pt(cell, lx, ly)])
        for net, x0 in ((vft, 0.0), (tnet, 5.4)):
            r.track(net, F, 0.25, [cell_pt(cell, x0, max(ends[net])), cell_pt(cell, x0, min(ends[net]))])
    for cell, yt in VB_TAPS.items():
        for x, y in ((-2.5, 4.025), (4.425, 5.775)):
            r.track("vb", F, 0.25, [cell_pt(cell, x, y), cell_pt(cell, x, yt)])
    for cell, net, pts in LINKS:
        r.track(net, F, 0.2, [cell_pt(cell, x, y) for x, y in pts])
    for net, w, pts in TRUNKS:
        r.track(net, F, w, pts)
    for net, pts in MIX2:
        r.track(net, F, 0.25, [cell_pt("mix2", x, y) for x, y in pts])
    net, a, b = MIX2_HOP
    a, b = cell_pt("mix2", *a), cell_pt("mix2", *b)
    r.via(net, *a)
    r.via(net, *b)
    r.track(net, B, 0.25, [a, b])
    for net, a, b in HOPS:
        r.via(net, *a)
        r.via(net, *b)
        r.track(net, B, 0.3, [a, b])
    for net, w, pts in REG:
        r.track(net, F, w, pts)
    for x, y in sorted({q for _n, a, b in REG_HOP for q in (a, b)}):
        r.via("pe", x, y)
    for net, a, b in REG_HOP:
        r.track(net, B, 0.4, [a, b])
    for name, box in NO_BOTTOM:
        rule_area(board, "no bottom tracks: " + name, [B], box)
    plan, missing = plan_ground(board)
    with open(GNDPLAN, "w", encoding="utf-8") as f:
        json.dump(plan, f)
    for i, (cx, cy, x, y) in enumerate(plan):
        rule_area(board, "ground via %d" % i, [F, B], (x - 0.6, y - 0.6, x + 0.6, y + 0.6), no_vias=True)
        rule_area(board, "ground via %d track" % i, [F],
                  (min(cx, x) - 0.4, min(cy, y) - 0.4, max(cx, x) + 0.4, max(cy, y) + 0.4), no_vias=True)
    print("hand: places for %d ground vias kept free; no room beside: %s" % (len(plan), " ".join(missing) or "none"))
    pcbnew.SaveBoard(PCB, board)
    print("hand: %(tracks)d locked track segments" % r.n)
    sys.stdout.flush()
    os._exit(0)


# ============================================================================ step 2: autorouter
def auto(minutes=8):
    board = pcbnew.LoadBoard(PCB)
    ok = pcbnew.ExportSpecctraDSN(board, DSN)
    frhelp.strip_net(DSN, "GND")                 # GND is connected by the pours afterwards
    print("DSN export:", ok, flush=True)
    saved = frhelp.run_freerouting(DSN, SES, FRLOG, minutes)
    with open(FRLOG, encoding="utf-8", errors="replace") as lf:
        lines = [l for l in lf.read().splitlines() if "pass #" in l or "completed" in l or "ERROR" in l]
    print("\n".join(lines[-4:]), flush=True)
    print("session file written:", saved, flush=True)
    sys.stdout.flush()
    os._exit(0 if saved else 2)


# ============================================================================ step 3: merge the session
def merge():
    session = frhelp.read_session(SES)
    board = pcbnew.LoadBoard(PCB)
    have, have_via = {}, []
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA":
            have_via.append((pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y)))
        else:
            a, b = t.GetStart(), t.GetEnd()
            have.setdefault(t.GetNetname(), []).append((board.GetLayerName(t.GetLayer()), pcbnew.ToMM(a.x),
                                                        pcbnew.ToMM(a.y), pcbnew.ToMM(b.x), pcbnew.ToMM(b.y)))

    def on_segment(p, s, tol=0.02):
        (x, y), (_l, x1, y1, x2, y2) = p, s
        dx, dy = x2 - x1, y2 - y1
        n = math.hypot(dx, dy)
        if n < 1e-9:
            return math.hypot(x - x1, y - y1) < tol
        t = ((x - x1) * dx + (y - y1) * dy) / (n * n)
        return -tol / n <= t <= 1 + tol / n and abs((x - x1) * dy - (y - y1) * dx) / n < tol

    nets = {str(k): v for k, v in board.GetNetsByName().items()}
    added = {"tracks": 0, "vias": 0, "kept": 0, "bottom": 0}
    for name, d in session.items():
        ni = nets.get(name)
        if ni is None:
            print("  session net not on the board (skipped): %s" % name)
            continue
        mine = have.get(name, [])
        for layer, width, pts in d["wires"]:
            lid = F if layer == "F.Cu" else B
            for a, b in zip(pts, pts[1:]):
                if any(s[0] == layer and on_segment(a, s) and on_segment(b, s) for s in mine):
                    added["kept"] += 1
                    continue
                t = pcbnew.PCB_TRACK(board)
                t.SetStart(pcbnew.VECTOR2I(FM(a[0]), FM(a[1])))
                t.SetEnd(pcbnew.VECTOR2I(FM(b[0]), FM(b[1])))
                t.SetWidth(FM(width))
                t.SetLayer(lid)
                t.SetNet(ni)
                board.Add(t)
                added["tracks"] += 1
                added["bottom"] += lid == B
        for pad, x, y in d["vias"]:
            if any(math.hypot(x - vx, y - vy) < 0.05 for vx, vy in have_via):
                continue
            m = re.search(r"_(\d+):(\d+)_um", pad)
            dia, drill = (int(m.group(1)) / 1000.0, int(m.group(2)) / 1000.0) if m else (0.7, 0.3)
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(pcbnew.VECTOR2I(FM(x), FM(y)))
            v.SetViaType(pcbnew.VIATYPE_THROUGH)
            v.SetLayerPair(F, B)
            v.SetDrill(FM(drill))
            v.SetWidth(F, FM(dia))
            v.SetNet(ni)
            board.Add(v)
            added["vias"] += 1
    pcbnew.SaveBoard(PCB, board)
    print("merge: %(tracks)d autorouted segments (%(bottom)d on the bottom layer) and %(vias)d vias added, "
          "%(kept)d hand-laid pieces left alone" % added)
    sys.stdout.flush()
    os._exit(0)


# ============================================================================ step 4: clean
def clean():
    """Remove the autorouter's dangling leftovers that the last DRC run reported (locked copper stays)."""
    with open(os.path.join(OUT, "drc.json"), encoding="utf-8") as f:
        rep = json.load(f)
    marks = []
    for v in rep.get("violations", []):
        if v["type"] not in ("track_dangling", "via_dangling"):
            continue
        i = v["items"][0]
        d = i["description"]
        m = re.search(r"on (F\.Cu|B\.Cu), length ([0-9.,]+) mm", d)
        marks.append((i["pos"]["x"], i["pos"]["y"], "via" if d.startswith("Via") else "track",
                      m.group(1) if m else None, float(m.group(2).replace(",", ".")) if m else None))
    board = pcbnew.LoadBoard(PCB)
    kill = []
    for t in list(board.GetTracks()):
        if t.IsLocked():
            continue
        is_via = t.GetClass() == "PCB_VIA"
        pts = [t.GetPosition()] if is_via else [t.GetStart(), t.GetEnd(), t.GetPosition()]
        for mx, my, kind, layer, length in marks:
            if (kind == "via") != is_via:
                continue
            if not any(abs(pcbnew.ToMM(q.x) - mx) < 0.02 and abs(pcbnew.ToMM(q.y) - my) < 0.02 for q in pts):
                continue
            if not is_via and (board.GetLayerName(t.GetLayer()) != layer or
                               abs(pcbnew.ToMM(t.GetLength()) - length) > 0.02):
                continue
            kill.append(t)
            break
    grave = []
    for t in kill:
        board.Remove(t)
        grave.append(t)
    pcbnew.SaveBoard(PCB, board)
    print("clean: %d dangling marks, removed %d autorouted tracks / vias" % (len(marks), len(kill)))
    sys.stdout.flush()
    os._exit(0)


# ============================================================================ step 5: ground
VIA_R, VIA_DRILL = 0.35, 0.3        # ground via: 0.7 mm pad, 0.3 mm hole
GRID = 5.0                          # stitching grid
GNDPLAN = os.path.join(OUT, "gnd_vias.json")


def _obstacles(board, code):
    """Copper that a ground via must keep away from: tracks, vias, pads; plus the ground pads that want a via."""
    mm = pcbnew.ToMM
    segs, vias, pads, want, yards = [], [], [], [], []
    for t in board.GetTracks():
        same = t.GetNetCode() == code
        if t.GetClass() == "PCB_VIA":
            vias.append((mm(t.GetPosition().x) - OX, mm(t.GetPosition().y) - OY, mm(t.GetWidth(F)) / 2, same))
        else:
            a, b = t.GetStart(), t.GetEnd()
            segs.append((mm(a.x) - OX, mm(a.y) - OY, mm(b.x) - OX, mm(b.y) - OY, mm(t.GetWidth()) / 2, same))
    for fp in board.GetFootprints():
        fx, fy = mm(fp.GetPosition().x) - OX, mm(fp.GetPosition().y) - OY
        cy = fp.GetCourtyard(F).BBox()
        yards.append((mm(cy.GetX()) - OX, mm(cy.GetY()) - OY, mm(cy.GetRight()) - OX, mm(cy.GetBottom()) - OY))
        for q in fp.Pads():
            if not (q.IsOnLayer(F) or q.IsOnLayer(B)):
                continue
            bb = q.GetBoundingBox()
            box = (mm(bb.GetX()) - OX, mm(bb.GetY()) - OY, mm(bb.GetRight()) - OX, mm(bb.GetBottom()) - OY)
            same = q.GetNetCode() == code
            th = q.GetAttribute() == pcbnew.PAD_ATTRIB_PTH
            pads.append(box + (same, th))
            if same and th:
                q.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)     # connector pins: solid into the pours
            if same and not th:
                want.append((fp.GetReference(), q.GetNumber(), box, fx, fy))
    return segs, vias, pads, want, yards


def _seg_dist(x, y, sg):
    x1, y1, x2, y2 = sg[:4]
    dx, dy = x2 - x1, y2 - y1
    n2 = dx * dx + dy * dy
    t = 0.0 if n2 < 1e-12 else max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / n2))
    return math.hypot(x - (x1 + t * dx), y - (y1 + t * dy))


def _box_dist(x, y, bx):
    return math.hypot(max(bx[0] - x, 0, x - bx[2]), max(bx[1] - y, 0, y - bx[3]))


def _free(x, y, segs, vias, pads, own=None, pitch=0.9):
    """Room for a ground via at (x, y)?"""
    if not (1.2 <= x <= W - 1.2 and 1.2 <= y <= H - 1.2):
        return False
    for sg in segs:
        if not sg[5] and _seg_dist(x, y, sg) - sg[4] < VIA_R + 0.25:
            return False
    for vx, vy, vr, same in vias:
        d = math.hypot(x - vx, y - vy)
        if d < pitch or (not same and d - vr < VIA_R + 0.25):
            return False
    for bx in pads:
        if bx[:4] == own:
            continue
        d = _box_dist(x, y, bx)
        if bx[5]:                                   # through-hole pad, any net
            if d < VIA_R + 0.35:
                return False
        elif d < VIA_R + (0.12 if bx[4] else 0.25):  # surface-mount pad: not inside it, not too near
            return False
    return True


def _path_free(a, b, segs, vias, pads, own):
    """The short track from a pad to its via must stay clear of other nets."""
    n = max(2, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 0.1))
    for i in range(n + 1):
        x, y = a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n
        if any(not sg[5] and _seg_dist(x, y, sg) - sg[4] < 0.4 for sg in segs):
            return False
        if any(not v[3] and math.hypot(x - v[0], y - v[1]) - v[2] < 0.4 for v in vias):
            return False
        if any(bx[:4] != own and not bx[4] and _box_dist(x, y, bx) < 0.4 for bx in pads):
            return False
    return True


def plan_ground(board):
    """A via beside every surface-mount ground pad: [(pad x, pad y, via x, via y)], and the pads without room."""
    segs, vias, pads, want, _yards = _obstacles(board, find_net(board, "GND").GetNetCode())
    plan, missing = [], []
    for ref, num, bx, fx, fy in want:
        m = re.search(r"(\d+)$", ref)
        if m and 900 <= int(m.group(1)) < 1000:          # audio chain: low frequency, the pour and the
            continue                                     # stitching grid are enough
        cx, cy = (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2
        g = 0.2 + VIA_R                                  # pad edge to via centre
        ox, oy = cx - fx, cy - fy                        # outwards = away from the middle of the part
        if abs(ox) >= abs(oy):
            first = (bx[2] + g, cy) if ox > 0 else (bx[0] - g, cy)
            rest = [(cx, bx[1] - g), (cx, bx[3] + g), (bx[0] - g, cy) if ox > 0 else (bx[2] + g, cy)]
        else:
            first = (cx, bx[3] + g) if oy > 0 else (cx, bx[1] - g)
            rest = [(bx[0] - g, cy), (bx[2] + g, cy), (cx, bx[1] - g) if oy > 0 else (cx, bx[3] + g)]
        shared = [(p[2], p[3]) for p in plan if _box_dist(p[2], p[3], bx) < 0.9]
        far = []
        for d in (g + 0.5, g + 1.0):                     # then anywhere around the pad, further out
            far += [(cx + sx * ((bx[2] - bx[0]) / 2 + d), cy + sy * ((bx[3] - bx[1]) / 2 + d))
                    for sx, sy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1))]
        for x, y in shared + [first] + rest + far:
            is_shared = (x, y) in shared
            if (is_shared or _free(x, y, segs, vias, pads, own=bx[:4])) and \
                    _path_free((cx, cy), (x, y), segs, vias, pads, bx[:4]):
                plan.append((cx, cy, x, y))
                if not is_shared:
                    vias.append((x, y, VIA_R, True))
                break
        else:
            missing.append("%s.%s" % (ref, num))
    return plan, missing


def finish():
    """Ground vias beside the ground pads (planned in step 'hand', kept free by rule areas during the
    autorouting), a stitching grid, then the ground pours on both layers."""
    board = pcbnew.LoadBoard(PCB)
    gnd = find_net(board, "GND")
    r = Router(board)
    grave = []
    for z in list(board.Zones()):
        if z.GetIsRuleArea() and z.GetZoneName().startswith("ground via"):
            board.Remove(z)
            grave.append(z)
    with open(GNDPLAN, encoding="utf-8") as f:
        plan = json.load(f)
    seen = set()
    for cx, cy, x, y in plan:
        if (x, y) not in seen:
            seen.add((x, y))
            r.via("GND", x, y, 2 * VIA_R, VIA_DRILL, lock=False)
        r.track("GND", F, 0.3, [(cx, cy), (x, y)], lock=False)
    for cell in ("lo1osc", "lo2"):                       # the two ground pads of each crystal, joined under its body
        r.track("GND", F, 0.2, [cell_pt(cell, -3.1, -2.75), cell_pt(cell, -5.3, -4.45)], lock=False)
    segs, vias, pads, _want, yards = _obstacles(board, gnd.GetNetCode())
    grid = 0
    k = int(W / GRID)
    for i in range(k):
        for j in range(k):
            x, y = GRID / 2 + i * GRID, GRID / 2 + j * GRID
            if any(c[0] - 0.3 <= x <= c[2] + 0.3 and c[1] - 0.3 <= y <= c[3] + 0.3 for c in yards):
                continue                                 # not under a part
            if _free(x, y, segs, vias, pads, pitch=1.6):
                r.via("GND", x, y, 2 * VIA_R, VIA_DRILL, lock=False)
                vias.append((x, y, VIA_R, True))
                grid += 1
    for layer, name in ((F, "GND top"), (B, "GND bottom")):
        z = pcbnew.ZONE(board)
        ls = pcbnew.LSET()
        ls.AddLayer(layer)
        z.SetLayerSet(ls)
        ol = z.Outline()
        ol.NewOutline()
        for x, y in ((0.4, 0.4), (W - 0.4, 0.4), (W - 0.4, H - 0.4), (0.4, H - 0.4)):
            ol.Append(FM(x + OX), FM(y + OY))
        z.SetNet(gnd)
        z.SetZoneName(name)
        z.SetAssignedPriority(0)
        z.SetMinThickness(FM(0.25))
        z.SetLocalClearance(FM(0.3))
        z.SetThermalReliefGap(FM(0.3))
        z.SetThermalReliefSpokeWidth(FM(0.4))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        board.Add(z)
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    extra = 0
    for _round in range(3):                              # islands of the top pour that have no via yet
        top = [z for z in board.Zones() if z.GetZoneName() == "GND top"][0]
        polys = top.GetFilledPolysList(F)
        added = 0
        for i in range(polys.OutlineCount()):
            ol = polys.Outline(i)
            if any(ol.PointInside(pcbnew.VECTOR2I(FM(v[0] + OX), FM(v[1] + OY))) for v in vias if v[3]):
                continue
            bb = ol.BBox()
            x0, y0 = pcbnew.ToMM(bb.GetX()) - OX, pcbnew.ToMM(bb.GetY()) - OY
            x1, y1 = pcbnew.ToMM(bb.GetRight()) - OX, pcbnew.ToMM(bb.GetBottom()) - OY
            done = False
            yy = y0 + 0.45
            while yy < y1 and not done:
                xx = x0 + 0.45
                while xx < x1 and not done:
                    inside = all(ol.PointInside(pcbnew.VECTOR2I(FM(xx + dx + OX), FM(yy + dy + OY)))
                                 for dx, dy in ((0.4, 0), (-0.4, 0), (0, 0.4), (0, -0.4)))
                    if inside and _free(xx, yy, segs, vias, pads, pitch=0.9):
                        r.via("GND", xx, yy, 2 * VIA_R, VIA_DRILL, lock=False)
                        vias.append((xx, yy, VIA_R, True))
                        added += 1
                        done = True
                    xx += 0.25
                yy += 0.25
            if not done and (x1 - x0) * (y1 - y0) > 2.0:      # slivers joined by a ground track are fine
                print("  top-pour island without room for a via: x %.1f..%.1f  y %.1f..%.1f" % (x0, x1, y0, y1))
        extra += added
        if not added:
            break
        filler.Fill(board.Zones())
    pcbnew.SaveBoard(PCB, board)
    print("finish: %d ground vias beside pads (%d pads), %d on the %.0f mm grid, %d more for islands of the top pour"
          % (len(seen), len(plan), grid, GRID, extra))
    sys.stdout.flush()
    os._exit(0)


# ============================================================================ step 5b: pockets of bare board
# Tracks cut the top pour into pieces. A piece that touches no ground pad or track and holds no via is dropped
# by the filler, and bare board is left (91 pockets, 227 mm2 before this step existed). Here each pocket that
# has room for a via gets one (more than one if it is long), so that it stays as ground copper.
# Left bare on purpose: pockets next to the common emitter node of a transistor pair. Ground copper there adds
# stray capacitance to that node (layout rule 4 for the squarer; the same caution for the other pairs).
# The step can be run again: a pocket that already has its via is left alone.
POCKET_SHY = 0.6                    # mm: a pocket this near to a common emitter node stays bare
POCKET_PITCH = 6.0                  # mm between the vias of one long pocket
# Emitter nodes where a few tenths of a pF more do not matter: mixer 2 (MMBT3904 at 14 MHz; the transistors
# alone put about 10 pF on the node) and the regulator (DC). The pockets next to them are filled.
POCKET_FREE = ("em1", "em2", "ret")


def _common_emitter_nets(board):
    """Nets that join the emitters (pad 2 of the SOT-23) of two or more transistors."""
    count = {}
    for fp in board.GetFootprints():
        if fp.GetReference().startswith("Q"):
            for q in fp.Pads():
                if q.GetNumber() == "2":
                    count[q.GetNetname()] = count.get(q.GetNetname(), 0) + 1
    return {n for n, c in count.items()
            if c >= 2 and n not in ("GND", "VCC") and n.split("/")[-1] not in POCKET_FREE}


def pockets():
    board = pcbnew.LoadBoard(PCB)
    mm = pcbnew.ToMM
    gnd = find_net(board, "GND")
    r = Router(board)
    segs, vias, pads, _want, yards = _obstacles(board, gnd.GetNetCode())
    P = lambda x, y: pcbnew.VECTOR2I(FM(x + OX), FM(y + OY))                    # noqa: E731
    shy_nets = _common_emitter_nets(board)
    shy = []                                             # points on the copper of those nets
    for t in board.GetTracks():
        if t.GetNetname() in shy_nets and t.GetClass() != "PCB_VIA":
            a, b = t.GetStart(), t.GetEnd()
            ax, ay, bx, by = mm(a.x) - OX, mm(a.y) - OY, mm(b.x) - OX, mm(b.y) - OY
            n = max(1, int(math.hypot(bx - ax, by - ay) / 0.2))
            shy += [(ax + (bx - ax) * i / n, ay + (by - ay) * i / n, t.GetNetname()) for i in range(n + 1)]
    for fp in board.GetFootprints():
        for q in fp.Pads():
            if q.GetNetname() in shy_nets:
                bb = q.GetBoundingBox()
                for x in (bb.GetX(), bb.GetRight()):
                    for y in (bb.GetY(), bb.GetBottom()):
                        shy.append((mm(x) - OX, mm(y) - OY, q.GetNetname()))
    gnd_pts = [((bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2) for bx in pads if bx[4]]         # ground pads
    for sg in segs:                                                                          # ground tracks
        if sg[5]:
            n = max(1, int(math.hypot(sg[2] - sg[0], sg[3] - sg[1]) / 0.3))
            gnd_pts += [(sg[0] + (sg[2] - sg[0]) * i / n, sg[1] + (sg[3] - sg[1]) * i / n) for i in range(n + 1)]
    top = [z for z in board.Zones() if z.GetZoneName() == "GND top"][0]
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    area0 = top.GetFilledPolysList(F).Area() / 1e12
    top.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_NEVER)
    added, tied, bare = 0, 0, []
    ring = [(math.cos(k * math.pi / 4) * (VIA_R + 0.03), math.sin(k * math.pi / 4) * (VIA_R + 0.03)) for k in range(8)]
    for _round in range(3):
        filler.Fill(board.Zones())
        polys = top.GetFilledPolysList(F)
        new, bare = 0, []
        for i in range(polys.OutlineCount()):
            ol = polys.Outline(i)
            bb = ol.BBox()
            x0, y0, x1, y1 = mm(bb.GetX()) - OX, mm(bb.GetY()) - OY, mm(bb.GetRight()) - OX, mm(bb.GetBottom()) - OY
            inbox = lambda p, m=0.0: x0 - m <= p[0] <= x1 + m and y0 - m <= p[1] <= y1 + m      # noqa: E731
            if any(v[3] and inbox(v) and ol.PointInside(P(v[0], v[1])) for v in vias):
                continue                                 # has a via
            if any(inbox(p) and ol.PointInside(P(p[0], p[1])) for p in gnd_pts):
                continue                                 # hangs on a ground pad or a ground track
            size = abs(ol.Area()) / 1e12
            pts = [(mm(ol.CPoint(k).x) - OX, mm(ol.CPoint(k).y) - OY) for k in range(ol.PointCount())]
            edges = [(pts[k][0], pts[k][1], pts[(k + 1) % len(pts)][0], pts[(k + 1) % len(pts)][1]) for k in range(len(pts))]
            near = [s for s in shy if inbox(s, POCKET_SHY) and min(_seg_dist(s[0], s[1], e) for e in edges) < POCKET_SHY]
            if near:
                bare.append((size, x0, y0, x1, y1, "next to " + near[0][2].split("/")[-1]))
                continue
            spots = []
            for step in (0.25, 0.1, 0.05):
                yy = y0 + VIA_R
                while yy < y1 - VIA_R + 1e-6:
                    xx = x0 + VIA_R
                    while xx < x1 - VIA_R + 1e-6:
                        if not any(c[0] - 0.3 <= xx <= c[2] + 0.3 and c[1] - 0.3 <= yy <= c[3] + 0.3 for c in yards) \
                                and polys.Contains(P(xx, yy), i) \
                                and all(polys.Contains(P(xx + dx, yy + dy), i) for dx, dy in ring) \
                                and _free(xx, yy, segs, vias, pads, pitch=0.9):
                            spots.append((xx, yy))
                        xx += step
                    yy += step
                if spots or size > 30.0:
                    break
            if not spots:
                bare.append((size, x0, y0, x1, y1, "no room for a via"))
                continue
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            spots.sort(key=lambda s: math.hypot(s[0] - cx, s[1] - cy))
            mine = []
            for s in spots:
                if all(math.hypot(s[0] - m[0], s[1] - m[1]) >= POCKET_PITCH for m in mine):
                    mine.append(s)
            for x, y in mine:
                r.via("GND", x, y, 2 * VIA_R, VIA_DRILL, lock=False)
                vias.append((x, y, VIA_R, True))
            new += len(mine)
            tied += 1
        added += new
        if not new:
            break
    top.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    filler.Fill(board.Zones())
    area1 = top.GetFilledPolysList(F).Area() / 1e12
    pcbnew.SaveBoard(PCB, board)
    print("pockets: %d pockets tied to ground with %d vias; top pour %.0f -> %.0f mm2" % (tied, added, area0, area1))
    bare.sort(reverse=True)
    print("left bare: %d pockets, %.1f mm2 together" % (len(bare), sum(b[0] for b in bare)))
    for size, x0, y0, x1, y1, why in bare[:14]:
        print("   %.1f mm2  x %.1f..%.1f  y %.1f..%.1f  %s" % (size, x0, x1, y0, y1, why))
    sys.stdout.flush()
    os._exit(0)


# ============================================================================ step 6: silkscreen
# (text, x, y, height, angle). The part references are not printed (266 parts, no room): they are on the
# fabrication layer, and ../rx2_refs.csv and the pictures in ../preview give the place of every part.
SILK_TEXT = [
    ("QFH RX v2", 59.0, 88.5, 1.6, 0), ("Edy Grigore  2026-11", 59.0, 91.5, 1.0, 0),
    ("ESP32 DevKitC V4", 21.0, 88.6, 1.2, 0), ("pin 1 and antenna at this end >", 19.5, 90.7, 1.0, 0),
    ("< USB", 3.0, 91.0, 1.0, 0),
    # A label for each block, along the signal path. The places were searched by script: no label lies on a
    # pad or under a part, and none runs along a track. A few cross a ground via, which the solder mask covers.
    ("ANT", 4.9, 19.2, 1.0, 0),
    ("INPUT FILTER", 10.17, 6.50, 1.0, 0),
    ("LOW NOISE AMPLIFIER", 15.64, 22.25, 1.0, 0),
    ("FILTER 137.9 MHz", 28.07, 19.00, 1.0, 0),
    ("MIXER 1", 43.28, 9.00, 1.0, 0),
    ("25 MHz OSCILLATOR", 13.28, 40.50, 1.0, 0),
    ("MULTIPLIER x5", 44.25, 46.85, 1.0, 90),
    ("125 MHz FILTER", 42.53, 24.75, 1.0, 0),
    ("FILTER 12.9 MHz", 70.29, 5.75, 1.0, 0),
    ("IF AMPLIFIER 1  12.9 MHz", 98.60, 38.10, 1.0, 90),
    ("MIXER 2", 89.10, 48.75, 1.0, 0),
    ("14.318 MHz CRYSTAL OSCILLATOR", 70.11, 86.00, 1.0, 0),
    ("IF AMPLIFIER 2  1.418 MHz", 50.67, 68.75, 1.0, 0),
    ("LIMITER", 43.84, 60.00, 1.0, 0),
    ("FM DETECTOR", 21.05, 51.00, 1.0, 0),
    ("AUDIO FILTER", 8.12, 64.00, 1.0, 0),
    ("AUDIO AMPLIFIER", 1.75, 53.48, 1.0, 90),
    ("3.3 V REGULATOR", 12.78, 83.75, 1.0, 0),
    ("BIAS", 61.23, 36.00, 1.0, 0),
    ("BIAS", 40.23, 49.00, 1.0, 0),
]
# outline of the DevKitC board and of its module end, so that it is plugged in the right way round
SILK_LINES = [
    [(0.75, 72.8), (0.75, 94.2)],
    [(49.9, 72.8), (49.9, 74.5), (55.55, 74.5), (55.55, 92.5), (49.9, 92.5), (49.9, 94.2)],
]
# The owner's mark, bottom right, between two rows of ground vias: the name, and a small raised "TM" as the
# trademark sign, with letters 1 mm high so that JLCPCB can print them.
# (name, sign, x of the right end, y of the centre line of the name, height of the name, height of the sign)
SILK_MARK = ("Dedeghe", "TM", 93.5, 95.0, 2.0, 1.0)


def _silk_text(board, text, x, y, hgt, ang=0):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(text)
    t.SetLayer(pcbnew.F_SilkS)
    t.SetPosition(V(x, y))
    t.SetTextSize(pcbnew.VECTOR2I(FM(hgt), FM(hgt)))
    t.SetTextThickness(FM(max(0.15, hgt * 0.15)))
    t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
    t.SetTextAngleDegrees(ang)
    board.Add(t)
    return t


def silk():
    board = pcbnew.LoadBoard(PCB)
    for d in list(board.GetDrawings()):                  # texts and lines of an earlier run of this step
        if d.GetLayer() == pcbnew.F_SilkS:
            board.Delete(d)                              # not Remove(): with that, KiCad 10's Python crashes later
    for fp in board.GetFootprints():
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)
    for text, x, y, hgt, ang in SILK_TEXT:
        _silk_text(board, text, x, y, hgt, ang)
    name, sign, xr, yc, h1, h2 = SILK_MARK
    ys = yc - h1 / 2 + h2 / 2                            # the sign's top is level with the name's top
    a = _silk_text(board, name, 0.0, yc, h1)
    b = _silk_text(board, sign, 0.0, ys, h2)
    wa = pcbnew.ToMM(a.GetBoundingBox().GetWidth())
    wb = pcbnew.ToMM(b.GetBoundingBox().GetWidth())
    b.SetPosition(V(xr - wb, ys))
    a.SetPosition(V(xr - wb - 0.3 - wa, yc))
    print("silk: mark '%s' %.1f mm wide, sign '%s' %.1f mm wide, from x %.1f to %.1f" % (name, wa, sign, wb, xr - wb - 0.3 - wa, xr))
    for pts in SILK_LINES:
        for a, b in zip(pts, pts[1:]):
            sh = pcbnew.PCB_SHAPE(board)
            sh.SetShape(pcbnew.SHAPE_T_SEGMENT)
            sh.SetStart(V(*a))
            sh.SetEnd(V(*b))
            sh.SetLayer(pcbnew.F_SilkS)
            sh.SetWidth(FM(0.15))
            board.Add(sh)
    pcbnew.SaveBoard(PCB, board)
    print("silk: %d texts, %d outline pieces; part references hidden" % (len(SILK_TEXT), sum(len(q) - 1 for q in SILK_LINES)))
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        if cmd == "hand":
            hand()
        elif cmd == "auto":
            auto(float(sys.argv[2]) if len(sys.argv) > 2 else 8)
        elif cmd == "merge":
            merge()
        elif cmd == "clean":
            clean()
        elif cmd == "finish":
            finish()
        elif cmd == "pockets":
            pockets()
        elif cmd == "silk":
            silk()
        else:
            print(__doc__)
    except Exception:
        import traceback
        traceback.print_exc()
        sys.stderr.flush()
        os._exit(1)
