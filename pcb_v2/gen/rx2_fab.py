"""
rx2_fab.py - the files for JLCPCB in ../fabrication/: Gerber zip, and two pairs of BOM and placement file.

  rx2_receiver_jlc_bom.csv, rx2_receiver_jlc_cpl.csv
      the 252 surface-mount parts; the connectors are soldered by hand at home
  rx2_receiver_jlc_bom_with_connectors.csv, rx2_receiver_jlc_cpl_with_connectors.csv
      the same, and JLCPCB also solders the SMA jack and the two DevKitC sockets

The placement file needs care. JLCPCB places every part by its own footprint, and some of those are drawn
turned against KiCad's (the SOT-23 parts) or have their origin elsewhere (the socket strips: KiCad's origin
is pin 1, JLCPCB's is the middle). jlc_pads.json holds the pad positions of JLCPCB's footprint for every LCSC
number on the board. For each part this script finds the angle, and for the connectors also the place, at
which JLCPCB's footprint lands on the board's pads, writes them, and stops if a part does not land.

The drill files are checked too: the holes in them are counted and compared with the holes of the board.

Not in any BOM or placement file: the spare capacitor positions (not fitted).
Run: <KiCad 10>/bin/python.exe rx2_fab.py
"""
import csv
import json
import math
import os
import re
import shutil
import subprocess
import sys
import zipfile

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from rx2_board import read_netlist, NETLIST, PCB, CLI, OUT  # noqa: E402

FAB = os.path.join(OUT, "fabrication")
TMP = os.path.join(FAB, "_gerbers")
PADS = os.path.join(HERE, "jlc_pads.json")
FIT = 0.45          # mm: JLCPCB's pad centre may be this far from the board's (other land size, same package)
CLEAR = 0.9         # mm: every other angle must miss by at least this much
# through-hole connectors: LCSC number -> the name in the BOM
CONNECTORS = {"C496549": "SMA jack BWSMA-KE-Z001", "C2932678": "Socket 1x19 2.54mm KH-2.54FH-1X19P-H8.5"}

README = """Files for JLCPCB, receiver version 2. Made by gen/rx2_fab.py from the board file.

Upload:
- rx2_receiver_gerbers_jlc.zip   as the Gerber file
- then ONE of these two pairs as the BOM and as the placement (CPL) file:
  A. JLCPCB also solders the connectors (the SMA jack J101 and the two DevKitC sockets J1001, J1002):
       rx2_receiver_jlc_bom_with_connectors.csv   and   rx2_receiver_jlc_cpl_with_connectors.csv
  B. The connectors are soldered by hand at home:
       rx2_receiver_jlc_bom.csv                   and   rx2_receiver_jlc_cpl.csv

Board settings (option names as on JLCPCB's order page on 2026-11-14):
- Base Material FR-4, Layers 2, PCB Qty 5, Delivery Format Single PCB, PCB Thickness 1.6mm,
  PCB Color Green. The size (100 x 100 mm) comes from the Gerber file.
- Surface Finish: LeadFree HASL (HASL with lead and ENIG also work). NOT OSP, which the page lists
  first: JLCPCB's economic assembly takes only HASL or ENIG on a green 1.6 mm board. With OSP the
  order becomes Standard assembly (quote of 2026-11-14: EUR 143.52 for 2 assembled boards, of which
  EUR 88.46 is a loading fee of about EUR 1.40 for each of the 63 part lines).
- Outer Copper Weight 1 oz, Via Covering Tented, Min via hole size 0.3mm.
- Mark on PCB: Remove Mark. Gold Fingers, Castellated Holes, Edge Plating: No.
- PCB Build Time: a free one. The paid "24 hours" is not needed.
- Leave every other option as the page sets it.
- The board has four mounting holes of %(hole)s mm for M3 screws. They are not plated and have their own
  drill file in the zip (rx2_receiver-NPTH.drl). The order page needs no setting for them.

PCB Assembly:
- PCBA Type Economic, Assembly Side Top Side, PCBA Qty 2.
- Confirm Parts Placement: Yes.
- Leave the other assembly options as the page sets them.
- After the upload JLCPCB must find every BOM line: %(lines_a)d lines (%(parts_a)d parts) with pair A,
  %(lines_b)d lines (%(parts_b)d parts) with pair B. If it marks one as not found or short of stock, do not
  pick a replacement by hand: the circuit is simulated with these parts.
- Pair A costs about 12.70 dollars more than pair B for two boards. This is computed from JLCPCB's fee
  table of 2026-11-15, it is not a quote: two more Extended lines at 3.07 dollars each, hand-soldering
  labour 3.58, 86 solder joints at 0.0164, and the parts (0.40 for a jack, 0.19 for a socket). Both
  connector parts are through-hole, "Extended", and allowed in Economic assembly (JLCPCB's part pages,
  2026-11-15). JLCPCB solders them by hand.

Before paying:
- Look at JLCPCB's placement preview. Every SOT-23 part must sit with its three legs on its three
  pads. The angles in the placement file are already turned to JLCPCB's footprints (%(turned)s)
  and checked by script against JLCPCB's footprint data. The preview is the only check at JLCPCB itself.
- With pair A also look at the connectors in the preview: the SMA jack on its five holes at the top
  left, and one socket strip on each row of 19 holes at the bottom left.
- Measure the DevKitC that will be plugged in. The board assumes 25.40 mm between its two pin rows.
  With pair A the sockets arrive soldered, so measure before the order.

When the boards arrive:
- Measure with an ohmmeter from the centre of the SMA jack to its shell before anything else: about
  10 kohm is right (R101). The antenna track leaves the jack on the bottom side, so only ground copper
  lies under the metal base of the jack, and no tape is needed there.

Not in any BOM or placement file, on purpose: the 11 spare capacitor positions (not fitted). With
pair B also the SMA jack J101 and the two DevKitC sockets J1001 and J1002.
"""


