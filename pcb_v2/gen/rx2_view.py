"""
rx2_view.py - picture of a part of the board, for checking the layout by eye.

  rx2_view.py <name> <x0> <y0> <x1> <y1> [layers] [px per mm] [refs]

Plots the board with kicad-cli to SVG, cuts out the rectangle (board millimetres, (0, 0) = top left corner)
and renders it to ../preview/<name>.png with headless Chrome or Edge.
layers: comma separated KiCad layer names, default F.Cu,B.Cu,F.Fab,Edge.Cuts
refs:   "sim" (default) shows the names of the simulation on the fabrication layer instead of R101, C205, ...;
        "ref" shows the board references.
"""
import math
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
CLI = r"C:\Users\grigo\AppData\Local\Programs\KiCad\10.0\bin\kicad-cli.exe"
BROWSERS = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"]
OX, OY = 100.0, 50.0


def main():
    name = sys.argv[1]
    x0, y0, x1, y1 = (float(v) for v in sys.argv[2:6])
    layers = sys.argv[6] if len(sys.argv) > 6 else "F.Cu,B.Cu,F.Fab,Edge.Cuts"
    k = float(sys.argv[7]) if len(sys.argv) > 7 else 24.0
    refs = sys.argv[8] if len(sys.argv) > 8 else "sim"
    prev = os.path.join(OUT, "preview")
    os.makedirs(prev, exist_ok=True)
    board = os.path.join(OUT, "rx2_receiver.kicad_pcb")
    if refs == "sim":                       # a copy of the board whose references are the simulation names
        import pcbnew
        b = pcbnew.LoadBoard(board)
        for fp in b.GetFootprints():
            if fp.HasField("Sim"):
                fp.SetReference(fp.GetFieldText("Sim").replace("spare_", "sp_"))
        board = os.path.join(prev, "_view.kicad_pcb")
        pcbnew.SaveBoard(board, b, True)
    svg = os.path.join(prev, "_view.svg")
    if os.path.exists(svg):
        os.remove(svg)
    r = subprocess.run([CLI, "pcb", "export", "svg", "--mode-single", "-o", svg, "--layers", layers,
                        "--page-size-mode", "0", "--exclude-drawing-sheet", "--drill-shape-opt", "2", board],
                       capture_output=True, text=True)
    if not os.path.exists(svg):
        sys.exit("svg export failed: " + r.stdout + r.stderr)
    with open(svg, encoding="utf-8") as f:
        head = f.read(3000)
    m = re.search(r'width="([\d.]+)mm"\s+height="([\d.]+)mm"', head)
    wmm, hmm = float(m.group(1)), float(m.group(2))      # the whole sheet: positions are sheet millimetres
    w, h = (x1 - x0) * k, (y1 - y0) * k
    html = os.path.join(prev, "_view.html")
    with open(html, "w", encoding="utf-8") as f:
        f.write('<html><body style="margin:0;background:#fff"><div style="width:%dpx;height:%dpx;overflow:hidden;'
                'position:relative"><img src="_view.svg" style="position:absolute;left:%.1fpx;top:%.1fpx;'
                'width:%.1fpx;height:%.1fpx"></div></body></html>'
                % (w, h, -(x0 + OX) * k, -(y0 + OY) * k, wmm * k, hmm * k))
    png = os.path.join(prev, name + ".png")
    if os.path.exists(png):
        os.remove(png)
    browser = next((b for b in BROWSERS if os.path.exists(b)), None)
    subprocess.run([browser, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    "--user-data-dir=" + os.path.join(os.environ.get("TEMP", prev), "kisch_chrome_profile"),
                    "--window-size=%d,%d" % (math.ceil(w), math.ceil(h)), "--force-device-scale-factor=1",
                    "--screenshot=" + png, "file:///" + html.replace("\\", "/")], capture_output=True)
    print("%s: %.0f x %.0f mm at %.0f px/mm -> %s" % (name, x1 - x0, y1 - y0, k, png if os.path.exists(png) else "PNG FAILED"))
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
