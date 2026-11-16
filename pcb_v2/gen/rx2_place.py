"""
rx2_place.py - where every part of receiver version 2 sits on the board.

A cell is a group of parts with its own origin ("at", board millimetres, (0, 0) = top left corner, y down) and
its own angle ("rot", counter-clockwise, multiples of 90). Inside a cell a part is
    (simulation name, x, y, how it is turned)
where the last item is an angle, or "net:D" (the pad on that net points to D = N, E, S, W in the cell),
or "#pad:D" (that pad number points to D). Parts are named as in the simulation blocks (field Sim).
"""

FIDUCIALS = [(3.0, 3.0), (93.0, 6.5), (97.0, 97.0)]


def pair(q1, q2, cpi, rbi1, cbi, rbi2, re, nets, rungs, cft, rft, l_across=None):
    """Emitter-coupled pair. In the cell the signal runs from west to east, the supply filter and the load are
    to the north, the bias line is to the south. Both collectors point north; the load parts are rungs between
    the two collector lines (x = 0: supply side, x = 5.4: output side). The emitters are joined by a U-shaped
    track under the second base; its bypass capacitor sits inside the U and its bias resistor bridges the U.
    nets = (first base, second base, emitters, supply-filter node, output node); rungs = [(name, y)];
    l_across = (name, y): the inductor turned by 90 degrees across the top end of the two lines."""
    bi1, bi2, e, vft, t = nets
    parts = [(q1, 0.0, 0.0, "#3:N"), (q2, 5.4, 0.0, "#3:N"),
             (cpi, -3.2, 0.94, bi1 + ":E"), (rbi1, -2.5, 3.2, bi1 + ":N"),
             (re, 0.95, 6.0, e + ":N"), (cbi, 3.65, 2.7, bi2 + ":E"), (rbi2, 4.425, 4.95, bi2 + ":N"),
             (cft, -1.75, -3.6, vft + ":E"), (rft, -1.8, -5.5, vft + ":E")]
    parts += [(name, 2.7, y, t + ":E") for name, y in rungs]
    if l_across:
        parts.append((l_across[0], 2.7, l_across[1], t + ":S"))
    return parts