def run(*a):
    r = subprocess.run([CLI] + list(a), capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-500:], r.stderr[-500:])
        raise SystemExit("kicad-cli failed: " + " ".join(a[:3]))


def order(ref):
    m = re.match(r"([A-Z]+)(\d+)", ref)
    return (m.group(1), int(m.group(2)))


def turn(x, y, deg):
    """Turn a point counter-clockwise as seen on the board (y points down)."""
    a = math.radians(deg)
    return x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a)


def angle_for(fp, jlc):
    """Angle to add to KiCad's rotation so that JLCPCB's footprint lands on this footprint's pads."""
    o = fp.GetPosition()
    mine = {p.GetNumber(): (pcbnew.ToMM(p.GetPosition().x - o.x), pcbnew.ToMM(p.GetPosition().y - o.y))
            for p in fp.Pads() if p.GetNumber()}
    if set(mine) != set(jlc):
        raise SystemExit("%s: pad numbers differ, board %s, JLCPCB %s" % (fp.GetReference(), sorted(mine), sorted(jlc)))
    k = fp.GetOrientationDegrees()
    miss = {}
    for add in (0, 90, 180, 270):
        miss[add] = max(math.hypot(turn(*jlc[n], k + add)[0] - mine[n][0], turn(*jlc[n], k + add)[1] - mine[n][1])
                        for n in mine)
    best = min(miss, key=miss.get)
    others = min(v for a, v in miss.items() if a != best)
    if miss[best] > FIT or others < CLEAR:
        raise SystemExit("%s: no clear angle, misses %s" % (fp.GetReference(), {a: round(v, 2) for a, v in miss.items()}))
    return best, miss[best]


def connector_place(fp, jlc):
    """Where the origin of JLCPCB's footprint must be (sheet mm) and at which angle, so that its pads land on
    this footprint's pads. If both footprints number their pads alike, the pads are matched by number and only
    one angle may fit. If not (the SMA jack: one centre pin and four equal legs), they are matched by place,
    and KiCad's own angle is taken when it fits. Returns (x, y, angle, largest difference, angles that fit)."""
    mine = [(p.GetNumber(), pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)) for p in fp.Pads() if p.GetNumber()]
    if len(mine) != len(jlc):
        raise SystemExit("%s: %d pads on the board, %d in JLCPCB's footprint" % (fp.GetReference(), len(mine), len(jlc)))
    by_number = sorted(n for n, _x, _y in mine) == sorted(jlc) and len(set(n for n, _x, _y in mine)) == len(mine)
    cx, cy = sum(m[1] for m in mine) / len(mine), sum(m[2] for m in mine) / len(mine)
    fits = {}
    for ang in (0, 90, 180, 270):
        t = {n: turn(v[0], v[1], ang) for n, v in jlc.items()}
        ox, oy = cx - sum(v[0] for v in t.values()) / len(t), cy - sum(v[1] for v in t.values()) / len(t)
        if by_number:
            miss = max(math.hypot(ox + t[n][0] - x, oy + t[n][1] - y) for n, x, y in mine)
        else:
            miss = max(max(min(math.hypot(ox + v[0] - x, oy + v[1] - y) for _n, x, y in mine) for v in t.values()),
                       max(min(math.hypot(ox + v[0] - x, oy + v[1] - y) for v in t.values()) for _n, x, y in mine))
        fits[ang] = (miss, ox, oy)
    good = sorted(a for a in fits if fits[a][0] <= FIT)
    if not good:
        raise SystemExit("%s: JLCPCB's footprint does not land, misses %s" % (fp.GetReference(), {a: round(v[0], 2) for a, v in fits.items()}))
    if by_number:
        if len(good) != 1 or min(v[0] for a, v in fits.items() if a != good[0]) < CLEAR:
            raise SystemExit("%s: no clear angle, misses %s" % (fp.GetReference(), {a: round(v[0], 2) for a, v in fits.items()}))
        ang = good[0]
    else:
        k = int(round(fp.GetOrientationDegrees())) % 360
        ang = k if k in good else good[0]
    return fits[ang][1], fits[ang][2], ang, fits[ang][0], len(good)


