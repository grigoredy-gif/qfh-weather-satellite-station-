* rx2_blk_fe.inc - front end at 137.9 MHz: input tuned circuit R1, LNA, tuned circuits R2 and R3
* Nodes: ant (antenna connector, 50 ohm), m1in (output: R3 drives the first mixer), vcc
* Parameters the deck must define: tolLr (tolerance of the 68 nH inductors), tolC (5 % capacitors),
*   tolS (0 or 1: switches the +-0.25 pF tolerance of the small capacitors on)
* Inductors: 68 nH +-2 % 0603 wirewound (Murata LQW18AN68NG00D, LCSC C86135; Q 35 at 138 MHz assumed, 0.13 pF self-capacitance).
*
* static bleed and clamp at the connector (BAV99: two diodes to ground, one each way)
Resd ant 0 10k
Desd1 ant 0 DBAV99
Desd2 0 ant DBAV99
* R1: 50 ohm in, 50 ohm out, loaded Q about 5 (wide, about 1.2 dB loss)
Cr1a ant r1 {8.2p+strv(0.25p)*tolS}
Lr1 r1 r1g {tolv(68n,tolLr)} Rser=1.68 Cpar=0.13p
Lr1g_x r1g 0 1.5n
Cr1b r1 0 {6p+strv(0.25p)*tolS}
Cr1c r1 lb {6.8p+strv(0.25p)*tolS}
* LNA: version 1's feedback amplifier, re-biased for 3.3 V and about 10 mA; about 50 ohm in and out
Rlb1 vfl lb 1.8k
Rlb2 lb 0 1k
Ql qlc qlb qle 0 QRF
Xql_x lc lb le qlc qlb qle SOT23X PKG={pkg}
Rle1 le le2 2.2
Rle2 le2 0 33
Cle2 le2 le2a 1n Rser=0.15
Lle2_x le2a 0 0.7n
Cle3 le2 le2b 1n Rser=0.15
Lle3_x le2b 0 0.7n
Rlc vfl lc 120
Rlf lc lfb 470
Clf lfb lb 1n
Rfl vcc vfl 10
Cfl2 vfl vfla 100n Rser=0.15
Lfl_x vfla 0 0.7n
* R2 and R3: two tuned circuits coupled through the shared capacitor Cm23 (Lm23 = its own and its via's inductance)
Cr2a lc r2 {6.8p+strv(0.25p)*tolS}
Lr2 r2 r2g {tolv(68n,tolLr)} Rser=1.68 Cpar=0.13p
Lr2g_x r2g 0 1.5n
Cr2b r2 cm23 {tolv(12p,tolC)}
Cm23 cm23 cm23g {tolv(330p,tolC)}
Lm23_x cm23g 0 1n
Lr3 m1in r3g {tolv(68n,tolLr)} Rser=1.68 Cpar=0.13p
Lr3g_x r3g 0 1.5n
Cr3b m1in cm23 {tolv(18p,tolC)}
Rd3 m1in 0 2.2k
* Elements ending in _x are layout estimates (pad and trace capacitance, via inductance), not parts.
* Lr1g_x, Lr2g_x, Lr3g_x: 1.5 nH for the path from each inductor's grounded pad through its via to the ground plane.
* They pull each tuned circuit about 1.5 MHz down; the capacitor values above are chosen with them in place.
Cr1_x r1 0 {0.5p+strv(0.3p)*tolS}
Cr2_x r2 0 {0.5p+strv(0.3p)*tolS}
Cr3_x m1in 0 {0.5p+strv(0.3p)*tolS}
Cant_x ant 0 {0.7p+strv(0.3p)*tolS}
* Bypass rule at VHF: never a small and a large capacitor in parallel on the same node. With their via inductance
* (about 0.7 nH each) a 1 nF and a 100 nF form a parallel resonance near 135 MHz. The emitter of the LNA therefore
* has two equal 1 nF capacitors; supply feeds have a single 100 nF.
