"""
rx2_measure.py - the distances on the board that the layout rules ask for.

For two nets it gives the smallest distance between their copper (tracks, vias and pads, measured
between points sampled every 0.2 mm along the tracks and at the corners and centres of the pads).
It also lists the tracks on the bottom layer and the track length of the tuned nodes.
It only reads the board. Run: <KiCad 10>/bin/python.exe rx2_measure.py
"""
import math
import os

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(os.path.dirname(HERE), "rx2_receiver.kicad_pcb")
OX, OY = 100.0, 50.0                      # sheet position of the board's top-left corner, mm

# rule 7: the nodes of the pump driver, pump and detector against the tuned nodes of the first IF
STRONG = ["c2", "x", "vp", "ec", "bc1", "vfc", "cb", "det"]
FIRST_IF = ["t1", "t2", "t3", "m2in"]
# rule 3: the pump driver against the first tuned node of the second IF
RULE3 = [("c2", "t5"), ("x", "t5")]
LENGTHS = ["t1", "t2", "t3", "m2in", "t5", "t6", "c2", "x", "eq"]


def mm(v):
    return pcbnew.ToMM(v)


def load():
    board = pcbnew.LoadBoard(PCB)
    pts, length, full = {}, {}, {}
    bottom = []
    for t in board.GetTracks():
        name = t.GetNetname()
        short = name.split("/")[-1]
        full.setdefault(short, set()).add(name)
        a, b = t.GetStart(), t.GetEnd()
        ax, ay, bx, by = mm(a.x) - OX, mm(a.y) - OY, mm(b.x) - OX, mm(b.y) - OY
        d = math.hypot(bx - ax, by - ay)
        n = max(1, int(d / 0.2))
        pts.setdefault(short, []).extend((ax + (bx - ax) * i / n, ay + (by - ay) * i / n) for i in range(n + 1))
        if t.GetClass() == "PCB_TRACK":
            length[short] = length.get(short, 0.0) + d
            if t.GetLayer() == pcbnew.B_Cu:
                bottom.append((short, ax, ay, bx, by, d, mm(t.GetWidth())))
    for fp in board.GetFootprints():
        for p in fp.Pads():
            name = p.GetNetname()
            short = name.split("/")[-1]
            full.setdefault(short, set()).add(name)
            bb = p.GetBoundingBox()
            x0, y0 = mm(bb.GetX()) - OX, mm(bb.GetY()) - OY
            x1, y1 = mm(bb.GetRight()) - OX, mm(bb.GetBottom()) - OY
            pts.setdefault(short, []).extend([(x0, y0), (x1, y0), (x0, y1), (x1, y1), ((x0 + x1) / 2, (y0 + y1) / 2)])
    return pts, length, full, bottom


def dist(pts, a, b):
    best = (1e9, None, None)
    for p in pts[a]:
        for q in pts[b]:
            d = math.hypot(p[0] - q[0], p[1] - q[1])
            if d < best[0]:
                best = (d, p, q)
    return best


def main():
    pts, length, full, bottom = load()
    for n in sorted(set(STRONG + FIRST_IF + ["t5"] + LENGTHS)):
        if n not in pts:
            raise SystemExit("net not on the board: " + n)
        if len(full[n]) != 1:
            raise SystemExit("net name is not unique: %s %s" % (n, sorted(full[n])))
    print("Rule 7: smallest copper distance to the tuned nodes of the first IF, mm (board coordinates)")
    print("  %-5s" % "" + "".join("%8s" % v for v in FIRST_IF) + "   nearest")
    for s in STRONG:
        row = [dist(pts, s, v) for v in FIRST_IF]
        k = min(range(len(row)), key=lambda i: row[i][0])
        d, p, q = row[k]
        print("  %-5s" % s + "".join("%8.1f" % r[0] for r in row)
              + "   %s: (%.1f, %.1f) to (%.1f, %.1f)" % (FIRST_IF[k], p[0], p[1], q[0], q[1]))
    print("Rule 3: pump driver to the first tuned node of the second IF, mm")
    for a, b in RULE3:
        print("  %s - %s  %.1f" % (a, b, dist(pts, a, b)[0]))
    print("Track length of the tuned and strong nodes, mm")
    print("  " + ",  ".join("%s %.1f" % (n, length.get(n, 0.0)) for n in LENGTHS))
    print("Tracks on the bottom layer")
    total = 0.0
    for n, ax, ay, bx, by, d, w in bottom:
        total += d
        print("  %-4s (%.2f, %.2f) to (%.2f, %.2f)  %.2f mm, width %.2f" % (n, ax, ay, bx, by, d, w))
    print("  total %.1f mm in %d pieces" % (total, len(bottom)))


if __name__ == "__main__":
    main()