def holes_of_board(board):
    """{(diameter in mm, plated): number of holes} from the pads and vias of the board."""
    n = {}
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA":
            k = (round(pcbnew.ToMM(t.GetDrill()), 3), True)
            n[k] = n.get(k, 0) + 1
    for fp in board.GetFootprints():
        for p in fp.Pads():
            d = pcbnew.ToMM(p.GetDrillSize().x)
            if d > 0:
                k = (round(d, 3), p.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH)
                n[k] = n.get(k, 0) + 1
    return n


def holes_of_file(path, plated):
    """{(diameter in mm, plated): number of hits} from an Excellon file."""
    tools, n, cur = {}, {}, None
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            m = re.match(r"T(\d+)C([\d.]+)", line)
            if m:
                tools[m.group(1)] = round(float(m.group(2)), 3)
                continue
            m = re.match(r"T(\d+)$", line)
            if m:
                cur = m.group(1)
                continue
            if re.match(r"X-?[\d.]+Y-?[\d.]+$", line) and cur in tools:
                n[(tools[cur], plated)] = n.get((tools[cur], plated), 0) + 1
    return n


def main():
    if os.path.isdir(FAB):
        shutil.rmtree(FAB)
    os.makedirs(TMP)
    run("pcb", "export", "gerbers", "-o", TMP + os.sep, "--layers",
        "F.Cu,B.Cu,F.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts", "--no-x2", "--no-netlist", PCB)
    run("pcb", "export", "drill", "-o", TMP + os.sep, "--format", "excellon", "--excellon-units", "mm",
        "--excellon-zeros-format", "decimal", "--excellon-separate-th", PCB)
    files = sorted(os.listdir(TMP))
    board = pcbnew.LoadBoard(PCB)
    want = holes_of_board(board)
    got = {}
    for f in files:
        if f.endswith(".drl"):
            if not (f.endswith("-PTH.drl") or f.endswith("-NPTH.drl")):
                raise SystemExit("unexpected drill file: " + f)
            got.update(holes_of_file(os.path.join(TMP, f), f.endswith("-PTH.drl")))
    if got != want:
        raise SystemExit("the drill files and the board differ: files %s, board %s" % (sorted(got.items()), sorted(want.items())))
    with zipfile.ZipFile(os.path.join(FAB, "rx2_receiver_gerbers_jlc.zip"), "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(os.path.join(TMP, f), f)

    comps, _nets = read_netlist(NETLIST)
    groups, lcsc, conn = {}, {}, {}
    for ref, c in comps.items():
        num = c["fields"].get("LCSC", "")
        if c["fields"].get("Assembly") == "JLCPCB":         # not the connectors, not the spare positions
            key = (num, c["value"], c["footprint"].split(":")[-1])
            groups.setdefault(key, []).append(ref)
            lcsc[ref] = num
        elif num in CONNECTORS:
            conn.setdefault((num, CONNECTORS[num], c["footprint"].split(":")[-1]), []).append(ref)
    if sorted(k[0] for k in conn) != sorted(CONNECTORS):
        raise SystemExit("connectors in the netlist: %s, expected %s" % (sorted(k[0] for k in conn), sorted(CONNECTORS)))
    rows = [[val, ",".join(sorted(refs, key=order)), fpname, num]
            for (num, val, fpname), refs in sorted(groups.items(), key=lambda kv: order(min(kv[1], key=order)))]
    conn_rows = [[val, ",".join(sorted(refs, key=order)), fpname, num]
                 for (num, val, fpname), refs in sorted(conn.items(), key=lambda kv: order(min(kv[1], key=order)))]
    for name, body in (("rx2_receiver_jlc_bom.csv", rows), ("rx2_receiver_jlc_bom_with_connectors.csv", rows + conn_rows)):
        with open(os.path.join(FAB, name), "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
            w.writerows(body)

    jlc = json.load(open(PADS, encoding="utf-8"))
    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    added, worst = {}, (0.0, "")
    for ref in lcsc:
        if lcsc[ref] not in jlc:
            raise SystemExit("%s: no pad data for %s in jlc_pads.json" % (ref, lcsc[ref]))
        add, miss = angle_for(fps[ref], {n: tuple(v) for n, v in jlc[lcsc[ref]]["pads"].items()})
        if added.setdefault(lcsc[ref], add) != add:
            raise SystemExit("%s: another angle than the other parts with %s" % (ref, lcsc[ref]))
        if miss > worst[0]:
            worst = (miss, ref)

    pos = os.path.join(FAB, "_pos.csv")
    run("pcb", "export", "pos", "-o", pos, "--format", "csv", "--units", "mm", "--side", "front", "--exclude-dnp", PCB)
    cpl = []
    with open(pos, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            ref = row["Ref"]
            if ref not in lcsc:
                continue
            fp = fps[ref]
            x, y = pcbnew.ToMM(fp.GetPosition().x), pcbnew.ToMM(fp.GetPosition().y)
            if abs(float(row["PosX"]) - x) > 0.001 or abs(float(row["PosY"]) + y) > 0.001 \
                    or abs((float(row["Rot"]) - fp.GetOrientationDegrees() + 180) % 360 - 180) > 0.001:
                raise SystemExit("%s: the position file and the board differ" % ref)
            cpl.append([ref, row["PosX"] + "mm", row["PosY"] + "mm", "Top",
                        "%g" % ((float(row["Rot"]) + added[lcsc[ref]]) % 360)])
    os.remove(pos)
    shutil.rmtree(TMP)
    if len(cpl) != len(lcsc):
        raise SystemExit("placement file has %d parts, the BOM %d" % (len(cpl), len(lcsc)))

    conn_cpl, conn_words = [], []
    for (num, _val, _fpname), refs in sorted(conn.items(), key=lambda kv: order(min(kv[1], key=order))):
        if num not in jlc:
            raise SystemExit("no pad data for %s in jlc_pads.json" % num)
        for ref in sorted(refs, key=order):
            x, y, ang, miss, nfit = connector_place(fps[ref], {n: tuple(v) for n, v in jlc[num]["pads"].items()})
            conn_cpl.append([ref, "%.6fmm" % x, "%.6fmm" % -y, "Top", "%g" % ang])
            conn_words.append("%s at (%.2f, %.2f) on the sheet, %d degrees, largest difference %.2f mm%s"
                              % (ref, x, y, ang, miss, "" if nfit == 1 else " (%d angles fit: the part looks the same turned)" % nfit))
    for name, body in (("rx2_receiver_jlc_cpl.csv", cpl), ("rx2_receiver_jlc_cpl_with_connectors.csv", cpl + conn_cpl)):
        with open(os.path.join(FAB, name), "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
            w.writerows(body)

    turned = {}
    for num, add in added.items():
        if add:
            turned.setdefault(add, []).append(num)
    words = "; ".join("%d degrees for %s" % (a, ", ".join(sorted(v, key=lambda c: int(c[1:])))) for a, v in sorted(turned.items()))
    npth = sorted(d for (d, plated) in want if not plated)
    with open(os.path.join(FAB, "READ_ME_FIRST.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(README % dict(turned=words, hole=" and ".join("%g" % d for d in npth) or "no",
                              lines_a=len(rows) + len(conn_rows), parts_a=len(cpl) + len(conn_cpl),
                              lines_b=len(rows), parts_b=len(cpl)))
    print("gerbers: %d files in the zip; drill files: %d plated holes, %d not plated, as on the board (%s)" % (
        len(files), sum(n for (d, p), n in want.items() if p), sum(n for (d, p), n in want.items() if not p),
        ", ".join("%d x %g mm%s" % (n, d, "" if p else " not plated") for (d, p), n in sorted(want.items()))))
    print("BOM: %d lines, %d parts; with connectors %d lines, %d parts" % (len(rows), len(cpl), len(rows) + len(conn_rows), len(cpl) + len(conn_cpl)))
    print("angles added to KiCad's rotation: %s; 0 for the other %d part numbers" % (words, len(added) - sum(len(v) for v in turned.values())))
    print("every part lands on its pads with JLCPCB's footprint; largest difference %.2f mm (%s)" % worst)
    for wd in conn_words:
        print("connector " + wd)


if __name__ == "__main__":
    main()
