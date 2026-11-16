"""
rx2_holes.py - four mounting holes for M3 screws on the finished board of receiver version 2 (KiCad 10 pcbnew).

Run it once, after rx2_route.py silk, with KiCad's Python (KiCad closed):
  <KiCad 10>\\bin\\python.exe rx2_holes.py
Then: rx2_route.py pockets, rx2_board.py drc all, rx2_fab.py.

The holes are 3.2 mm wide and not plated. They sit at HOLES (board millimetres, (0, 0) = top left corner):
a rectangle of 92.0 x 86.0 mm. The lower pair is 9.5 mm above the bottom edge, because the socket row J1002
runs along that edge; the lower left hole lies under the DevKitC.

Inside a circle of KEEP mm around each hole (screw head, washer or standoff) there is only ground copper, on
both layers. To make that room this step
  - replaces the corner of the 3.3 V trunk in the top right corner by a diagonal (CUT_TOP to CUT_EAST);
  - moves the fiducial marks FID1 and FID2 and the silkscreen text "< USB";
  - adds two ground vias that tie the copper left in the top right corner to the bottom pour;
  - fills the ground pours again.
Nothing else on the board is touched. The circuit does not change.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pcbnew  # noqa: E402
from rx2_board import PCB, OX, OY, FM, V, load_fp  # noqa: E402
from rx2_route import find_net, Router, F, B  # noqa: E402

FOOTPRINT = "MountingHole:MountingHole_3.2mm_M3"
HOLE = 3.2                                               # mm
HOLES = [("H1", 4.0, 4.5), ("H2", 96.0, 4.5), ("H3", 4.0, 90.5), ("H4", 96.0, 90.5)]
KEEP = 3.5                                               # mm from the hole centre: ground copper only
POUR_GAP = 0.5                                           # mm between the hole and the ground pour
TRUNK = ("VCC", 0.5, (97.4, 2.6), (88.6, 2.6), (97.4, 11.4))     # net, width, old corner, CUT_TOP, CUT_EAST
FID_MOVES = {"FID1": (10.0, 3.0), "FID2": (90.0, 9.5)}
TEXT_MOVES = {"< USB": (9.0, 91.0)}
CORNER_VIAS = [(92.0, 1.5), (98.5, 8.5)]
mm = pcbnew.ToMM


def P(v):
    return mm(v.x) - OX, mm(v.y) - OY


def seg_dist(x, y, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    n2 = dx * dx + dy * dy
    t = 0.0 if n2 < 1e-12 else max(0.0, min(1.0, ((x - a[0]) * dx + (y - a[1]) * dy) / n2))
    return math.hypot(x - (a[0] + t * dx), y - (a[1] + t * dy))


def box_dist(x, y, bb):
    x0, y0, x1, y1 = mm(bb.GetX()) - OX, mm(bb.GetY()) - OY, mm(bb.GetRight()) - OX, mm(bb.GetBottom()) - OY
    return math.hypot(max(x0 - x, 0, x - x1), max(y0 - y, 0, y - y1))


def copper(board, x, y, skip_net=None, skip_fp=()):
    """[(distance from (x, y) to the copper edge, what)] for tracks, vias and pads, nearest first."""
    out = []
    for t in board.GetTracks():
        if skip_net is not None and t.GetNetCode() == skip_net:
            continue
        if t.GetClass() == "PCB_VIA":
            vx, vy = P(t.GetPosition())
            out.append((math.hypot(x - vx, y - vy) - mm(t.GetWidth(F)) / 2, "via %s" % t.GetNetname().split("/")[-1]))
        else:
            out.append((seg_dist(x, y, P(t.GetStart()), P(t.GetEnd())) - mm(t.GetWidth()) / 2,
                        "track %s on %s" % (t.GetNetname().split("/")[-1], board.GetLayerName(t.GetLayer()))))
    for fp in board.GetFootprints():
        if fp.GetReference() in skip_fp:
            continue
        for q in fp.Pads():
            if skip_net is not None and q.GetNetCode() == skip_net:
                continue
            out.append((box_dist(x, y, q.GetBoundingBox()), "pad %s.%s" % (fp.GetReference(), q.GetNumber())))
    return sorted(out)


def pour_pieces(board):
    return {z.GetZoneName(): (z.GetFilledPolysList(z.GetFirstLayer()).OutlineCount(),
                              z.GetFilledPolysList(z.GetFirstLayer()).Area() / 1e12)
            for z in board.Zones() if not z.GetIsRuleArea()}


def main():
    board = pcbnew.LoadBoard(PCB)
    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    if any(name in fps for name, _x, _y in HOLES):
        raise SystemExit("the mounting holes are already on the board; nothing done")
    gnd = find_net(board, "GND")
    before = pour_pieces(board)
    r = Router(board)

    # 1. the trunk corner in the top right
    net, width, corner, cut_top, cut_east = TRUNK
    code = find_net(board, net).GetNetCode()
    ends = []
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA" or t.GetNetCode() != code or t.GetLayer() != F:
            continue
        a, b = P(t.GetStart()), P(t.GetEnd())
        for mine, other, setter in ((a, b, t.SetStart), (b, a, t.SetEnd)):
            if math.hypot(mine[0] - corner[0], mine[1] - corner[1]) < 1e-3:
                ends.append((t, other, setter))
    if len(ends) != 2:
        raise SystemExit("expected two %s tracks ending at %s, found %d" % (net, corner, len(ends)))
    for t, other, setter in ends:
        if abs(other[1] - corner[1]) < 1e-3 and other[0] < cut_top[0]:
            new = cut_top                                # the track along the top edge
        elif abs(other[0] - corner[0]) < 1e-3 and other[1] > cut_east[1]:
            new = cut_east                               # the track along the east edge
        else:
            raise SystemExit("a %s track at the corner runs somewhere unexpected: to %s" % (net, other))
        setter(V(*new))
    for t in board.GetTracks():                          # nothing of this net may hang on the removed corner piece
        if t.GetNetCode() != code or any(t is e[0] for e in ends):
            continue
        pts = [P(t.GetPosition())] if t.GetClass() == "PCB_VIA" else [P(t.GetStart()), P(t.GetEnd())]
        for p in pts:
            if min(seg_dist(p[0], p[1], cut_top, corner), seg_dist(p[0], p[1], corner, cut_east)) < 0.3 \
                    and min(math.hypot(p[0] - c[0], p[1] - c[1]) for c in (cut_top, cut_east)) > 1e-3:
                raise SystemExit("a %s track or via hangs on the corner piece at (%.2f, %.2f)" % (net, p[0], p[1]))
    r.track(net, F, width, [cut_top, cut_east], lock=True)

    # 2. fiducial marks and the text that are in the way
    for ref, (x, y) in FID_MOVES.items():
        near = [c for c in copper(board, x, y, skip_fp=(ref,)) if c[0] < 1.5]
        if near:
            raise SystemExit("%s cannot go to (%.1f, %.1f): %s is %.2f mm away" % (ref, x, y, near[0][1], near[0][0]))
        fps[ref].SetPosition(V(x, y))
    moved = 0
    for g in board.GetDrawings():
        if g.GetClass() == "PCB_TEXT" and g.GetText() in TEXT_MOVES:
            g.SetPosition(V(*TEXT_MOVES[g.GetText()]))
            moved += 1
    if moved != len(TEXT_MOVES):
        raise SystemExit("texts to move: %d found, %d expected" % (moved, len(TEXT_MOVES)))

    # 3. the holes
    for name, x, y in HOLES:
        bad = [c for c in copper(board, x, y, skip_net=gnd.GetNetCode()) if c[0] < KEEP]
        if bad:
            raise SystemExit("%s at (%.1f, %.1f): %s is only %.2f mm from the centre" % (name, x, y, bad[0][1], bad[0][0]))
        for d, what in copper(board, x, y):
            if d < HOLE / 2 + 0.25:
                raise SystemExit("%s at (%.1f, %.1f): %s is %.2f mm from the centre, inside the hole" % (name, x, y, what, d))
        fp = load_fp(FOOTPRINT)
        fp.SetReference(name)
        fp.SetValue("M3 hole")
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)
        fp.SetBoardOnly(True)
        fp.SetExcludedFromBOM(True)
        fp.SetExcludedFromPosFiles(True)
        for q in fp.Pads():
            q.SetLocalClearance(FM(POUR_GAP))
        board.Add(fp)
        fp.SetPosition(V(x, y))
        fp.SetLocked(True)

    # 4. ground vias for the copper left in the top right corner, then the pours
    for x, y in CORNER_VIAS:
        near = [c for c in copper(board, x, y) if c[0] < 0.35 + 0.25]
        if near:
            raise SystemExit("no room for a ground via at (%.1f, %.1f): %s" % (x, y, near[0][1]))
        r.via("GND", x, y, 0.7, 0.3, lock=False)
    board.GetTitleBlock().SetRevision("board of 2026-11-15")
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    top = [z for z in board.Zones() if z.GetZoneName() == "GND top"][0].GetFilledPolysList(F)
    bot = [z for z in board.Zones() if z.GetZoneName() == "GND bottom"][0].GetFilledPolysList(B)
    for x, y in CORNER_VIAS:
        pt = pcbnew.VECTOR2I(FM(x + OX), FM(y + OY))
        if not (top.Contains(pt) and bot.Contains(pt)):
            raise SystemExit("the ground via at (%.1f, %.1f) is not inside both pours" % (x, y))
    pcbnew.SaveBoard(PCB, board)

    after = pour_pieces(board)
    print("holes: %s, %.1f mm, not plated" % (", ".join("%s (%.1f, %.1f)" % h for h in HOLES), HOLE))
    for name, x, y in HOLES:
        d, what = copper(board, x, y, skip_net=gnd.GetNetCode(), skip_fp=(name,))[0]
        print("  %s: nearest copper that is not ground: %s, %.2f mm from the centre" % (name, what, d))
    print("trunk %s: corner %s replaced by a diagonal from %s to %s" % (net, corner, cut_top, cut_east))
    print("moved: %s; text %s" % (", ".join("%s to (%.1f, %.1f)" % (k, v[0], v[1]) for k, v in FID_MOVES.items()),
                                  ", ".join("'%s' to (%.1f, %.1f)" % (k, v[0], v[1]) for k, v in TEXT_MOVES.items())))
    for name in sorted(before):
        print("pour %-10s: %d pieces, %.0f mm2  ->  %d pieces, %.0f mm2" % ((name,) + before[name] + after[name]))


if __name__ == "__main__":
    try:
        main()
        sys.stdout.flush()
        os._exit(0)
    except SystemExit as e:
        print("STOPPED:", e)
        sys.stdout.flush()
        os._exit(1)
    except Exception:
        import traceback
        traceback.print_exc()
        sys.stderr.flush()
        os._exit(1)
