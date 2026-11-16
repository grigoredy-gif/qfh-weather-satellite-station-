* rx2_blk_audio.inc - audio chain: buffer, 4th-order low-pass (two Sallen-Key sections), gain stage, ADC interface
* Nodes: det (detector output: 1.27 V DC, 27 kohm source, about 10 mV peak of audio), adc (to ESP32 GPIO36), vcc
* Followers alternate PNP / NPN / PNP so the DC level steps up, down, up and nothing needs a coupling capacitor
* until the gain stage. The gain stage is AC-coupled on both sides, so its own DC drift does not reach the ADC.
* Gain stage: base at 1.45 V, emitter at 0.8 V, collector at about 1.7 V, so it has room to swing both ways at
* every corner. The rest level at the ADC pin (1.25 V) comes from the filtered audio supply va, not from the
* 3V3 pin: ripple on that pin would otherwise reach the ADC only 26 dB down.
Rfa1 vcc va 100
Cfa1 va 0 100u Rser=5m
Qu1 0 det ea1 0 QP
Rea1 va ea1 10k
R11 ea1 n11 15k
R12 n11 ub2 5.6k
C11 n11 ea2 4.7n
C12 ub2 0 1n
Qu2 va ub2 ea2 0 QN
Rea2 ea2 0 2.7k
R21 ea2 n21 15k
R22 n21 ub3 5.6k
C21 n21 ea3 4.7n
C22 ub3 0 1n
Qu3 0 ub3 ea3 0 QP
Rea3 va ea3 2.2k
Cg1 ea3 bg 1u
Rg1 va bg 27k
Rg2 bg 0 22k
Qg cg bg eg 0 QN
Rgc va cg 3k
Rge1 eg eg2 47
Rge2 eg2 0 1.5k
Cge eg2 0 100u
Cuo cg adc 1u
Rup1 va adc 82k
Rup2 adc 0 51k
Cadc adc 0 1n
