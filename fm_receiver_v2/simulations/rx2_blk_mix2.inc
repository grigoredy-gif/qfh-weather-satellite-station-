* rx2_blk_mix2.inc - second mixer: 12.9 MHz in, 1.418 MHz out into tuned circuit T5
* Double-balanced (Gilbert cell) from six MMBT3904, so the 14.3 MHz LO cancels at the output.
*   (A single-balanced version leaked 30 mV of LO onto T5 and captured the limiter on weak signals.)
* Nodes: m2in (signal in), lo2 (14.318 MHz drive, also the DC-biased base node of Qs1 and Qs4; the oscillator block couples in through its own capacitor), t5 (output: feeds T5 of the second-IF strip), vcc, vb
* Qm1/Qm2 turn the input voltage into two opposite currents; Qs1..Qs4 swap them at the LO2 rate.
* Re1, Re2 = 100 ohm (they were 220): 4 dB more conversion gain, to make up for the gain taken out of the first-IF
* strip. This mixer sits in neither strip's feedback loop, so the gain is safe here.
Cm2 m2in bm1 1n
Rbm1 vb bm1 10k
Rbm2 vb bm2 10k
Cbm2 bm2 0 10n
Qm1 em1 bm1 e1 0 QN
Qm2 em2 bm2 e2 0 QN
Re1 e1 et 100
Re2 e2 et 100
Rt et 0 1k
* switching quad, bases at about 2.0 V
Rs1 vcc vbs 10k
Rs2 vbs 0 15k
Cvbs vbs 0 100n
Rbsa vbs lo2 10k
Rbsb vbs bsb 10k
Cbsb bsb 0 10n
Qs1 vfm lo2 em1 0 QN
Qs2 t5 bsb em1 0 QN
Qs3 vfm bsb em2 0 QN
Qs4 t5 lo2 em2 0 QN
Rfm vcc vfm 100
Cfm vfm 0 100n