CELLS = {
    # ---- antenna connector and front end; origin = centre of the SMA jack, signal runs east along y = 0
    "fe": dict(at=(6.5, 12.5), rot=0, parts=[
        ("ant_sma", 0.0, 0.0, 0),
        ("Desd1+Desd2", 6.0, -2.3, "ant:S"),
        ("Resd", 6.0, 2.1, "ant:N"),
        ("Cr1a", 8.3, 0.0, "ant:W"),
        ("Lr1", 11.1, -2.1, "r1:S"),
        ("Cr1b", 10.0, 2.4, "r1:N"),
        ("spare_Lr1", 12.0, 2.4, "r1:N"),
        ("Cr1c", 13.7, 0.0, "r1:W"),
        ("Rlb2", 14.5, 2.35, "lb:N"),
        ("Ql", 17.3, 0.95, 0),
        ("Clf", 16.2, -2.6, "lb:W"),
        ("Rlf", 19.4, -2.6, "lfb:W"),
        ("Rlb1", 15.4, -5.0, "lb:S"),
        ("Rlc", 21.4, -5.0, "lc:S"),
        ("Cfl2", 18.4, -7.4, "vfl:S"),
        ("Rfl", 23.7, -5.8, "vfl:W"),
        ("Rle1", 16.36, 4.2, "le:N"),
        ("Cle2", 13.7, 5.025, "le2:E"),
        ("Cle3", 19.0, 5.025, "le2:W"),
        ("Rle2", 16.36, 7.2, "le2:N"),
        ("Cr2a", 21.8, 0.95, "lc:W"),
        ("Lr2", 24.4, 3.2, "r2:W"),
        ("spare_Lr2", 24.4, -1.15, "r2:S"),
        ("Cr2b", 27.1, 0.95, "r2:W"),
        ("Cm23", 29.25, 3.3, "cm23:N"),
        ("Cr3b", 31.4, 0.95, "cm23:W"),
        ("Lr3", 34.0, -1.2, "m1in:S"),
        ("Rd3", 34.0, 3.05, "m1in:N"),
        ("spare_Lr3", 36.0, 3.05, "m1in:N"),
    ]),
    # ---- mixer 1; origin = centre of Qxa. m1in comes in from the west, lo1 from the south, t1 leaves to the east
    "mix1": dict(at=(55.8, 12.3), rot=0, parts=[
        ("Qxa", 0.0, 0.0, 180),
        ("Qxb", 1.9, -3.6, 0),
        ("Qx", -7.1, 0.2, 90),
        ("Cx1", -10.4, 1.14, "bx:E"),
        ("Rbx", -9.625, 3.4, "bx:N"),
        ("Rex1", -6.15, 3.7, "ex1:N"),
        ("Rex2", -6.15, 6.7, "ex2:N"),
        ("Cex2", -3.9, 5.1, "ex2:W"),
        ("Rcxa", -3.5, 0.0, "cxa:E"),
        ("Cfx2", -4.325, 2.25, "vfx:N"),
        ("Rfx", -4.325, -2.25, "vfx:S"),
        ("Rsta", 0.94, 3.3, "bxa:N"),
        ("Clo1", 0.94, 6.3, "lo1c:N"),
        ("Rbxa", 4.6, -3.6, "vbx:N"),
        ("Cbxb", -1.55, -4.55, "bxb:E"),
        ("Rsnb", -0.9, -6.8, "bxb:S"),
        ("Csnb", -3.2, -7.625, "snb:E"),
        ("Rbxb", 2.8, -6.1, "bxb:W"),
        ("Rsx1", 5.1, -7.9, "vbx:S"),
        ("Rsx2", 6.9, -5.5, "vbx:W"),
        ("Cvbx", 7.4, -7.3, "vbx:W"),
    ]),
    # ---- first IF, tuned circuits T1 and T2 (coupled through Cm12); t1 comes in from the west along y = 0
    "if1_t12": dict(at=(67.5, 11.5), rot=0, parts=[
        ("Lt1", 1.5, -2.7, "t1:S"), ("Rdt1", 4.0, -2.7, "t1:S"), ("Cft1", 6.4, -3.7, "vft1:W"),
        ("Rft1", 1.5, -6.6, "vft1:S"),
        ("Ct1a", 0.8, 0.775, "t1:N"), ("Ct1b", 2.8, 0.775, "t1:N"), ("spare_Lt1", 4.8, 0.775, "t1:N"),
        ("Cm12", 6.8, 2.325, "cm12:N"),
        ("Ct2a", 8.8, 0.775, "t2:N"), ("Ct2b", 10.8, 0.775, "t2:N"), ("spare_Lt2", 12.8, 0.775, "t2:N"),
        ("Lt2", 11.5, -2.5, "t2:W"),
    ]),
    # ---- first IF, the two pairs: a column down the east edge (cells turned so that the signal runs south,
    #      the supply is at the east edge and the bias line on the west side)
    "if1_p1": dict(at=(86.4, 20.0), rot=270, parts=pair(
        "Qi11", "Qi12", "Cpi1", "Rbi11", "Cbi12", "Rbi12", "Rei1", ("bi11", "bi12", "ei1", "vft3", "t3"),
        [("Ct3b", -2.7), ("Ct3a", -4.3), ("spare_Lt3", -5.9), ("Lt3", -8.6)], "Cft3", "Rft3")),
    "if1_p2": dict(at=(86.4, 32.0), rot=270, parts=pair(
        "Qi21", "Qi22", "Cpi2", "Rbi21", "Cbi22", "Rbi22", "Rei2", ("bi21", "bi22", "ei2", "vft4", "m2in"),
        [("Ct4b", -2.7), ("Ct4a", -4.3), ("spare_Lt4", -5.9)], "Cft4", "Rft4", l_across=("Lt4", -8.7))),
    # ---- mixer 2 (Gilbert cell), under the end of the first-IF column; the cell is turned by 180 degrees.
    #      In the cell: switching quad in a row (y = 0), supply side to the north, signal side to the south.
    #      Everything is on the top layer except the bias feed of Rbm2:
    #      - the two t5 collectors drop south to a bus; inside this pocket sit Qm2 and its parts;
    #      - Re1 bridges the bus (emitter of Qm1 outside, node et inside), Rbsb bridges the vfm line,
    #      - lo2 runs as a ring around the supply side from Qs1's base to Qs4's base; Rfm and Rs1 bridge it.
    "mix2": dict(at=(94.0, 57.4), rot=180, parts=[
        ("Qs1", 0.0, 0.0, "#3:N"), ("Qs2", 3.6, 1.9, "#3:S"), ("Qs3", 9.2, 0.0, "#3:N"), ("Qs4", 12.8, 1.9, "#3:S"),
        ("Qm1", 1.8, 12.0, "#3:N"), ("Qm2", 11.0, 5.8, "#3:N"),
        ("Cm2", -1.4, 12.94, "bm1:E"), ("Rbm1", -0.625, 15.2, "bm1:N"),
        ("Cbsb", 6.4, 2.6, "bsb:N"), ("Cbm2", 7.4, 6.74, "bm2:E"), ("Rbm2", 8.6, 9.3, "bm2:N"),
        ("Re2", 11.95, 9.3, "e2:N"), ("Rt", 10.4, 12.0, "et:N"), ("Re1", 11.95, 14.0, "et:N"),
        ("Cfm", 2.4, -3.575, "vfm:S"), ("Rbsb", 6.4, -2.8, "bsb:S"), ("Rs2", 4.7, -5.4, "vbs:E"),
        ("Cvbs", 8.5, -5.4, "vbs:W"), ("Rbsa", 6.4, -7.7, "vbs:S"), ("Rs1", 4.4, -8.525, "vbs:S"),
        ("Rfm", 0.0, -8.525, "vfm:S"),
    ]),
    # ---- second IF: a row flowing west (cells turned by 180 degrees: supply to the south, bias to the north)
    "if2_t5": dict(at=(74.0, 55.4), rot=180, parts=[
        ("C5b", 2.7, -2.7, "t5:E"), ("C5a", 2.7, -4.3, "t5:E"), ("spare_L5", 2.7, -5.9, "t5:E"),
        ("L5", 2.7, -8.6, "t5:E"), ("Cf5", -1.75, -3.6, "vf5:E"), ("Rf5", -1.8, -5.5, "vf5:E"),
    ]),
    "if2_pa": dict(at=(62.5, 55.4), rot=180, parts=pair(
        "Qa1", "Qa2", "Cc5", "Rba1", "Cba2", "Rba2", "Rea", ("ba1", "ba2", "ea", "vfa", "t6"),
        [("C6b", -2.7), ("C6a", -4.3), ("spare_L6", -5.9)], "Cfa", "Rfa", l_across=("L6", -9.2))),
    "if2_pb": dict(at=(50.5, 55.4), rot=180, parts=pair(
        "Qb1", "Qb2", "Cc6", "Rbb1", "Cbb2", "Rbb2", "Reb", ("bb1", "bb2", "eb", "vfb", "cb"),
        [("Rcb", -2.7)], "Cfb", "Rfb")),
    "if2_pc": dict(at=(38.5, 55.4), rot=180, parts=pair(
        "Qc1", "Qc2", "Cc7", "Rbc1", "Cbc2", "Rbc2", "Rec", ("bc1", "bc2", "ec", "vfc", "c2"),
        [("Rcc", -2.7)], "Cfc", "Rfc") + [
        # charge pump and detector output, west of the pump driver (same cell, so the same turned frame)
        ("C1", 8.6, -1.5, "c2:W"), ("D1", 9.1, -4.7, "#3:S"), ("Q3", 12.8, -2.45, 0),
        ("Cvp", 12.6, -5.64, "vp:W"), ("Rp2", 10.05, -8.2, "vp:S"), ("Rp1", 6.8, -7.5, "vp:E"),
    ]),
    # ---- second local oscillator (14.318 MHz), south of mixer 2; lo2 leaves at the north side
    "lo2": dict(at=(85.5, 79.5), rot=0, parts=[
        ("Qo", 0.0, 0.0, 0), ("Co1", -2.7, 0.0, "ob:N"), ("Co2", -0.94, 3.2, "oe:N"), ("Roe", -2.9, 3.2, "oe:N"),
        ("Rob1", -0.94, -3.2, "ob:S"), ("Rob2", -5.0, -0.775, "ob:E"), ("Xq14", -4.2, -3.6, 0),
        # Cd2 bridges the supply trunk (xs2 south of it, lo2 north); Cl2 sits inside the lo2 ring of mixer 2
        ("Cd2", -1.5, -12.0, "lo2:N"), ("Cl2", -3.5, -14.5, "lo2:S"),
        ("Dcl3", -6.1, -7.8, "#3:N"), ("Dcl4", -2.6, -8.4, "#3:S"),
        ("Cfo", 3.5, 0.0, "vfo:W"), ("Rfo", 2.725, -2.3, "vfo:S"),
    ]),
    # ---- the bias reference vb, where the bias lines of the two IF strips meet
    "bias": dict(at=(65.0, 39.5), rot=0, parts=[
        ("Qref", 0.0, 0.0, 0), ("Rrefs", -0.94, 3.2, "vbr:N"), ("Rref", 3.6, 0.0, "vb:W"), ("Cref", 0.94, -3.2, "vb:S"),
    ]),
    # ---- the second reference (vbd) feeds only the pump driver, so it sits next to it
    "biasd": dict(at=(31.3, 41.0), rot=0, parts=[
        ("Qrd1", 7.5, 0.0, 0), ("Qrd2", 7.5, 3.6, 180), ("Rrefd", 3.9, 0.0, "vbd:E"), ("Crefd", 8.44, -3.2, "vbd:S"),
    ]),
    # ---- 25 MHz crystal oscillator
    "lo1osc": dict(at=(27.0, 33.0), rot=180, parts=[
        ("Qo25", 0.0, 0.0, 0), ("Co25a", -2.7, 0.0, "o25b:N"), ("Co25b", -0.94, 3.2, "o25e:N"),
        ("Ro25e", -2.9, 3.2, "o25e:N"), ("Ro25b1", -0.94, -3.2, "o25b:S"), ("Ro25b2", -5.0, -0.775, "o25b:E"),
        ("Xq25", -4.2, -3.6, 0), ("Cs25", -0.5, -5.7, "osc25:W"), ("Ccl", -3.1, -7.0, "osc25:S"),
        ("Dcl1+Dcl2", -3.1, -10.5, "cl:S"), ("Cfo25", 3.5, 0.0, "vfo25:W"), ("Rfo25", 2.725, -2.3, "vfo25:S"),
    ]),
    # ---- audio chain (board coordinates). The detector output det stays east of the gap at x = 19: Qu1, RL and
    #      CL sit beside the pump transistor. The first filter runs west, the second one north along the west
    #      side, the gain stage east again; its output cg comes back down the gap at x = 19 to Cuo.
    #      Parts that bridge a track instead of a hop to the bottom layer: R11 and Rea1 over cg, Cuo and Rup1
    #      over the supply trunk at y = 67.5, Rfa1 on the supply feeder at the west edge.
    "audio": dict(at=(0.0, 0.0), rot=0, parts=[
        ("Qu1", 21.6, 58.8, 180), ("RL", 21.9, 61.3, "det:E"), ("CL", 21.9, 63.0, "det:E"),
        ("Rea1", 19.0, 55.2, "ea1:E"), ("R11", 19.0, 53.4, "ea1:E"),
        ("R12", 15.4, 53.4, "n11:E"), ("C11", 16.7, 56.9, "n11:N"), ("C12", 12.0, 53.4, "ub2:E"),
        ("Qu2", 13.9, 56.5, 0), ("Rea2", 12.96, 59.7, "ea2:N"),
        ("R21", 10.35, 58.0, "ea2:E"), ("R22", 9.525, 55.6, "n21:S"), ("C21", 7.35, 58.0, "n21:E"),
        ("Qu3", 8.4, 51.0, "#3:S"), ("C22", 11.6, 50.06, "ub3:W"), ("Rea3", 5.2, 50.06, "ea3:E"),
        ("Cg1", 7.45, 47.5, "ea3:S"), ("Qg", 10.2, 45.7, 0), ("Rge1", 11.1, 48.2, "eg:W"),
        ("Rge2", 14.4, 48.2, "eg2:W"), ("Cge", 13.4, 45.1, "eg2:S"),
        ("Rg1", 7.45, 42.5, "bg:S"), ("Rg2", 5.6, 44.75, "bg:E"), ("Rgc", 11.14, 42.4, "cg:S"),
        ("Cfa1", 6.2, 62.2, "va:N"), ("Rfa1", 4.3, 58.5, "va:E"),
        ("Cuo", 21.0, 67.5, "cg:N"), ("Rup1", 17.8, 67.5, "va:N"),
        ("Rup2", 41.2, 74.1, "adc:N"), ("Cadc", 43.18, 74.1, "adc:N"),
    ]),
    # ---- 3.3 V regulator under the west end of the DevKitC, and the two DevKitC sockets
    "reg": dict(at=(0.0, 0.0), rot=0, parts=[
        ("devkitc_left", 48.26, 70.8, 270), ("devkitc_right", 48.26, 96.2, 270),
        ("Cin", 4.2, 74.6, "v5:N"), ("Rrs", 6.4, 74.6, "v5:N"), ("Qrl", 9.5, 76.0, 0), ("Qrp", 13.5, 76.0, 0),
        ("Rpb", 11.5, 78.6, "pe:E"), ("Cout", 16.9, 77.2, "VCC:N"), ("Qre1", 9.5, 81.1, 0), ("Qre2", 13.5, 81.1, 0),
        ("Rret", 10.6, 84.4, "ret:N"), ("Cr", 6.0, 80.9, "vref:N"), ("Rr1", 6.0, 84.4, "vref:N"),
    ]),
    # ---- multiplier to 125 MHz: follower, squarer pair, current source, tuned circuits TA and TB.
    #      Origin = centre of Qq1. Both squarer collectors point north: Lta is a rung between the two collector
    #      lines and Cfq2 sits at Qq1's collector (a longer collector lead makes the pair oscillate: rx2_m1 with
    #      8 nH in that lead). The emitters are joined by a U-shaped track; Rbq2 and Rsnq bridge it.
    "lo1mul": dict(at=(51.0, 33.2), rot=0, parts=[
        ("Qq1", 0.0, 0.0, "#3:N"), ("Qq2", 5.4, 0.0, "#3:N"),
        ("Cf1", -3.2, 0.94, "bq1:E"), ("Rbq1", -2.5, 3.2, "bq1:N"),
        ("Cbq2", 3.65, 2.7, "bq2:E"), ("Rbq2", 4.425, 4.95, "bq2:N"), ("Rsnq", 2.6, 4.95, "bq2:N"),
        ("Csnq", 2.6, 8.4, "snq:N"), ("Rqs", 0.125, 4.95, "eq:E"),
        ("Qqt", -0.7, 8.0, "#3:N"), ("Rqe", 0.25, 11.5, "eqt:N"), ("Cqt", -3.9, 8.94, "bqt:E"),
        ("Rqt", -1.65, 11.5, "bqt:N"),
        ("Cvbq", 4.425, 8.2, "vbq:N"), ("Rqb1", 7.4, 5.9, "vbq:W"), ("Rqb2", 7.4, 7.6, "vbq:W"),
        ("Cfq2", -1.75, -2.9, "vfq:E"), ("Rfq", -1.8, -4.8, "vfq:E"), ("Lta", 2.7, -2.7, "ta:E"),
        ("Cta2", 7.2, -2.7, "ta:W"), ("spare_Lta", 7.2, -4.4, "ta:W"), ("Cta", 5.4, -6.7, "ta:S"),
        ("Cmab", 7.7, -7.8, "cmab:W"), ("Ctb", 5.4, -9.9, "cmab:S"),
        ("Ctb2", 3.1, -12.4, "lo1:E"), ("Rdb", 3.1, -10.675, "lo1:E"),
        ("Ltb", 7.4, -11.7, "lo1:N"), ("spare_Ltb", 9.3, -11.7, "lo1:N"),
        ("Rf1", -6.2, 0.94, "fes:E"), ("Qf", -9.5, 0.0, "#3:N"), ("Rfe", -8.55, 3.5, "fe:N"),
        ("Rfs", -13.1, 0.94, "fbs:E"), ("Rfb1", -14.2, -1.4, "osc25:S"), ("Rfb2", -14.2, 3.2, "osc25:N"),
        ("Cfu", -11.8, -2.9, "vfu:E"), ("Rfu", -9.5, -4.2, "vfu:S"),
    ]),
}
