* rx2_blk_lo1osc.inc - 25 MHz crystal oscillator (Colpitts, S9018) with a clean output
* Nodes: vcc, osc25 (output). The output is taken across Cs25, between the crystal and ground: only the crystal's
* own current flows there, and that current is a clean sine. The base node carries 7.5 % of second harmonic.
* The DC level of osc25 comes from the follower's bias resistors in rx2_blk_lo1mul.inc.
* Parameter the deck must define: xforce (0 = real crystal, 1 = motional branch open, deck forces the current)
Rfo25 vcc vfo25 100
Cfo25 vfo25 0 100n
Ro25b1 vfo25 o25b 22k
Ro25b2 o25b 0 22k
Qo25 qo25c qo25b qo25e 0 QIF
Xqo25_x vfo25 o25b o25e qo25c qo25b qo25e SOT23X PKG={pkg}
Co25a o25b o25e 47p
Co25b o25e 0 100p
Ro25e o25e 0 470
Xq25 o25b osc25 XTAL25 FORCE={xforce}
Cs25 osc25 0 10p
Ccl osc25 cl 10n
Dcl1 cl 0 DBAV99
Dcl2 0 cl DBAV99
Cosc_x osc25 0 1p
