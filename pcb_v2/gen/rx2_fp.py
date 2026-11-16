"""
rx2_fp.py - writes the project footprint library ../rx2.pretty.

KiCad's standard footprints do not match the land patterns in the data sheets of four parts, so each gets its
own footprint, derived from a KiCad one (numbers: vault note "Rev 2 footprint research (2026-11-14)"):

  L_0603_LQW18A               Murata LQW18AN: pads 0.65 x 0.9 mm centred at +-0.675 mm
                              (Murata: gap 0.6 to 0.8, outer span 1.9 to 2.0, width 0.7 to 1.0; larger pads lower Q)
  L_1008_AHW2520C             APV AHW2520C: pads 1.02 x 2.54 mm centred at +-1.145 mm (gap 1.27 mm)
  L_1210_NLV32                TDK NLV32-EF: pads 1.2 x 2.0 mm centred at +-1.6 mm (gap 2.0 mm)
  SMA_BWSMA-KE-Z001_Vertical  BAT WIRELESS BWSMA-KE-Z001, a vertical through-hole jack: five holes of 1.4 mm,
                              centre pin and four legs on a 5.08 mm square

Run: <KiCad 10>\\bin\\python.exe rx2_fp.py      (before rx2_sch.py)
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
KICAD = r"C:\Users\grigo\AppData\Local\Programs\KiCad\10.0"
FPDIR = os.path.join(KICAD, "share", "kicad", "footprints")
LIB = os.path.join(OUT, "rx2.pretty")
FM = pcbnew.FromMM
KEEP = []   # removed items stay referenced until the process ends


def V(x, y):
    return pcbnew.VECTOR2I(FM(x), FM(y))


def shape(fp, kind, layer, a, b, width):
    s = pcbnew.PCB_SHAPE(fp)
    s.SetShape(kind)
    s.SetStart(V(*a))
    s.SetEnd(V(*b))
    s.SetLayer(layer)
    s.SetWidth(FM(width))
    fp.Add(s)


def save(fp, name, descr):
    fp.SetFPID(pcbnew.LIB_ID("rx2", name))
    fp.SetLibDescription(descr)
    path = os.path.join(LIB, name + ".kicad_mod")
    if os.path.exists(path):
        os.remove(path)
    pcbnew.PCB_IO_KICAD_SEXPR().FootprintSave(LIB, fp)
    print("%-28s %s" % (name, "; ".join("%s (%.3f, %.3f) %.2f x %.2f" % (
        p.GetNumber(), pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y),
        pcbnew.ToMM(p.GetSize().x), pcbnew.ToMM(p.GetSize().y)) for p in fp.Pads())))


def chip(src, name, pad_len, pad_wid, centre, body_l, body_w, descr):
    fp = pcbnew.FootprintLoad(os.path.join(FPDIR, "Inductor_SMD.pretty"), src)
    fp.SetPosition(V(0, 0))
    for p in fp.Pads():
        p.SetSize(V(pad_len, pad_wid))
        p.SetPosition(V(-centre if p.GetNumber() == "1" else centre, 0))
    for g in list(fp.GraphicalItems()):
        if g.GetClass() == "PCB_SHAPE" and g.GetLayer() in (pcbnew.F_CrtYd, pcbnew.F_SilkS, pcbnew.F_Fab):
            fp.Remove(g)
            KEEP.append(g)
    hx = max(body_l / 2, centre + pad_len / 2) + 0.25
    hy = max(body_w, pad_wid) / 2 + 0.25
    shape(fp, pcbnew.SHAPE_T_RECT, pcbnew.F_CrtYd, (-hx, -hy), (hx, hy), 0.05)
    shape(fp, pcbnew.SHAPE_T_RECT, pcbnew.F_Fab, (-body_l / 2, -body_w / 2), (body_l / 2, body_w / 2), 0.1)
    sx = centre - pad_len / 2 - 0.2          # silkscreen: two short lines in the gap between the pads
    sy = max(body_w, pad_wid) / 2 + 0.12
    if sx > 0.12:
        for s in (-1, 1):
            shape(fp, pcbnew.SHAPE_T_SEGMENT, pcbnew.F_SilkS, (-sx, s * sy), (sx, s * sy), 0.12)
    save(fp, name, descr)


def sma():
    fp = pcbnew.FootprintLoad(os.path.join(FPDIR, "Connector_Coaxial.pretty"), "SMA_Amphenol_132134_Vertical")
    fp.SetPosition(V(0, 0))
    for p in fp.Pads():
        d = 2.0 if p.GetNumber() == "1" else 2.3
        p.SetDrillSize(V(1.4, 1.4))
        p.SetSize(V(d, d))
    save(fp, "SMA_BWSMA-KE-Z001_Vertical",
         "SMA jack, vertical, through hole, BAT WIRELESS BWSMA-KE-Z001 (LCSC C496549): centre pin and four "
         "0.9 mm square legs on a 5.08 mm square, holes 1.4 mm")


def main():
    if not os.path.isdir(LIB):
        os.makedirs(LIB)
    chip("L_0603_1608Metric", "L_0603_LQW18A", 0.65, 0.9, 0.675, 1.6, 0.8,
         "Murata LQW18A wirewound inductor, 0603: land pattern of the data sheet (gap 0.7, outer span 2.0, width 0.9)")
    chip("L_1008_2520Metric", "L_1008_AHW2520C", 1.02, 2.54, 1.145, 2.92, 2.70,
         "APV AHW2520C wirewound inductor, 1008: land pattern of the data sheet (pads 1.02 x 2.54, gap 1.27)")
    chip("L_1210_3225Metric", "L_1210_NLV32", 1.2, 2.0, 1.6, 3.2, 2.5,
         "TDK NLV32-EF wound inductor, 1210: land pattern of the data sheet (pads 1.2 x 2.0, gap 2.0)")
    sma()


if __name__ == "__main__":
    try:
        main()
        sys.stdout.flush()
        os._exit(0)
    except Exception:
        import traceback
        traceback.print_exc()
        sys.stderr.flush()
        os._exit(1)
