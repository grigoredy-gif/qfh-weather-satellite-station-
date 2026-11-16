* rx2_blk_if1.inc - first-IF strip at 12.9 MHz: four wide tuned circuits and two emitter-coupled pairs
* Nodes: t1 (input: collector of mixer 1 feeds tuned circuit T1), m2in (output: tuned circuit T4, feeds mixer 2), vcc, vb
* Parameters the deck must define: tolL, tolC (part tolerances for Monte-Carlo, 0 = nominal)
* Each tuned circuit: 3.3 uH +-5 % 1008 wirewound (LCSC C6364740: Q 22 at 25 MHz, SRF 110 MHz; Q 16 at 12.9 MHz assumed).
* The loading is light (10 kohm), so the loaded Q is about 7 to 10 and follows the Q of the inductor (12 to 20).
* The strip only has to reject the second image at 15.736 MHz; the bandwidth is set later, at 1.418 MHz.
* The pairs use the S9018 (QIF), not the MMBT3904: a 3904 pair adds about 10 pF to a 46 pF
* tuned circuit, and that capacitance is not well controlled (the slow-corner 3904 moved the strip 0.3 MHz low).
*
* T1 (load of mixer 1) and T2, coupled through the shared 330 pF capacitor Cm12 (bottom coupling: it gets weaker
* above resonance, which is where the second image is; a small top capacitor would favour the low side instead)
Lt1 t1 vft1 {tolv(3.3u,tolL)} Rser=16.7 Cpar=0.63p
Ct1a t1 cm12 {tolv(47p,tolC)}
Ct1b t1 cm12 {tolv(6.8p,tolC)}
Ct1_x t1 0 0.5p
Rdt1 t1 vft1 10k
Rft1 vcc vft1 100
Cft1 vft1 0 100n
Cm12 cm12 0 {tolv(330p,tolC)}
Lt2 t2 0 {tolv(3.3u,tolL)} Rser=16.7 Cpar=0.63p
Ct2a t2 cm12 {tolv(47p,tolC)}
Ct2b t2 cm12 {tolv(4.7p,tolC)}
Ct2_x t2 0 0.5p
* pair 1, tail 0.4 mA, load T3. (It was 1 mA: the strip then had so much gain between T2 and T4 that 0.1 pF of
* stray capacitance from its output back to T2, or a magnetic coupling of 0.002 between the inductors, made it
* oscillate. See rx2_p1_if1_stray_kick.cir and the layout rules in the design log.)
Cpi1 t2 bi11 1n
Rbi11 vb bi11 10k
Rbi12 vb bi12 10k
Cbi12 bi12 0 10n
Qi11 vft3 bi11 ei1 0 QIF
Qi12 t3 bi12 ei1 0 QIF
Rei1 ei1 0 1.2k
Lt3 t3 vft3 {tolv(3.3u,tolL)} Rser=16.7 Cpar=0.63p
Ct3a t3 vft3 {tolv(33p,tolC)}
Ct3b t3 vft3 {tolv(6.8p,tolC)}
Ct3_x t3 0 0.5p
Rft3 vcc vft3 100
Cft3 vft3 0 100n
* pair 2, tail 0.4 mA, load T4. The small tail limits the swing on T4 to about 0.6 V peak, which is all
* the second mixer can take at its input without its transistor saturating.
Cpi2 t3 bi21 1n
Rbi21 vb bi21 10k
Rbi22 vb bi22 10k
Cbi22 bi22 0 10n
Qi21 vft4 bi21 ei2 0 QIF
Qi22 m2in bi22 ei2 0 QIF
Rei2 ei2 0 1.2k
Lt4 m2in vft4 {tolv(3.3u,tolL)} Rser=16.7 Cpar=0.63p
Ct4a m2in vft4 {tolv(33p,tolC)}
Ct4b m2in vft4 {tolv(3p,tolC)}
Ct4_x m2in 0 0.5p
Rft4 vcc vft4 100
Cft4 vft4 0 100n
