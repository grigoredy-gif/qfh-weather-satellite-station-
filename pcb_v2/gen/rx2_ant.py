"""
rx2_ant.py - the antenna track leaves the SMA jack on the bottom layer (KiCad 10 pcbnew).

The autorouter ran the track from the centre pin of the SMA jack J101 on the top layer: 2.2 mm of it under
the jack's body and 1.2 mm of that under its metal base, with only the solder mask between. A jack soldered
at home can get a piece of tape under it. A jack soldered by JLCPCB cannot. This step moves that piece to the
bottom layer: a bottom track from the centre pin to a via beside the jack, and from the via the old top track.
After it only ground copper lies under the jack on the top side.

The rule area that keeps the bottom layer free of tracks under the front end is cut back to x = EDGE, so
that it no longer covers the jack. No tuned part sits left of that line.

Run it once on the finished board, with KiCad's Python (KiCad closed):
  <KiCad 10>\\bin\\python.exe rx2_ant.py
Then: rx2_route.py pockets, rx2_board.py drc all, rx2_fab.py.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pcbnew  # noqa: E402
from rx2_board import PCB, OX, OY, FM, V  # noqa: E402
from rx2_route import Router, F, B  # noqa: E402
from rx2_holes import P, seg_dist, box_dist, pour_pieces  # noqa: E402

JACK, PIN = "J101", "1"
BODY = 6.5                                               # mm: the jack's body is a square of this size
VIA_X = 10.75                                            # mm: the via, 0.65 mm outside the body
AREA, EDGE = "no bottom tracks: front end and mixer 1", 11.0
mm = pcbnew.ToMM


def main():
    board = pcbnew.LoadBoard(PCB)
    jack = [fp for fp in board.GetFootprints() if fp.GetReference() == JACK][0]
    pin = [q for q in jack.Pads() if q.GetNumber() == PIN][0]
    code, net = pin.GetNetCode(), pin.GetNetname()
    px, py = P(pin.GetPosition())
    if any(t.GetNetCode() == code and t.GetClass() != "PCB_VIA" and t.GetLayer() == B for t in board.GetTracks()):
        raise SystemExit("net %s already has a track on the bottom layer; nothing done" % net)
    before = pour_pieces(board)

    # 1. the top track that starts at the centre pin
    mine = []
    for t in board.GetTracks():
        if t.GetNetCode() != code or t.GetClass() == "PCB_VIA" or t.GetLayer() != F:
            continue
        a, b = P(t.GetStart()), P(t.GetEnd())
        if math.hypot(a[0] - px, a[1] - py) < 1e-3:
            mine.append((t, b, t.SetStart))
        elif math.hypot(b[0] - px, b[1] - py) < 1e-3:
            mine.append((t, a, t.SetEnd))
    if len(mine) != 1:
        raise SystemExit("expected one top track at the centre pin of %s, found %d" % (JACK, len(mine)))
    t, far, setter = mine[0]
    if abs(far[1] - py) > 1e-3 or far[0] < VIA_X + 0.3:
        raise SystemExit("the track from the centre pin does not run straight to the right: it ends at (%.3f, %.3f)" % far)
    edge = px + BODY / 2
    width = mm(t.GetWidth())
    under = min(far[0], edge) - px
    if VIA_X - 0.35 < edge + 0.5:
        raise SystemExit("the via would be nearer than 0.5 mm to the body of the jack")

    # 2. bottom track, via, and the rest of the top track
    setter(V(VIA_X, py))
    r = Router(board)
    short = net.split("/")[-1]
    r.via(short, VIA_X, py, 0.7, 0.3, lock=True)
    r.track(short, B, width, [(px, py), (VIA_X, py)], lock=True)

    # 3. the rule area no longer covers the jack
    zone = [z for z in board.Zones() if z.GetIsRuleArea() and z.GetZoneName() == AREA]
    if len(zone) != 1:
        raise SystemExit("rule area '%s' not found" % AREA)
    ol = zone[0].Outline()
    moved = 0
    for i in range(ol.TotalVertices()):
        v = ol.CVertex(i)
        if abs(mm(v.x) - OX) < 1e-6:
            ol.SetVertex(i, pcbnew.VECTOR2I(FM(EDGE + OX), v.y))
            moved += 1
    if moved != 2:
        raise SystemExit("rule area '%s': %d corners at the left edge, expected 2" % (AREA, moved))
    if hasattr(zone[0], "HatchBorder"):
        zone[0].HatchBorder()

    # 4. what is near the new copper (for the record; the rules check decides)
    near_via, near_trk = (9.9, ""), (9.9, "")
    for o in board.GetTracks():
        if o.GetNetCode() == code:
            continue
        if o.GetClass() == "PCB_VIA":
            vx, vy = P(o.GetPosition())
            rad = mm(o.GetWidth(F)) / 2
            near_via = min(near_via, (math.hypot(vx - VIA_X, vy - py) - rad - 0.35, "via " + o.GetNetname().split("/")[-1]))
            near_trk = min(near_trk, (seg_dist(vx, vy, (px, py), (VIA_X, py)) - rad - width / 2, "via " + o.GetNetname().split("/")[-1]))
        else:
            d = seg_dist(VIA_X, py, P(o.GetStart()), P(o.GetEnd())) - mm(o.GetWidth()) / 2 - 0.35
            near_via = min(near_via, (d, "track %s on %s" % (o.GetNetname().split("/")[-1], board.GetLayerName(o.GetLayer()))))
    for fp in board.GetFootprints():
        for q in fp.Pads():
            if q.GetNetCode() == code:
                continue
            what = "pad %s.%s" % (fp.GetReference(), q.GetNumber())
            near_via = min(near_via, (box_dist(VIA_X, py, q.GetBoundingBox()) - 0.35, what))
            if q.IsOnLayer(B):
                near_trk = min(near_trk, (min(box_dist(px + (VIA_X - px) * i / 40.0, py, q.GetBoundingBox()) for i in range(41)) - width / 2, what))

    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(PCB, board)
    after = pour_pieces(board)
    print("antenna track of %s: %.2f mm of top track under the body before, none now" % (JACK, under))
    print("  bottom track (%.2f, %.2f) to (%.2f, %.2f), %.2f mm, width %.2f; via at (%.2f, %.2f), its copper %.2f mm from the body" % (
        px, py, VIA_X, py, VIA_X - px, width, VIA_X, py, VIA_X - 0.35 - edge))
    print("  top track left: (%.2f, %.2f) to (%.3f, %.3f), %.2f mm" % (VIA_X, py, far[0], far[1], far[0] - VIA_X))
    print("  nearest copper of another net: to the via %s, %.2f mm; to the bottom track %s, %.2f mm" % (near_via[1], near_via[0], near_trk[1], near_trk[0]))
    print("  rule area '%s' now starts at x = %.1f" % (AREA, EDGE))
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
