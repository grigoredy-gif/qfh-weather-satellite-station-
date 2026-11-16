"""probe_fp.py - print pads and courtyard of every KiCad footprint the schematic uses (from ../rx2_refs.csv).
Run: <KiCad 10>\bin\python.exe probe_fp.py"""
import csv, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kisch

def xy(e):
    return float(e[1]), float(e[2])

def probe(fp):
    lib, name = fp.split(":")
    root = kisch.parse(open(os.path.join(kisch.FPDIR, lib + ".pretty", name + ".kicad_mod"), encoding="utf-8").read())[0]
    pads, pts = [], []
    for e in root:
        if not isinstance(e, list) or not e:
            continue
        if e[0] == "pad":
            at, sz, dr = kisch._child(e, "at"), kisch._child(e, "size"), kisch._child(e, "drill")
            pads.append("%s %s (%s,%s) %sx%s%s" % (e[1], e[2], at[1], at[2], sz[1], sz[2],
                        " drill " + " ".join(str(x) for x in dr[1:] if not isinstance(x, list)) if dr else ""))
        lay = kisch._child(e, "layer")
        if e[0] in ("fp_line", "fp_rect", "fp_poly") and lay and str(lay[1]) == "F.CrtYd":
            for k in ("start", "end"):
                c = kisch._child(e, k)
                if c:
                    pts.append(xy(c))
            p = kisch._child(e, "pts")
            if p:
                pts += [xy(q) for q in p[1:]]
    box = "courtyard x %.2f..%.2f y %.2f..%.2f" % (min(p[0] for p in pts), max(p[0] for p in pts),
                                                   min(p[1] for p in pts), max(p[1] for p in pts)) if pts else "no courtyard"
    print("%s\n   %s\n   %s" % (fp, box, "; ".join(pads[:10]) + (" ... %d pads" % len(pads) if len(pads) > 10 else "")))

with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rx2_refs.csv"), encoding="utf-8") as f:
    fps = sorted({r["footprint"] for r in csv.DictReader(f)})
for fp in fps + ["Connector_Coaxial:SMA_Samtec_SMA-J-P-H-ST-EM1_EdgeMount"]:
    probe(fp)
