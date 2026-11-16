"""
frhelp.py - running Freerouting 2.1.0 and reading its result.

These functions come from the routing script of another board of mine (2026-11-10), unchanged:
strip_net (take one net out of a Specctra DSN file), run_freerouting (start Freerouting with its window,
watch its log, stop it so that it writes the session file) and read_session (wires and vias of the session
file, in KiCad millimetres).
"""
import os
import re
import subprocess
import time

FREEROUTING = ["java", "-jar", r"C:\Users\grigo\Tools\freerouting-2.1.0\freerouting-2.1.0.jar"]


def strip_net(dsn, netname):
    """Remove one net from a Specctra DSN (its pins become plain, netless obstacles for the router)."""
    with open(dsn, encoding="utf-8") as f:
        text = f.read()
    for head in ("(net %s\n" % netname, '(net "%s"\n' % netname):
        i = text.find(head)
        if i < 0:
            continue
        depth, j = 0, i
        while True:
            ch = text[j]
            depth += (ch == "(") - (ch == ")")
            j += 1
            if depth == 0:
                break
        text = text[:i] + text[j:]
    out, pos = [], 0
    while True:
        i = text.find("(class ", pos)
        if i < 0:
            break
        k = text.find("(circuit", i)
        head = text[i:k]
        toks = head.split(" ")
        head = " ".join(t for t in toks if t.strip() not in (netname, '"%s"' % netname))
        out.append(text[pos:i] + head)
        pos = k
    out.append(text[pos:])
    with open(dsn, "w", encoding="utf-8") as f:
        f.write("".join(out))


def _click_cancel(title_part):
    """Post a left click into the centre of the Freerouting window ("click anywhere on the canvas to cancel")."""
    import ctypes
    import ctypes.wintypes as wt
    u32 = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(hwnd, _):
        n = u32.GetWindowTextLengthW(hwnd)
        if n and u32.IsWindowVisible(hwnd):
            buf = ctypes.create_unicode_buffer(n + 1)
            u32.GetWindowTextW(hwnd, buf, n + 1)
            if buf.value.startswith(title_part + " - Freerouting"):
                found.append(hwnd)
        return True

    u32.EnumWindows(cb, 0)
    for hwnd in found:
        if u32.IsIconic(hwnd):
            u32.ShowWindow(hwnd, 9)
            time.sleep(1.0)
        rc = wt.RECT()
        u32.GetClientRect(hwnd, ctypes.byref(rc))
        lp = (((rc.bottom - rc.top) // 2) << 16) | (((rc.right - rc.left) // 2) & 0xFFFF)
        u32.PostMessageW(hwnd, 0x0200, 0, lp)
        u32.PostMessageW(hwnd, 0x0201, 1, lp)
        u32.PostMessageW(hwnd, 0x0202, 0, lp)
    return bool(found)


def run_freerouting(dsn, ses, log, minutes, patience=25, min_passes=8, stall_min=4.0):
    """Run Freerouting 2.1.0 with its window and stop it ourselves so that it writes the session file.
    (A normal end of a GUI run crashes before saving, and headless mode saves a stale snapshot: see v27's pcb.py.)"""
    def kill_tree(proc):
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)

    if os.path.exists(ses):
        os.remove(ses)
    title = os.path.basename(dsn)
    with open(log, "w", encoding="utf-8") as lf:
        p = subprocess.Popen(FREEROUTING + ["-de", dsn, "-do", ses, "-mp", "9999", "-mt", "1", "-da", "-dct", "1"],
                             stdout=lf, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
        t0 = last_t = time.time()
        seen, best, best_pass, clicked, tries = 0, None, 0, None, 1
        while p.poll() is None:
            time.sleep(2)
            with open(log, encoding="utf-8", errors="replace") as f:
                passes = [(int(a), int(b)) for a, b in re.findall(r"pass #(\d+) .*?\((\d+) unrouted[ )]", f.read())]
            if len(passes) != seen:
                seen, last_t = len(passes), time.time()
                n, unrouted = passes[-1]
                if best is None or unrouted < best:
                    best, best_pass = unrouted, n
                stop = (unrouted == 0 and n >= min_passes) or (n >= min_passes and n - best_pass >= patience) or \
                    time.time() - t0 > minutes * 60
                if clicked is None and stop and (unrouted == best or time.time() - t0 > minutes * 60 + 120):
                    if _click_cancel(title):
                        clicked = time.time()
                        print("stopped Freerouting after pass %d: %d unrouted (best %d at pass %d)"
                              % (n, unrouted, best, best_pass), flush=True)
            if clicked is not None and os.path.exists(ses) and os.path.getsize(ses) > 0:
                size = -1
                while os.path.getsize(ses) != size:
                    size = os.path.getsize(ses)
                    time.sleep(3)
                try:
                    p.wait(30)
                except subprocess.TimeoutExpired:
                    kill_tree(p)
                break
            if clicked is not None and not os.path.exists(ses) and time.time() - clicked > 20:
                if tries >= 6:
                    print("Freerouting ignored 6 stop clicks - killed", flush=True)
                    kill_tree(p)
                    break
                if _click_cancel(title):
                    tries += 1
                    clicked = time.time()
                    print("stop click again (%d)" % tries, flush=True)
            if clicked is None and time.time() - last_t > stall_min * 60:
                print("Freerouting stalled (no pass for %.0f min) - killed" % stall_min, flush=True)
                kill_tree(p)
                break
    return os.path.exists(ses) and os.path.getsize(ses) > 0


def read_session(path):
    """Wires and vias of a Specctra session file: {net: {"wires": [(layer, width, [(x, y), ...])], "vias": [(pad, x, y)]}}.
    Session units are 0.1 um with y up; the result is in KiCad mm."""
    from kisch import parse
    with open(path, encoding="utf-8") as f:
        root = parse(f.read())[0]

    def find(node, key):
        return [e for e in node if isinstance(e, list) and e and e[0] == key]

    out = {}
    routes = find(root, "routes")[0]
    for net in find(find(routes, "network_out")[0], "net"):
        name = str(net[1])
        d = out.setdefault(name, {"wires": [], "vias": []})
        for w in find(net, "wire"):
            p = find(w, "path")[0]
            nums = [float(v) for v in p[3:]]
            pts = [(nums[i] / 10000.0, -nums[i + 1] / 10000.0) for i in range(0, len(nums), 2)]
            d["wires"].append((str(p[1]), float(p[2]) / 10000.0, pts))
        for v in find(net, "via"):
            d["vias"].append((str(v[1]), float(v[2]) / 10000.0, -float(v[3]) / 10000.0))
    return out
