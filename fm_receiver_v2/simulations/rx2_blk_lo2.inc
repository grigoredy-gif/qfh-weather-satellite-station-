* rx2_blk_lo2.inc - second local oscillator: 14.31818 MHz crystal Colpitts (one MMBT3904) with a diode clamp
* Nodes: lo2 (output, about 0.19 V peak, goes straight to the second mixer's LO bases), vcc
* Crystal: 14.31818 MHz at its 20 pF load (LCSC C34748 class), model XTAL14 in models.lib.
* The crystal sits between the base and node xs2. Two Schottky diodes clamp xs2 at about +-0.33 V, so the
* amplitude and the power in the crystal do not depend on the crystal's resistance or on the transistor.
* Cd2 and Cl2 divide that down to the level the mixer wants (more LO only leaks more into the second IF).
* Parameter the deck must define: xforce (0 = real crystal, 1 = motional branch open, deck forces the current)
Rfo vcc vfo 100
Cfo vfo 0 100n
Rob1 vfo ob 22k
Rob2 ob 0 22k
Qo vfo ob oe 0 QN
Co1 ob oe 68p
Co2 oe 0 100p
Roe oe 0 680
Xq14 ob xs2 XTAL14 FORCE={xforce}
Dcl3 xs2 0 DBAS70
Dcl4 0 xs2 DBAS70
Cd2 xs2 lo2 68p
Cl2 lo2 0 33p
Cxs2_x xs2 0 1p
