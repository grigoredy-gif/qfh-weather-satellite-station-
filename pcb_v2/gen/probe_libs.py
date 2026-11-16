"""probe_libs.py - print the pin numbers of the KiCad symbols and the pads of the footprints
that the rev 2 schematic uses, so the part-type table in ../README.md can be checked by eye.
Run: <KiCad>\bin\python.exe probe_libs.py"""
import os, re, sys, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kisch

def pins(lib_id):
    try:
        s = kisch.resolve_symbol(lib_id)
    except Exception as e:
        print("  %-34s MISSING (%s)" % (lib_id, e)); return
    print("  %-34s %s" % (lib_id, "  ".join("%s=%s(%g,%g)" % (p["number"], p["name"], p["x"], p["y"])
                                             for p in kisch.symbol_pins(s))))

def pads(fp):
    lib, name = fp.split(":")
    path = os.path.join(kisch.FPDIR, lib + ".pretty", name + ".kicad_mod")
    if not os.path.exists(path):
        print("  %-52s MISSING" % fp); return
    root = kisch.parse(open(path, encoding="utf-8").read())[0]
    out = []
    for e in root:
        if isinstance(e, list) and e and e[0] == "pad":
            at = kisch._child(e, "at"); sz = kisch._child(e, "size")
            out.append("%s:%s@(%s,%s)%sx%s" % (e[1], e[2], at[1], at[2], sz[1], sz[2]))
    print("  %-52s %s" % (fp, " ".join(out[:8]) + (" ... %d pads" % len(out) if len(out) > 8 else "")))

print("SYMBOLS")
for s in ["Transistor_BJT:Q_NPN_BEC", "Transistor_BJT:Q_PNP_BEC", "Diode:BAV99", "Device:Crystal_GND24",
          "Device:D_Schottky", "Device:R", "Device:C", "Device:L", "Connector:Conn_Coaxial",
          "Connector:Conn_01x19_Socket", "power:VCC", "power:GND", "power:PWR_FLAG"]:
    pins(s)
for lib, pat in (("Diode", r"^(BAS70|BAT54|BAS40|BAT54)[A-Z0-9_-]*$"), ("Device", r"^D_Schottky")):
    names = [n for n in kisch._lib(lib) if re.match(pat, n)]
    print("  %s matches: %s" % (lib, " ".join(sorted(names))))
print("FOOTPRINTS")
for f in ["Package_TO_SOT_SMD:SOT-23", "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm", "Inductor_SMD:L_0603_1608Metric",
          "Inductor_SMD:L_1008_2520Metric", "Inductor_SMD:L_1210_3225Metric", "Resistor_SMD:R_0603_1608Metric",
          "Capacitor_SMD:C_0603_1608Metric", "Capacitor_SMD:C_1206_3216Metric",
          "Connector_PinSocket_2.54mm:PinSocket_1x19_P2.54mm_Vertical", "Diode_SMD:D_SOT-23_ANK"]:
    pads(f)
print("  SMA edge footprints: " + " ".join(os.path.basename(p)[:-10] for p in
      glob.glob(os.path.join(kisch.FPDIR, "Connector_Coaxial.pretty", "SMA*Edge*"))))
