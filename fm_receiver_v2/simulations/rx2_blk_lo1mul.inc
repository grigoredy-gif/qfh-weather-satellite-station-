* rx2_blk_lo1mul.inc - x5 stage: follower, squarer pair and two tuned circuits at 125 MHz
* Nodes: osc25 (25 MHz sine in, about 0.5 V peak), lo1 (125 MHz out, drives the first mixer), vcc
* Parameters the deck must define: tolLr, tolC (tolerances, 0 = nominal), tolS (0 or 1: switches the +-0.25 pF
*   tolerance of the small capacitors and the spread of the strays on), voq (offset voltage between the two squarer
*   transistors, 0 nominally), pkg (1 = SOT-23 package model around the transistors, 0 = bare dice)
* Follower (S9018, about 3 mA): loads the crystal lightly and drives the squarer from a low impedance.
* Rfs, Rf1 and the snubber Rsnq + Csnq are there against UHF parasitic oscillation (base stopper, isolation, damped bypass).
* Squarer (two 2SC3356): its tail is a current source (Qqt, about 7 mA), so both transistors carry the same
* current when they are on. Both bases get the same DC through equal 680 ohm resistors, so the
* pair switches at the zero crossings of the sine and its current is a 50 % square wave (odd harmonics only).
* The output is taken from Qq2, whose base is grounded for AC: its current pulse is flat-topped.
* Rqs (47 ohm) sits between the emitter node eq and the current source. Without it the pair can oscillate near
* 1.7 GHz through the package lead inductances once the stray capacitance on eq passes about 1 pF (rx2_m1).
* Layout: keep node eq as small as possible (the two emitters and Rqs close together).
* Voq is not a part: it stands for the base-emitter mismatch of the two squarer transistors (see rx2_b4).
* TA and TB (68 nH) pick out the fifth harmonic; they are coupled through the shared 330 pF Cmab.
* Elements ending in _x are layout estimates (board stray, via inductance), not parts.
Rfu vcc vfu 22
Cfu vfu vfua 100n
Lfu_x vfua 0 0.7n
Rfb1 vfu osc25 15k
Rfb2 osc25 0 33k
Rfs osc25 fbs 100
Qf qfc qfb qfe 0 QIF
Xqf_x vfu fbs fe qfc qfb qfe SOT23X PKG={pkg}
Rfe fe 0 390
Rf1 fe fes 33
Cf1 fes bq1 10n
Rqb1 vcc vbq 2.2k
Rqb2 vbq 0 4.7k
Cvbq vbq 0 100n
Rbq1 vbq bq1 680
Rbq2 vbq bq2 680
Voq bq1 bq1o {voq}
Rsnq bq2 snq 47
Csnq snq 0 1n
Cbq2 bq2 bq2a 10n Rser=0.15
Lbq2_x bq2a 0 0.7n
Qq1 qq1c qq1b qq1e 0 QRF
Xqq1_x vfq bq1o eq qq1c qq1b qq1e SOT23X PKG={pkg}
Qq2 qq2c qq2b qq2e 0 QRF
Xqq2_x ta bq2 eq qq2c qq2b qq2e SOT23X PKG={pkg}
Qqt qqtc qqtb qqte 0 QRF
Xqqt_x eqc bqt eqt qqtc qqtb qqte SOT23X PKG={pkg}
Rqt vb bqt 100
Cqt bqt bqtg 100n
Lqt_x bqtg 0 0.7n
Rqe eqt 0 47
Rqs eq eqc 47
Ceq_x eq 0 0.5p
Lta ta vfq {tolv(68n,tolLr)} Rser=1.52 Cpar=0.13p
Cta ta cmab {tolv(18p,tolC)}
Cta2 ta 0 {6.8p+strv(0.25p)*tolS}
Cta_x ta 0 {0.5p+strv(0.3p)*tolS}
Cmab cmab cmabg {tolv(100p,tolC)}
Lmab_x cmabg 0 1n
Ltb lo1 0 {tolv(68n,tolLr)} Rser=1.52 Cpar=0.13p
Ctb lo1 cmab {tolv(15p,tolC)}
Ctb2 lo1 0 {6.8p+strv(0.25p)*tolS}
Ctb_x lo1 0 {0.5p+strv(0.3p)*tolS}
Rdb lo1 0 680
Rfq vcc vfq 22
Cfq2 vfq vfqb 100n Rser=0.15
Lfq2_x vfqb 0 0.7n
