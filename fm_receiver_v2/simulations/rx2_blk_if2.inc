* rx2_blk_if2.inc - second-IF strip at 1.418 MHz: tuned circuit T5, pair A + tuned circuit T6, limiter pair B,
*                   pump-driver pair C, charge-pump detector.
* Nodes: vcc (3.3 V rail), t5 (input: collector of mixer 2 feeds this tuned circuit), det (detector output),
*        vb and vbd (the two references from rx2_blk_bias.inc)
* Parameters the deck must define: tolL, tolC (part tolerances for Monte-Carlo, 0 = nominal)
*
* T5: 100 uH (Q 30 at 1.4 MHz, 4 pF self-capacitance) with 100 pF + 4.7 pF; T6 the same with 100 pF + 6.8 pF.
* The small capacitors centre the pair on 1.418 MHz with the second mixer connected and 1 pF of board stray
* on each tuned circuit (Ct5_x, Ct6_x: layout estimates, not parts).
L5 t5 vf5 {tolv(100u,tolL)} Rser=30 Cpar=4p
C5a t5 vf5 {tolv(100p,tolC)}
C5b t5 vf5 {tolv(4.7p,tolC)}
Ct5_x t5 0 1p
Rf5 vcc vf5 100
Cf5 vf5 0 100n
* pair A, tail 0.5 mA, load T6
Cc5 t5 ba1 1n
Rba1 vb ba1 10k
Rba2 vb ba2 10k
Cba2 ba2 0 10n
Qa1 vfa ba1 ea 0 QN
Qa2 t6 ba2 ea 0 QN
Rea ea 0 1.1k
L6 t6 vfa {tolv(100u,tolL)} Rser=30 Cpar=4p
C6a t6 vfa {tolv(100p,tolC)}
C6b t6 vfa {tolv(6.8p,tolC)}
Ct6_x t6 0 1p
Rfa vcc vfa 100
Cfa vfa 0 100n
* pair B, limiter, tail 1 mA, resistive load
Cc6 t6 bb1 1n
Rbb1 vb bb1 10k
Rbb2 vb bb2 10k
Cbb2 bb2 0 10n
Qb1 vfb bb1 eb 0 QN
Qb2 cb bb2 eb 0 QN
Reb eb 0 560
Rcb vfb cb 1.8k
Rfb vcc vfb 100
Cfb vfb 0 100n
* pair C, pump driver, tail 1.6 mA: square wave of about 1.65 V at c2. Its bases hang on vbd, not on vb:
* vbd follows the two junction drops the charge pump loses, so the detector output does not drift with temperature.
* Its reference base goes to vbd through only 470 ohm, so the square-wave height does not depend on transistor gain.
Cc7 cb bc1 10n
Rbc1 vbd bc1 10k
Rbc2 vbd bc2 470
Cbc2 bc2 0 10n
Qc1 vfc bc1 ec 0 QN
Qc2 c2 bc2 ec 0 QN
Rec ec 0 390
Rcc vfc c2 1.1k
Rfc vcc vfc 47
Cfc vfc 0 100n
* charge pump: one packet of charge per cycle through Q3 into RL
Rp1 vfc vp 1.5k
Rp2 vp 0 3k
Cvp vp 0 1u
C1 c2 x 47p
D1 vp x DBAS70
Q3 det vp x 0 QP
RL det 0 27k
CL det 0 470p
