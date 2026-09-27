# Discrete FM receiver for 137.9 MHz weather-satellite signals

> This is the complete, step-by-step design log of the receiver, kept as I wrote it along the way. For the short overview, start with [README.md](README.md).

This is the receiver half of my weather-satellite project. The antenna half (a
QFH antenna with a MATLAB design toolchain) is in [`../qfh_matlab`](../qfh_matlab).

**Goal:** an analog superheterodyne receiver for the 137.9 MHz weather-satellite
band, built **entirely from discrete parts**: transistors, diodes and LC
networks, with no ICs in the signal path. The demodulated audio is in NOAA APT
format. The NOAA satellites were decommissioned in 2025, so I play recordings
back through an ADALM-Pluto. A microcontroller ADC digitizes the audio and
software decodes it into an image.

**Constraints:** a student budget (~30–45 EUR of parts). The "no ICs" rule is on
purpose, because I want to learn every stage at component level. Test gear:
miniVNA Tiny, ADALM-Pluto (signal source / spectrum check), a homemade RF probe,
and sometimes access to the university RF lab (spectrum analyzer, calibrated
FM generator, noise-figure meter).
> **Supply-rail caveat (September 2026).** Every block simulation below
> (SIM 1–11, SIM 13) was run at **5.0 V**. The hardware rail is **4.6 V**,
> because the ESP32-DevKitC feeds its 5V pin through a BAT760 Schottky. `sim12`,
> the design authority, has been re-centred for that rail (bias dividers recomputed,
> all stages back within +2.5 % of their design currents, 40.7 mA total). So
> read the block-sim numbers as topology and behaviour, not as the exact
> operating point of the built board. The real numbers are in `sim12`. Details
> are in "The supply rail" section and in `../pcb/DESIGN_LOG.md`.

## Motivation

In my first year of Electrical Engineering at the University of Twente, the
Module 4 project was to design an antenna and a transmitter PCB. I really
enjoyed that field, together with the courses that went with it: High Frequency
Electronics, and Electromagnetostatics and Electrodynamics. After the module I
wanted to go deeper than the project allowed, so I decided to design my own
antenna and my own receiver for the 137 MHz weather satellites.

I wanted to do everything analog, without any integrated circuits in the signal
path. That way I have to understand every stage at component level, instead of
letting a chip do the work for me.

The plan had to change along the way. The NOAA satellites whose analog APT
signal this receiver was designed for were switched off in 2025, and the
Meteor-M satellites that are still up send a digital signal that an analog FM
receiver cannot decode. So I test the two halves separately: the antenna with
an SDR on the Meteor-M satellites, and the receiver (once it is built) with
recorded NOAA passes played back into it through an ADALM-Pluto.

The next step is to close the loop with my own hardware on both ends. I want to
build a second QFH antenna and a transmitter, which should be easier than the
receiver, and send information between the two stations with frequency
modulation, using my own PCBs and my own antennas at both ends. That link has
to run on a frequency I'm allowed to transmit on, because 137 MHz is
receive-only for me.

## Architecture

```
antenna ──► ESD ──► BPF 137.9 ──► LNA ──► mixer ──► IF filter ──► IF amp (~75 dB)
(or Pluto            LC, image    1x BF998/  ▲        12.9 MHz         │
 + attenuator)       rejection    BFR93A     │                         ▼
                                        LO 125 MHz               limiter ──► slope
                                        (25 MHz crystal                      detector
                                         oscillator + x5                        │
                                         multiplier)                            ▼
                                                            ESP32 ADC ◄── LPF + scaling
```

## Frequency plan

| Parameter | Value | Why |
|---|---|---|
| RF input | 137.9 MHz | Meteor-M / NOAA band |
| Crystal | 25 MHz | cheap, standard |
| LO | 125 MHz (25 × 5) | low-side injection |
| **IF** | **12.9 MHz** | 137.9 − 125 |
| Image | 112.1 MHz | falls in the quiet gap between FM broadcast (<108) and airband (>118), so it is easy to filter |
| FM deviation | ±17 kHz | APT specification |
| APT subcarrier | 2400 Hz AM | image brightness = subcarrier envelope |
| ADC sampling | 44.1 kHz, decimated in software | lets a cheap 3-pole anti-alias filter work |

I picked this exact plan because of the image frequency. With a 12.9 MHz IF the
image lands at 112.1 MHz, where nothing strong transmits, so a simple
2-resonator input filter is enough to reject it.

## Stages

1. **ESD protection**: antiparallel small-signal diodes + choke. It bleeds
   static from the antenna and is invisible at signal levels.
2. **Band-pass filter 137.9 MHz**: two coupled LC resonators. It rejects FM
   broadcast, airband, and most of all the 112.1 MHz image (target ≥30 dB).
3. **LNA**: one VHF transistor (BF998 dual-gate MOSFET or BFR93A). It sets the
   noise figure of the whole receiver, ~18 dB gain. Gate 2 of a dual-gate
   device can later also be the AGC control point.
4. **Mixer**: dual-gate MOSFET (RF on G1, LO on G2). It gives conversion
   *gain* (+10…15 dB) and needs only a few hundred mV of LO. Fallback: 4-diode
   double-balanced mixer (better linearity, −6 dB loss, needs +7 dBm LO).
5. **Local oscillator**: 25 MHz crystal Colpitts oscillator, then one
   class-C stage multiplying ×5, with the output tank tuned to 125 MHz. A
   crystal + multiplier replaces a PLL synthesizer. The stability is the same
   (the crystal sets it), and there is no programmable divider, which is the
   one block that cannot be built without ICs. We only need a single fixed
   frequency, so nothing is lost.
6. **IF filter**: 2–3 coupled LC resonators at 12.9 MHz. With practical LC
   values the realistic bandwidth is 100–200 kHz, not the ideal 40 kHz (that
   would need Q≈320). This costs ~5–7 dB of sensitivity, which is fine for v1.
7. **IF amplifier**: three tuned stages, ~25 dB each. The layout (ground
   plane, shielding between stages, per-stage supply decoupling) decides
   whether this is an amplifier or an oscillator. Simulation cannot check
   that part.
8. **Limiter**: antiparallel diodes clipping the last IF stage. It removes AM
   so the detector responds to frequency only. (This is safe for APT: the
   image information is *inside* the FM modulation and appears only after
   demodulation.)
9. **Slope detector**: the FM demodulator, and the part of the project I learn
   the most from. It is a tank detuned from the carrier on purpose, so the
   signal sits on the flank of the resonance curve. Frequency deviation →
   amplitude variation → a Schottky envelope detector recovers the audio.
10. **Audio LPF + scaling**: 3-pole low-pass (~6 kHz), DC offset and level
    matching into the ADC range, buffered by an emitter follower.

## Simulation roadmap (LTspice)

I ordered the simulations by *what they unblock*, not by build order. For
example, the detector defines the IF gain requirement and the multiplier
defines the mixer drive. I trust LTspice for topology, filters and audio. I do
**not** trust it for VHF gain figures, noise figure or stability, because
layout parasitics dominate at 137 MHz. Those get checked on the bench with the
miniVNA, an RF probe and the Pluto.

| # | File | What it proves | Status |
|---|---|---|---|
| 0 | `slope_tank_test.asc` | tank resonance sanity + schematic-generation test | ✔ passed (peak −6 dB @ 12.9 MHz, Q≈62, phase zero-crossing at resonance) |
| 1a | `sim1a_slope_scurve.asc` | detector S-curve, optimum detune, linearity window | ✔ closed (rev 5): peak 520.9 mV @ 12.95 MHz, carrier at 83 % of peak |
| 1b | `sim1b_slope_demod.asc` | actual FM→audio demodulation, recovered level + THD | ✔ closed (rev 4): ~60 mVpp of 2400 Hz, in-band THD 0.78 % |
| 1c | `sim1c_debug_dc.asc` | A/B debug: modulated vs unmodulated carrier | ✔ did its job: showed the modulation was not the problem |
| 1d | `sim1d_timestep_check.asc` | solver timestep convergence ladder | ✔ 5n/2n/1n/0.5n study; 1 ns adopted as the standard step |
| 2a | `sim2a_audio_freq.asc` (audio LPF) | anti-alias shape ahead of the ADC | ✔ closed (rev 3b): passband flat to **0.70 dB**, **45.7 dB** down at 22 kHz, 171 dB down at the IF |
| 2b | `sim2b_audio_thd.asc` (levels, bias, ESP32 interface) | DC ladder, ADC drive, distortion | ✔ closed (rev 3b): **1.02 Vpp on 1.26 V** (the ADC's linear window), in-band **THD 1.6 %** (1.45 % in situ, SIM 13), pedestal disturbed by **1.3 mV** |
| 3 | `sim3_if_filter.asc` (IF filter) | achievable bandwidth and shape at 12.9 MHz | ✔ closed: **200.5 kHz** at critical coupling (hand calculation said 201), −27.9 dB at ±500 kHz, −39.9 dB at ±1 MHz |
| 4a | `sim4a_if_gain.asc` (IF amplifier chain) | gain, bandwidth, stability margin | ✔ closed (rev 3: **four** cascode stages, **5 V**): **95.8 dB**, 164 kHz, peak exactly 12.9 MHz, stages within 1.2 dB |
| 4b | `sim4b_if_limiting.asc` (chain + limiter) | does the output stop following the input? | ✔ closed (rev 3): **+20 dB in → +1.6 dB out**, 2.51 Vpp delivered, limiting from ~22 µV |
| 5 | `sim5_multiplier_x5.asc` (×5 multiplier) | 5th-harmonic level, rejection of ×4/×6 | ✔ closed (rev 4, **5 V**): topology validated (magnetic coupling, H4 −36.7 dB, H6 −42.1 dB); absolute H5 figure superseded by the settled SIM 5b curve |
| 5b | `sim5b_multiplier_drive.asc` (multiplier drive robustness) | settled H5 vs realistic (330 Ω) drive | ✔ closed (rev 3, **5 V**): cliff unmoved, nominal H5 **1.68 V**, −20 % corner 1.02 V = 3.4× the mixer's need, **no saturation** (collector min 3.33 V) |
| 6 | `sim6_xtal_oscillator.asc` (25 MHz crystal oscillator) | startup, amplitude limiting, frequency | ✔ closed (rev 2, **5 V**): starts from the `.ic` kick, limits at **409.7 mVpp** (bit-stable between spaced windows), 25 MHz dominant |
| 6b | `sim6b_osc_buffer.asc` (oscillator buffer/driver) | drive for the multiplier, crystal isolation | ✔ closed (rev 3, **5 V**): **2.33 Vpp** into the replica load, cliff margin intact, no added clipping, oscillator untouched |
| 7 | `sim7_input_bpf.asc` (input BPF) | image rejection at 112.1 MHz | ✔ closed: **37.6 dB** image rejection, 6 MHz passband, 2.2 dB insertion loss, 50 Ω/50 Ω so it is miniVNA-measurable. **Rev 2 (Sept 2026):** tap caps 15p/100p → **8.2p/56p** (same 0.128 ratio; trimmer ~8.7 pF in the ideal netlist, ~6.5 pF on the board): 39.5 dB image rejection, 6.1 MHz passband, 2.4 dB insertion loss, so within 0.2 dB / 0.1 MHz of the rev 1 curve |
| 8 | `sim8_mixer.asc` (mixer) | conversion gain, LO drive plateau, image response | ✔ closed (rev 2, **5 V**): **22.8 dB** conversion gain, flat for LO ≥ 0.4 V, image converts within 0.04 dB of the wanted signal |
| 9 | `sim9_lna.asc` (LNA) | 50 Ω match and gain ahead of the mixer | ✔ closed (rev 2, **5 V**): **S21 15.8 dB**, Zin 38 Ω (VSWR 1.31), flat and monotonic to 1 GHz |
| 10 | `sim10_limiter_detector.asc` (integration: limiter → detector) | does the S-curve survive the real 100k/clamp source? | ✔ closed: **peak still exactly 12.95 MHz** with a physical 33k coupling resistor, so the C1 alignment target survives; carrier lands on a 1.96 mV/kHz linear flank |
| 11 | `sim11_mixer_filter_if.asc` (integration: mixer → IF filter → first IF stage) | interface gain, in-situ selectivity, tap sizing | ✔ closed: **+20.6 dB** measured to the first IF base (4 dB above the composed paper figure), −29.6 dB at ±500 kHz, tap re-sized 20 % → **13/27**, all biases untouched |
| 12 | `sim12_full_receiver.asc` (**the full receiver**) | one master schematic, every bias network on one rail (5.0 V originally; **4.6 V since Sept 2026**, dividers re-centred) | ✔ closed: `.op` verified, every node matches its block sim (cascode mid-nodes to **6 digits**), total draw **40.7 mA / 187 mW at 4.6 V** (41.6 mA / 208 mW at the original 5.0 V) |
| 13 | `sim13_fm_endtoend.asc` (**FM in, audio out**) | a true APT FM signal through IF chain → limiter → detector → audio → ADC | ✔ closed: **20 dB of input change → 0.5 dB at the detector**, 2400 Hz at the ADC; found the signal-acquisition transient and a 2× audio overdrive (fixed in SIM 2 rev 3b; Sept 2026: RE4A 150 → **270 Ω** for headroom on the real 4.6 V rail, giving THD **1.1 / 1.8 %** and **0.45 Vpp** at the ADC) |

## SIM 1 — slope detector

**Design math (final values, rev 5).** Tank: L = 2.2 µH, **C1 = 66.7 pF**.
The detector diode really adds **~1.9 pF** on top (its junction capacitance,
seen through the envelope cap acting as RF ground), so the tank lands at
**f₀ = 12.95 MHz**. That is ~55 kHz *above* the 12.9 MHz carrier on purpose:
it is the maximum-slope point of the flank for the measured loaded
**Q ≈ 80** (optimum detune = f₀/(2√2·Q)). Z₀ = √(L/C) ≈ 179 Ω. The measured
slope is ≈ 1.7 µV/Hz at the detector output with 1 V drive, so the ±17 kHz
APT deviation gives ~60 mVpp of recovered 2400 Hz audio on a ~0.23 V DC
pedestal.

Envelope detector: 1N5711-class Schottky (low junction capacitance, ~2 pF;
model included inline as `DSCH`), R = 220 kΩ, C = 47 pF → τ = 10.3 µs. That is
≫ the 77 ns carrier period (ripple ~2 mVpp) and ≪ 35 µs, so it tracks the
4.4 kHz envelope without diagonal clipping (worst-case required slew 0.7 V/ms
vs ~19 V/ms available).

**What the first run caught (why rev 2 exists).** The very first S-curve came
out monotonically falling instead of peaking at 12.95 MHz. The tank resonance
had been pushed ~200 kHz low. The cause: the detector diode's junction
capacitance (~2.2 pF) sits directly on the tank node. Behind the diode, the
envelope capacitor is almost a short at 12.9 MHz, so the tank sees the full
Cj. The fix is the same as on a real bench: **tune the tank with the detector
connected**. Here that means C1 goes 68.7 pF → 66.5 pF. Rev 2 also steps a
second measurement (`Vtank`, the true tank amplitude) next to `Vdet`, so tank
problems and detector-efficiency problems cannot be mixed up again. CE also
went 22 pF → 47 pF to cut the carrier ripple ~4×. This is exactly what the
simulation is *for*. Making this mistake on copper would have cost me an
evening of confused trimming.

**What the timestep study caught (why rev 4/5 exist).** The rev-2/3 runs used
a maxstep of 5 ns, close to the LTspice default (~15 points per 12.9 MHz
carrier cycle). The numbers looked fine but were wrong: 412 mV on the tank
where the converged answer is ~200 mV. They even agreed perfectly with the
simple R_in = R/2 textbook model, because both made the same optimistic
error. A convergence ladder (5n → 2n → 1n → 0.5n gave 412/224/204/199 mV)
settled on **maxstep = 1 ns** as the standard step. The diode current shows
why it needs such a small step: ~24 µA RMS of *displacement* current flows
through its nonlinear junction capacitance, against only ~0.3 µA of average
rectified current. At 12.9 MHz this diode is first a ~2 pF nonlinear
capacitor and only second a rectifier. I took two rules from this. First,
**never trim a design against an unconverged simulation**. An early
"measured 3.3 pF" diode contribution was a timestep artifact, and it sent one
whole retune iteration the wrong way. Second, **`.options plotwinsize=0` in
every measurement deck**, because LTspice's lossy waveform compression clips
`.meas` results on RF nodes without any warning.

**Final results (converged, rev 5):** S-curve peak **520.9 mV at
12.95 MHz** (transfer 0.52 from a 1 V source through 33 kΩ; at full drive the
detector loads the tank only lightly). The carrier sits at 83 % of peak on the
straight part of the flank. Recovered audio is **~60 mVpp** of 2400 Hz, with
**in-band THD 0.78 %**. The early detuned runs gave 4.7 %, which shows
directly why the carrier must sit on the linear part of the slope. The
requirement this hands to the IF chain (SIM 4): the limiter must deliver
**≥ 1 V amplitude** into the detector tank.

**Pass criteria**

| Criterion | Target |
|---|---|
| S-curve linear window | ±17 kHz around 12.9 MHz within ~±10% of a straight line |
| Recovered 2400 Hz | ≥ 50 mVpp |
| THD @ 2400 Hz | < 5 % **in-band**. Read LTspice's *Partial* THD figure. The *Total* figure also counts the residual 12.9 MHz ripple (first run: partial 4.5 %, total 257 %!), which the stage-10 audio LPF removes anyway |

**How to run**

- `sim1a`: Run, then *View → SPICE Error Log → right-click → Plot .step'ed
  .meas data*. This plots detected DC (`Vdet`) vs carrier frequency, which is
  the S-curve.
- `sim1b`: Run, plot `V(audio)`. You should see a 2400 Hz sine on a DC
  pedestal. THD is at the bottom of the SPICE Error Log.

## SIM 2 — audio filter and ADC scaling

**What this block is for.** The detector hands over ~60 mVpp of 2400 Hz on a
0.23 V pedestal, behind ~150 kΩ. That is the APT subcarrier, and *its
amplitude is the picture*. The ESP32 samples this audio at 44.1 kHz and
software turns the envelope into pixels. So the block has two jobs:
anti-alias filtering before that sampler, and enough gain to use the ADC's
range.

**Why active filtering.** APT occupies 320–4480 Hz (2400 Hz subcarrier ±
the 2080 Hz pixel rate) and Nyquist for 44.1 kHz is 22 kHz. Three cascaded
passive RC poles reach only ~20 dB there. Two Sallen-Key sections give a
4th-order Butterworth: **45 dB at 22 kHz** with 0.63 dB of passband ripple,
for two transistors.

**Why a Darlington, and why PNP.** The detector's 150 kΩ source impedance is
very high. A single transistor's base current through it would shift the
detector's own operating point by ~0.3 V. That moves the carrier off the
straight part of the slope and ruins SIM 1's linearity, three blocks upstream
of where the symptom would show up. Measured pedestal shift with the
Darlington: **1.7 mV**. PNP because the chain is DC-coupled end to end. A PNP
follower shifts the level *up* by one V_BE and an NPN shifts it *down*.
Alternating them keeps every stage biased inside one 5 V rail, with no
coupling capacitors and no negative supply.

**A bias subtlety.** The first hand calculation assumed 0.70 V per junction
and predicted 0.23 → 1.63 → 0.93 → 1.63 V. That was wrong, because
V_BE = V_T·ln(I_C/I_S) and **the first Darlington transistor carries only the
second one's base current**. That is about 2 µA, which gives V_BE ≈ 0.50 V
instead of 0.64 V at 0.46 mA. So the Darlington shift is +1.13 V, not +1.30 V.
Measured ladder: **0.232 → 1.364 → 0.744 → 1.412 V**, which matches the
corrected prediction to a few millivolts.

**Results:**

| | measured | target |
|---|---|---|
| passband ripple 400–4400 Hz | 0.63 dB | < 1 dB |
| rejection at 22 kHz | 45.3 dB | ≥ 30 dB |
| rejection at 12.9 MHz | 172.6 dB | — |
| output | 1.51 Vpp on 1.643 V | 1.3–1.8 Vpp at 1.65 V |
| in-band THD at 2400 Hz | 3.77 % | < 5 % |

The first run came out with 1.63 dB of passband tilt and 54 dB of rejection.
So I moved the corner from 5.4 to 6.6 kHz (C1/C2/C3/C4 → 2.7n/2.2n/8.2n/1.2n,
all E12), **trading 9 dB of surplus rejection for 1 dB of flatness**. This was
worth it. The tilt weakens the subcarrier's upper sideband compared to the
lower one, which softens the finest picture detail, and 45 dB at Nyquist is
still far more than the sampler needs.

The distortion is mostly second harmonic (H2 3.76 %, H3 0.21 %, rest below
0.005 %). It is asymmetric, which is the typical sign of r_e modulation in the
common-emitter gain stage, the same source the design notes named. `RE4B` was
set to 2.7 kΩ instead of 3.3 kΩ after a review that ran the circuit. It
centres the collector at 3.23 V instead of 3.69 V on the 6 V rail and drops
THD from 4.66 % to 3.77 % at no cost.

**Without the gain stage the ADC would see 60 mV out of 3.3 V, which is about
six effective bits.** With it, 1.5 Vpp: half the range, with headroom for a
stronger pass.

### SIM 2 rev 3 — the ESP32 module interface

The receiver feeds an **ESP32 development module**, not a bare chip. It has USB
power and a programming port, it is easy to buy, and it also works as the
debug console during alignment. That choice affects the audio chain in three
ways.

**The ADC cannot be driven by a 23.5 kΩ divider.** The ESP32's SAR ADC wants a
source below ~10 kΩ. With the old 47k/47k and CADC 470 pF, the pin charged
with τ = 11 µs against a 22.7 µs sample period. That is only two time
constants, so there is a sample-dependent error that lands directly on
picture brightness. Also, the old 1.5 Vpp on a 1.65 V pedestal peaked at
2.4 V, right against the ESP32 ADC's nonlinear region above ~2.45 V. New
divider **10 kΩ / 6.2 kΩ**: pedestal 1.26 V, swing inside 0.5–2.0 V (the
linear part), source impedance 3.8 kΩ. As a side effect, supply rejection at
the ADC improved from 70 % to 28 %. `CADC` 470 pF → 2.2 nF gives the SAR a
real charge reservoir.

**The module's 5 V pin is USB VBUS.** It carries laptop switching noise plus
the ESP32's own 250–500 mA WiFi bursts through the cable resistance: tens to
hundreds of mV, with content in the audio band. This topology has poor supply
rejection (ripple reaches the gain stage's collector straight through `RC4`),
so it now has its own rail: **RSUP 100 Ω + CSUP 100 µF**. That is a 16 Hz
corner, giving −43 dB at 2400 Hz for 0.14 V of drop at the 1.4 mA this chain
draws. On the board, put 100 nF in parallel with CSUP, and keep WiFi off
during a pass: record first, transmit afterwards.

**Rev 3b: the operating point, after the rev 3 run measured 7.5 % THD.**
The numbers show what happened. With 120 mVpp in and r_e = 86 Ω against 150 Ω
of degeneration, v_BE swung ±22 mV against a 25.8 mV V_T. The emitter current
was modulated ±85 %, so r_e itself swung between 47 and 577 Ω. H2 at 7.46 %
against H3 at 0.78 % confirmed r_e modulation rather than clipping. It helps
to look at what that actually costs. **The picture lives in the *envelope* of
the 2400 Hz subcarrier**, and H2 at 4800 Hz is outside the envelope band. So
the metric that matters is gain compression: 10.17 small-signal against 9.83
large-signal, 3.3 % at full white, which the APT calibration wedge corrects
anyway. That was usable, but the operating point had become tight (V_CE fell
to 0.46 V on negative peaks). So I changed two resistors to get both margin
and linearity: **RC4 10 kΩ → 3.3 kΩ and RE4B 2.7 kΩ → 820 Ω**. Stage current
rises 0.30 → 0.85 mA, r_e falls 86 → 30 Ω, the v_BE swing halves to 0.4 V_T,
and **in-band THD drops to 1.4–1.6 %** (1.45 % in situ in SIM 13, 1.58 %
standalone). That is five to six times better.

**A measurement mistake from the same run.** The output landed at 0.75 Vpp
when the arithmetic said 1.17. The gap was a *reading* error, not a circuit
error. The detector's 124 mVpp includes the residual 12.9 MHz carrier ripple
(the thick band you can see on the plot). The true 2400 Hz content is
~89 mVpp, and the audio chain then delivers exactly its designed 8.5×. So
always separate the wanted spectral line from the raw peak-to-peak. The
`.four` fundamental is the number to trust.

And 0.75 Vpp is the right level, not too little. Against a 3.3 V full scale it
is **931 ADC counts**, and APT needs only 64–256 grey levels. Giving up half
the amplitude for six times the linearity is the right trade when the
amplitude *is* the picture.

### SIM 2 rev 2 — back to 5 V

A bit ironic: the original `.cir` decks *were* 5 V. The `.asc` conversion
took 6 V from the rest of the receiver, and now the rail is back. Only V2
changes. The DC-coupled ladder is anchored to the detector's pedestal through
junction drops and never sees the rail. One thing I kept on purpose: **RE4B
stays 2.7 kΩ** instead of going back to the `.cir`'s 3.3 kΩ. The THD is
dominated by r_e modulation and falls with bias current, and Q4 still has
1.3 V of room downwards for a 0.76 V swing. Measured on 5 V: ladder
0.231 → 1.351 → 0.731 → 1.386 V (each 12–26 mV below the 6 V run, only
because of the smaller V_BE at the follower currents), pedestal shift down to
**1.3 mV**, Q4 collector at 2.313 V, output **1.48 Vpp on 1.643 V** (the 1.643
comes from the ESP32's 3.3 V rail and does not depend on VCC), ripple
0.69 dB, 45.6 dB at 22 kHz, in-band **THD 3.89 %** (H2 3.88, H3 0.21). That is
0.12 points more than at 6 V, which supports the RE4B choice.

## SIM 3 — the IF filter

**Circuit.** Two identical tanks (2.2 µH ∥ 69.2 pF, Z₀ = 178 Ω) at 12.9 MHz,
joined **only** by mutual inductance. There is no galvanic path at all, for
the reason SIM 5 taught me. Each tank is loaded to Q ≈ 91 by 33 kΩ. On tank 1
that is the mixer drain's own output resistance. On tank 2 it is the first IF
stage **tapped down**: a 2N3904-class base at 2 mA is only ~1.3 kΩ, so it
connects at ~20 % of the turns and 1.3 k/0.2² = 33 kΩ appears across the
tank. Coil Q_unloaded ≈ 178, modelled as Rser = 1 Ω. *(The 20 % tap figure
was replaced later, at integration. SIM 11 measured the real cascode input
at ~6.1 kΩ and re-sized the build tap to **13/27**. The 33 kΩ loading this
file assumes is still valid.)*

**Why so wide.** APT occupies ~43 kHz (Carson), but I made the passband
~200 kHz on purpose. It has to cover the Doppler that is in the recording
(±3.5 kHz), crystal tolerance and alignment error, and a slope detector needs
the whole FM spectrum undistorted. The filter's real jobs here are to limit
the noise bandwidth ahead of 75 dB of IF gain, and to keep that gain in-band
so the chain stays stable.

**Results (k stepped through all three coupling regimes):**

| k | regime | BW (−3 dB) | peak | tank 1 vs output |
|---|---|---|---|---|
| 0.005 | undercoupled | 114.5 kHz | −14.67 dB | −7.8 / −14.7 dB |
| **0.011** | **critical** | **200.5 kHz** | **−12.20 dB** | **−12.196 / −12.197 dB** |
| 0.022 | overcoupled | 373.4 kHz | −12.12 dB (2 dB dip) | −20.1 / −14.1 dB |

Two theory checks came out exact. **Bandwidth**: √2·f₀/Q predicted 201 kHz,
and the simulation gave 200.5. **Insertion loss**: (1 − Q_L/Q_U)² predicted
6.2 dB above the 6 dB a lossless matched network would show, and the measured
value was 6.2 dB. Also, at critical coupling the two tanks carry **identical
amplitude** (−12.196 vs −12.197 dB). That is the physical sign of maximum
power transfer, and here it shows up directly in the numbers. Skirts:
−27.9 dB at ±500 kHz, −39.9 dB at ±1 MHz, symmetric to 0.03 dB.

**Bench recipe.** With N = 27 turns, a link of n turns gives k ≈ (n/N)², so
**2 / 3 / 4 turns land almost exactly on the three curves above**. Wind
3 turns for critical coupling, and remove one if the response comes out
double-humped. So the simulation also gave me the winding instructions.

## SIM 4 — the IF amplifier and limiter

**What it has to deliver.** SIM 1 set the requirement: **≥ 1 V into the
detector tank**. Three tuned stages at 12.9 MHz, then a diode limiter.

**Rev 1 looked fine, but it was not.** Three single-transistor common-emitter
stages gave 87 dB at 12.9 MHz, but three measurements showed the problem:

- the base voltage rose **above** the source voltage (+10 dB). No passive
  network can do that, so energy was coming back from the collector.
- the −3 dB bandwidth collapsed to **51 kHz** against a natural ~200 kHz.
  Aligning tanks that are already close cannot narrow a response. Only
  Q-multiplication can do that. Factor 4 → feedback loop gain ≈ 0.75.
- changing one capacitor by 1.5 % moved the bandwidth by 2.5×.

So this was an amplifier three quarters of the way to oscillation, even in a
simulation with no board capacitance and no coil-to-coil coupling. The
real board would have added the rest. The cause was Miller feedback through
the 0.7 pF base-collector capacitance, multiplied by the ~33× gain at the
collector.

**Rev 2: cascode.** Each stage became two transistors. The lower one
(common emitter) drives the **emitter** of the upper one (common base), which
is an impedance of only 1/gm ≈ 26 Ω. So the lower collector barely moves. Its
voltage gain is ~1 instead of ~33, and its Miller capacitance is 1.4 pF
instead of 23 pF. The upper transistor has the voltage gain, but its base is
grounded for signal, so its own feedback capacitance lands on a bypassed bias
node instead of the input.

A **BF998 dual-gate MOSFET is exactly this**: two devices stacked in one
package, with gate 2 as the upper base. So the topology maps straight onto
that part if I prefer it on the board. Here I built it on purpose from the
transistors already in the BOM and the **same `QRF` model used everywhere
else in this project**. That way the improvement comes from the topology, not
from a hand-written model with a too-good number in it.

**Results (rev 2):**

| | rev 1 | rev 2 (cascode) |
|---|---|---|
| base voltage vs source | +4.1 dB | **−1.2 dB** |
| −3 dB bandwidth | 51 kHz | **236 kHz** |
| gain | 79.8 dB (inflated by regeneration) | **70.5 dB real** |
| gain per stage | 21.3 / 22.0 / 32.4 dB | **23.1 / 23.1 / 24.6 dB** |

The per-stage spread going from 12 dB to 1.5 dB is the clearest sign. The
stages now work independently instead of pulling on each other.

**Limiting (SIM 4b).** Input stepped over 54 dB:

| input | output |
|---|---|
| 20 µV | 0.121 Vpp |
| 100 µV | 0.604 Vpp |
| 1 mV | 2.267 Vpp |
| 10 mV | **2.502 Vpp** |

**+20 dB of input produces +0.86 dB of output.** That is the limiter doing its
job. It lets the slope detector convert frequency only, so fading and AM noise
are thrown away instead of ending up in the picture. Output 2.50 Vpp = 1.25 V
amplitude, against SIM 1's ≥ 1 V requirement. Limiting starts around 0.4 mV
at the chain input.

The same run showed three more things. The cascode mid-node sits at 1.721 V
and moves **2 mV** across the whole 54 dB input range, so the cascode is
holding. Stage 1's tank voltage scales perfectly linearly ×5, ×10, ×10, so
limiting happens only at the end of the chain, where it should. And stage 3's
emitter DC rises 0.49 → 0.75 V at maximum overdrive. It really rectifies
there, which is what hard limiting looks like. That is harmless because the
diodes define the output, but it matters for recovery behaviour.

**Bench notes.** Every tank is the same 27-turn T37-6 toroid as SIM 3, tapped
at 13 turns, tuned with 56 pF plus a 5–30 pF trimmer. The **four** upper bases
share one 8.2k/10k divider (2.56 V, bypassed), which is one track on the board
(the 22k/18k figure from rev 2 is out of date; see the rev 3 section). And the
input **must** be AC-coupled. A rev-1 bug had the 1 kΩ source resistance in
parallel with the base divider. That dropped the bias to 0.12 V and cut stage
1 off completely. A dead transistor still passes signal through its
base-collector capacitance, so it showed up as −19 dB of "gain" instead of as
an obvious failure.

As always, none of this predicts stability on copper. What it does show is
that the design no longer starts from a position 75 % of the way to
oscillation.

## SIM 5 — ×5 frequency multiplier (the LO chain)

**Final circuit (rev 3).** One transistor (generic UHF NPN, BFR93A-class,
inline model `QRF`) driven by 1 V of 25 MHz through a coupling cap. There is
no DC base bias. The RC input network self-biases the stage into class C, so
the collector current flows in narrow ~25 mA pulses that are rich in
harmonics. The collector tank (150 nH ∥ 10.8 pF, Q≈19) selects 125 MHz, and a
**second, magnetically coupled tank** (`K1 L1 L2 0.03`, near-critical
coupling, Q≈58) cleans it up. On the bench that is a link winding / two
adjacent coils, just like an old IF transformer. VCC is now 5 V (rev 4). It
was originally 6 V, chosen to keep the collector swing inside a real BFR93A's
ratings. The supply-rail section below tells that story in full.

**Final results:** H5 (125 MHz) = **4.65 V** into the 6.8 kΩ-loaded output
tank (the mixer gate needs only ~0.3 V, so a simple tap is enough). Spurious
harmonics: H4 (100 MHz) **−36.9 dB**, H6 (150 MHz) **−42.4 dB**. Supply
current ~2.1 mA average. This validates the frequency plan (25 MHz crystal
× 5). The crystal oscillator (SIM 6) now gets the requirement to deliver
**~1 V amplitude at 25 MHz**.

**Two things I learned from the revisions:**

1. *Capacitive top-coupling has a trap.* Rev 2 coupled the two tanks with a
   series 1.5 pF cap, and H4 barely improved. Below resonance the second
   tank looks inductive, and together with the coupling cap it forms a
   spurious **series resonance** (~117 MHz here). That peaks the transfer
   exactly where I needed rejection. Transformer (mutual-inductance)
   coupling has no such path: H4 improved by 18.6 dB as soon as the
   coupling became magnetic.
2. *Spur targets come from the system, not from symmetry.* H6 is the spur
   that matters. A 150 MHz LO line converts **137.1 MHz straight onto the
   12.9 MHz IF**, inside the front BPF's passband, so it needs ~40 dB from
   the LO chain alone (got 42.4). H4 converts 112.9 MHz, which the front
   BPF already rejects by ≥30 dB. So its total protection is ~67 dB, even
   though the LO-only number (36.9 dB) misses the paper target of 40. I
   accepted that on system-level grounds and wrote it down here instead of
   iterating it away.

**Post-script (from SIM 5b).** The 4.65 V H5 figure above was measured 2 µs
into the run, halfway through the self-bias charge (τ = CC·RB ≈ 10 µs), and
from an ideal 0 Ω source. Both make the result look better than it is. The
settled numbers with realistic drive are in SIM 5b below. The topology
conclusions (magnetic coupling, spur structure) do not change, and the spur
ratios are confirmed again there.

**Rev 4: 5 V.** There is no divider to recompute (the stage self-biases), so
V2 is the only electrical change. I did add a new measurement, because the
rail change moves *both* headroom edges. The flywheel top peak moves 1 V
further from the 12 V V_CEO, which is good. But the swing **minimum** moves
1 V closer to saturation, and a saturating class-C collector clips the tank
and changes the same harmonics H5 depends on. Measured: collector minimum
**0.96 V** even in this file's hard-driven ideal-source case, spurs unchanged
(H4 −36.7 dB, H6 −42.1 dB). The saturation worry came from the old 9.3 Vpp
swing figure, which was an unsettled, ideal-source number. The settled
realistic swing (SIM 5b) is 3.6 Vpp with a 3.3 V floor.

## SIM 5b — multiplier drive robustness

**Question.** SIM 5 characterized the multiplier from an ideal source at
exactly 1 V. The real driver is the SIM 6b buffer: **270 Ω output impedance,
1.9 Vpp nominal, ±20 % tolerance**. A class-C base is a difficult load. It
draws current only in narrow pulses at the positive peaks, and every pulse
through 270 Ω pulls the peak down exactly when it matters. So the question is
how H5 behaves with this real driver.

**Artifact caught first: the unsettled measurement window.** Rev 1 (4 µs run)
showed the LO still drifting 10–12 % between two measurement windows. The
input self-bias network settles with **τ = CC·RB = 10 µs**, so rev 1 *and
SIM 5 itself* had been measured in the middle of the transient. This gave a
new rule next to the timestep one: **the slowest bias loop sets the
measurement window, so prove settling with two spaced windows** (rev 2,
40 µs = 4τ: windows agree ≤1.5 %).

**The settled curve (rev 2):**

| Source ampl. | Drive at base (sagged) | H5 @ 125 MHz | Ic peak |
|---|---|---|---|
| 0.65 V | 1.26 Vpp | 0.007 V | 0.04 mA |
| 0.75 V | 1.44 Vpp | 0.16 V | 0.9 mA |
| 0.95 V (nominal) | 1.76 Vpp | 1.18 V | 8.2 mA |
| 1.15 V | 2.12 Vpp | 1.95 V | 16.4 mA |

**Finding: a conduction cliff.** The resistive sag itself is small (4–8 %).
The danger is the threshold. Self-bias keeps the base right at the edge of
conduction, so below ~1.6 Vpp of drive the collector pulses collapse
(Ic peak: 16 mA → 0.04 mA across the table). The nominal operating point sits
on the steep part: **−18 % drive costs 7× of LO.** Spurs at the settled
points stay fine: H6 (the critical one) −44/−45 dB, H4 −33/−34 dB
(covered at system level by the front BPF).

**Derived requirement (the fix, read straight off the curve).** The mixer
needs only ~0.3 V of LO. So I move the operating point one step up: the
buffer must deliver **~2.1–2.2 Vpp at the multiplier base**. Then nominal
H5 ≈ 2 V, and the −20 % corner lands exactly on the already-measured 1.76 Vpp
point: H5 = 1.18 V, still **4× the mixer's need**. This sim does not need a
re-run, because the curve already contains the new operating point and its
tolerance corner. The buffer revision implements it (SIM 6b rev 2).

### SIM 5b rev 3 — the same curve on 5 V

There is no divider to recompute (the stage self-biases), so V2 is the only
electrical change. I also changed **RSRC 270 → 330 Ω** (the rev-2 buffer's
actual collector resistor; the 270 value was out of date) and added a new
`Vt1min` measurement that watches the minimum of the collector swing for
saturation. The settled curve on 5 V:

| Source ampl. | Drive (sagged) | H5 @ 125 MHz | Collector min | H5 was (6 V) |
|---|---|---|---|---|
| 0.65 V | 1.25 Vpp | 0.006 V | 4.99 V | 0.007 V |
| 0.75 V | 1.43 Vpp | 0.13 V | 4.88 V | 0.16 V |
| 0.95 V (−20 % corner) | 1.74 Vpp | **1.02 V** | 4.03 V | 1.18 V |
| 1.15 V (nominal) | 2.11 Vpp | **1.68 V** | 3.33 V | 1.95 V |

This table answers three questions. **The cliff has not moved**: self-bias
tracks the drive, not the rail, and the collapse still sits between 1.43 and
1.74 Vpp of sagged drive. **No saturation**: the collector floor stays at
3.33 V at nominal. The worry before the run came from the unsettled
ideal-source 9.3 Vpp figure, so the spaced-windows rule helped again. **The
real price of 5 V is 14 % of H5** (1.95 → 1.68 V at the same drive). C_cb
grows at the lower V_CB and loads the tank, and the current pulses shrink a
little (16.4 → 15.2 mA peak). That is not a problem. The −20 % corner still
delivers **1.02 V against the mixer's 0.3 V need (3.4×, was 4×)**, well above
the mixer's measured 0.4 V plateau threshold. Spurs at nominal: H6
**−45.1 dB**, H4 −32.5 dB, so unchanged. Settling is proven: spaced windows
agree within 1.3 % on every step. The almost identical sagged-drive values
also show that the 330 Ω source costs almost nothing. The class-C base pulses
dominate the sag, not the resistor.

## SIM 6 — 25 MHz crystal oscillator

**Circuit.** Common-collector Colpitts, one transistor (`QRF`, the same
BFR93A-class inline model as SIM 5). The crystal is drawn as its **equivalent
circuit** instead of a library symbol, so the physics stays visible on the
schematic: motional arm L = 2.0265 mH, C = 20 fF, R = 15 Ω (series-resonant at
exactly 25.000 MHz, Q ≈ 21 000) plus 5 pF holder capacitance. The very large L
and very small C are the reason quartz works as a frequency standard.
Feedback goes through an 82 pF / 180 pF capacitive divider around the emitter
follower. Bias 11 kΩ/10 kΩ from 5 V, RE = 560 Ω (Ie ≈ 2.8 mA). Output taken
at the emitter.

**Simulating an oscillator has two quirks**, both documented in the .asc:

1. *Startup.* A simulator has no thermal noise, so an oscillator sim can sit
   at its DC operating point forever, stable and not oscillating at all.
   The `.ic V(b)=0` line pulls the base at t = 0 as a starting kick.
2. *Patience.* The envelope grows with a time constant set by the crystal's
   very high Q. Visible RF only appears after ~100 µs, and limiting takes a
   few hundred µs more. The run takes minutes. That is the crystal's
   physics, not a solver problem.

**Results.** Envelope: 55 mVpp at 200–250 µs → limited before 1 ms. The
measurement windows at 1.45–1.5 ms and 2.9–3 ms both read **410.6 mVpp**,
identical to six digits, so the amplitude is very stable. DC at the emitter
is 1.578 V, matching the hand-calculated bias. The 25 MHz fundamental is
dominant. H2 sits at −10.8 dB, which is *expected and harmless* at the
emitter node of a Colpitts. The emitter current flows in pulses, because Vbe
swings ~±100 mV and the exponential makes that very nonlinear. Frequency
purity is set by the crystal current, not at the emitter, and the next stage
is a class-C multiplier that is nonlinear on purpose anyway.

**Why the low amplitude is a good thing.** Real crystals have a maximum
drive-level rating (~0.1–0.5 mW). Overdriving speeds up aging and frequency
drift. So a good crystal oscillator runs *gently*, which is exactly what
410 mVpp is, and any level the next stage needs comes from amplifying
afterwards. That is why the classic architecture is "small oscillator +
buffer". The requirement this hands to **SIM 6b** is a buffer/driver with a
gain of ~5 (0.41 → ~2 Vpp for the class-C multiplier). It also isolates the
crystal from the multiplier's very nonlinear input.

**Pass criteria (all met)**

| Criterion | Target | Result |
|---|---|---|
| Startup | envelope grows from the kick | 55 mVpp @ 225 µs → limiting |
| Amplitude stability | Vpp constant between distant windows | 410.6 mVpp, identical @ 1.5 ms and 3 ms |
| Spectrum | 25 MHz fundamental dominant | H2 −10.8 dB (normal at the emitter node) |
| Bias under oscillation | matches hand calculation | 1.578 V vs ~1.6 V calculated |

**Rev 2: 5 V.** One resistor: R1 15k → **11k** restores the base to 2.38 V
and I_E to 2.8 mA. With the old divider at 5 V the current would have dropped
23 %. The limiting amplitude would have dropped with it, and the cliff margin
of the whole LO chain depends on that amplitude. Measured on 5 V:
**409.7 mVpp** (0.2 % below the 6 V figure), emitter DC 1.577 V, H2
unchanged. The operating point held, so the oscillation did not notice the
rail change.

### SIM 6b — buffer/driver

**Circuit.** Common-emitter stage AC-coupled to the oscillator's emitter:
bias divider 15 kΩ/5.1 kΩ, collector 270 Ω, emitter split into **47 Ω
unbypassed** (the gain is set by feedback, ≈ R_C/(r_e+47) ≈ 5, not by the
transistor's own spread) + 100 Ω bypassed. The output drives a **replica of
the multiplier's real input network** (1 nF + 10 kΩ self-bias), so the level
is measured into the load it will really see. The buffer also completes the
isolation: its ~2.2 kΩ input barely loads the oscillator node, and the
multiplier's nonlinear base-current pulses now land on the 270 Ω collector
resistor instead of the crystal loop.

**Results** (3 ms run, maxstep 1 ns): **1.904 Vpp** at the load, bit-identical
between the 1.5 ms and 3 ms windows. The 25 MHz fundamental (0.89 V) is
dominant. Oscillator amplitude 399.8 mVpp and DC 1.574 V, unchanged within
2.6 % from the buffer-less SIM 6 run. This also works as a
**timestep-convergence check** (2 ns vs 1 ns agree to ~2 %, unlike SIM 1's
early 2× artifact). One small second-order error: the collector sits at
4.88 V instead of the predicted ~4.6 V. Q2's ~40 µA base current through the
divider's 3.8 kΩ Thevenin resistance takes away ~0.15 V of bias, so Ic lands
at 4.1 mA instead of 5.2 mA and the gain at 4.9 instead of 5.2. That is within
tolerance, so I documented it instead of iterating it away.

This closed the buffer as an amplifier. SIM 5b then showed that 1.9 Vpp puts
the multiplier right on its conduction cliff, so rev 2 raises the drive one
step.

**Rev 2 (the SIM 5b fix): RC 270 → 330 Ω, RE2 100 → 68 Ω.** The gain goes
~4.9 → ~6 and the stage current 4.1 → 4.9 mA, so the larger positive swing
still clears cutoff. Results: **2.354 Vpp** into the replica load,
bit-stable between windows, collector at 4.37 V (Ic = 4.93 mA, matching the
hand calculation), H2 at 31 %. That is the same as rev 1, so the larger swing
adds no clipping. Oscillator amplitude and bias are untouched. On SIM 5b's
settled curve, the multiplier now sits at H5 ≈ 2 V nominal, and the −20 %
drive corner lands on the measured 1.76 Vpp point (H5 = 1.18 V), still 4× the
mixer's need. **The LO chain is closed end-to-end on settled
numbers: crystal 0.40 Vpp → buffer 2.35 Vpp → class-C ×5 → ~2 V of
125 MHz into a mixer that needs 0.3 V.**

**Rev 3: 5 V.** Two resistors, with both dividers recomputed to hold the
operating points: R1 15k → **11k** for the embedded oscillator and R3
15k → **12k** for the buffer. The buffer change is the important one. At
5 V the old divider would leave I_C at 3.4 mA, but the positive peak of
2.35 Vpp into the 330∥10k load needs 3.7 mA of swing. The stage would clip
through cutoff, which is exactly the defect rev 2 fixed. Measured on 5 V:
**2.333 Vpp** into the replica load (−0.9 % vs 6 V), bit-stable between
windows, collector at 3.42 V (I_C = 4.79 mA), H2 = 30.6 % (no new
clipping), oscillator untouched (396 mVpp / 1.573 V). The −20 % drive corner
now lands at 1.87 Vpp, still above the measured 1.76 Vpp point of SIM 5b's
curve. So **the LO chain stays closed on 5 V: crystal 0.41 Vpp → buffer
2.33 Vpp → class-C ×5 → 1.68 V of 125 MHz (1.0 V at the −20 % corner) into
a mixer that needs 0.3 V.**

## SIM 7 — the input filter

**Two jobs, and only one is obvious.** The obvious one is to keep FM
broadcast (88–108 MHz) and airband (118–137 MHz) out of the LNA, because both
are much stronger than any satellite. The one that decides the frequency plan
is **image rejection**. With LO = 125 MHz and IF = 12.9 MHz, the mixer
converts *both* 125 + 12.9 = 137.9 (wanted) and 125 − 12.9 = **112.1** (the
image) onto the same IF, and nothing downstream can separate them afterwards.
This filter is the only protection. That is why I chose 112.1 MHz to fall in
the quiet gap between the FM and airband allocations.

**New trick at VHF: the capacitive divider.** At 12.9 MHz I transformed the
impedance with a *coil tap* (turn 13 of 27). At 137.9 MHz the coil has only
~5 turns, and the tap would need to sit at 13 % of them. That is 0.65 of a
turn, which does not exist. So the tank capacitor is split instead: 15 pF in
series with 100 pF, with the port at the junction. Ratio 15/115 = 0.130, so
the 50 Ω port appears across the tank as 50/0.130² = 2.94 kΩ. It is the same
idea as the tap with different hardware, and it is why every VHF front end
looks like this.

L = 82 nH (Z₀ = 71 Ω), tank total 16.2 pF = 13.0 pF from the divider +
3.2 pF trimmer. With the coil's own Q ≈ 150, the loaded Q comes to 32 and the
passband to ~6 MHz. That is huge next to the 43 kHz the signal occupies, and
it is on purpose. This filter is not there to be selective. It is there to
reject a band 26 MHz away, and a narrow front end would only add loss at the
point where loss directly costs noise figure.

**Results (k stepped):**

| k | regime | passband | image rejection @112.1 | insertion loss |
|---|---|---|---|---|
| 0.015 | undercoupled | 3.5 MHz | 42.0 dB | 4.1 dB |
| **0.031** | **critical** | **6.0 MHz** | **37.6 dB** | **2.2 dB** |
| 0.062 | overcoupled | 11.2 MHz | 31.6 dB | 2.1 dB (2.3 dB dip) |

Also at critical coupling: 137.1 MHz (the other Meteor) passes within 0.03 dB
of centre, FM broadcast is 40.3 dB down and airband 33.0 dB down.

**Before the run I wrote a prediction into the file, and it turned out to be
wrong.** The note said overcoupling might give image rejection for free
through steeper skirts. It does the opposite: 31.6 dB against 37.6 dB
critical. Far from centre the attenuation is set by **loaded Q**, not by
skirt shape. Overcoupling widens the response, which is the same as lowering
the effective Q, so the whole curve moves outward. The skirts really are
steeper, but they start further out.

**Critical coupling chosen.** Undercoupling gives 4.4 dB more rejection but
costs 1.9 dB more insertion loss, and loss ahead of the LNA goes straight
into the noise figure. 37.6 dB already clears the 30 dB target. The 2.2 dB
that remains costs almost nothing in practice. At 137 MHz the galactic
background corresponds to well over 1000 K, clearly above a ~440 K receiver.
So the sky is noisier than the front end, and a couple of dB there changes
little, while the LNA gets real protection from the broadcast bands.

**This is the first block I can measure instead of only trusting the
simulation.** It is 50 Ω in and 50 Ω out, which is exactly what a miniVNA
presents. Build it, sweep it, and lay the trace over this simulation.

**Bench BOM:** L1, L2 = ~5 turns of 0.8 mm enamelled copper on a 5 mm former,
air core, trimmed by squeezing or spreading the turns. They are mounted about
one coil diameter apart with axes aligned (that spacing is what sets
k ≈ 0.03, and sliding them adjusts it). Ct1, Ct2 = 1–10 pF trimmer; 15 pF and
100 pF NP0 (rev 1 values, replaced below).

### SIM 7 rev 2 — real trimmer, real layout (September 2026)

The rev 1 numbers missed two things. First, the trimmer I can actually buy
(Murata TZC3) covers **3–10 pF**, not 1–10. Second, the board's tank loop adds
about **8.6 nH** in series with each 82 nH coil and **0.5 pF** of stray at the
hot node, even after the layout cleanup pulled it tight under the coils
(measured on the layout, `pcb/DESIGN_LOG.md`, step E1). With those in the rev 1
circuit, the trimmer value that centres the filter at 137.9 MHz is 0.7 pF.
That is below the trimmer's minimum, and with a +10 % coil no setting reaches
it at all.

The fix I chose keeps the coil and the tap ratio and changes only the divider:
**C1a/C2a 15 pF → 8.2 pF, C1b/C2b 100 pF → 56 pF.** The ratio 8.2/64.2 = 0.128
matches the rev 1 0.130, so the 50 Ω port still appears across the tank as
~3 kΩ. The loaded Q, the passband and the image rejection are unchanged. The
divider's series capacitance drops from 13.0 to 7.15 pF, and the trimmer takes
up the difference. Six alternatives were run through the same circuit with
the layout parasitics and ±10 % coils (all at critical coupling k = 0.031; IL
is the true 50 Ω-to-50 Ω insertion loss):

| option | trimmer at 137.9 (nominal / −10 % coil / +10 % coil) | IL | passband | image @112.1 |
|---|---|---|---|---|
| 82 nH, 15p/100p (rev 1 values on the real board) | 0.7 / 2.1 / **unreachable** pF | 2.2 dB | 5.4 MHz | 39.6 dB |
| 55 nH (4 turns), 15p/100p | 6.8 / 8.7 / 5.1 pF | 2.9 dB | 5.1 MHz | 42.4 dB |
| 82 nH, 10p/100p (ratio 0.091) | 4.6 / 6.1 / 3.5 pF | 4.1 dB, 137.1 MHz 3 dB down | 5.2 MHz | 44.4 dB |
| 82 nH, 10p/68p (ratio 0.128) | 5.2 / 6.6 / 4.0 pF | 2.2 dB | 5.5 MHz | 39.7 dB |
| **82 nH, 8.2p/56p (ratio 0.128), chosen** | **6.7 / 8.1 / 5.6 pF** | **2.2 dB** | **5.5 MHz** | **40.2 dB** |

The 4-turn coil gives 2 dB more image rejection, but it costs 0.7 dB more loss
in front of the LNA (its loaded Q rises, and the estimate is optimistic because
a 4-turn coil has a lower unloaded Q than the 150 assumed for all rows). It
also leaves 1.3 pF of headroom for a −10 % coil, and it changes a winding
recipe that the footprint, the keepout and the coupling spacing were all
designed around. The 10p/100p option is a different tap ratio, and you can see
it: 2 dB more loss and the other Meteor frequency 3 dB down. Between the two
splits that keep the ratio, 8.2p/56p puts the trimmer in the middle of its
range, with at least 1.9 pF to either end. It still has 1 pF of margin if the
stray copper turns out to be 1 pF instead of 0.5. In that case the 10p/68p
split would be at 3.0 pF, right at the minimum, for a +10 % coil.
`sim7_input_bpf.asc` and `sim12` now use 8.2p/56p. Their ideal-netlist trimmer
value is ~8.7 pF because the parasitics are not in the netlist. On the board,
expect **~6.7 pF**. The ideal rev 2 run at critical coupling: insertion loss
2.4 dB, passband 6.1 MHz, image rejection 39.5 dB, 137.1 MHz 0.5 dB down. That
is within 0.2 dB / 0.1 MHz of the rev 1 filter. (Its under- and over-coupled
rows now show 1–2 dB of ripple, because the trimmer is left at the
critical-coupling optimum instead of being re-tuned for each k, as the rev 1
table implicitly was. On the bench the trimmer gets turned, so only the
critical row is the design.)

## SIM 9 — the LNA

**Why a feedback amplifier and not another tuned stage.** There are two
reasons, and I only saw the first one after SIM 7. That filter was designed
against **50 Ω terminations**, and it will be aligned on the bench against
them too. Whatever follows it must really present 50 Ω, or its response and
its image rejection get distorted. A resistive feedback amplifier has an
input impedance set by *resistors*, so it holds across the band and from part
to part. The second reason comes from SIM 4: intentional negative feedback
through a resistor swamps the parasitic feedback path that made the tuned IF
stages regenerative. This is the classic EMRFD homebrew building block.

**How it works.** Two feedback paths set everything: `Rf` = 470 Ω from
collector to base (through `Cf`, so it carries only RF and leaves the DC
bias independent) and `RE1` = 2.2 Ω unbypassed in the emitter. With the
120 Ω collector load working into the 50 Ω output termination, the shunt
feedback lands the input near 50 Ω while the series feedback sets the gain.
Ie ≈ 21 mA. LNAs run at high current on purpose, for headroom against the FM
broadcast and airband energy that gets past the filter.

**Results (rev 2, 5 V):** S21 = **15.75 dB** at 137.9 MHz, input impedance
**38.3 Ω** (VSWR 1.31:1). The response is flat within 0.5 dB from 20 to
138 MHz and rolls off smoothly through 300 and 700 MHz with **no peaking
anywhere**. The measured maximum over the whole 10 MHz–1 GHz sweep sits
0.02 dB above the low-frequency plateau. That is what a purely resistive
feedback amplifier should do, and exactly what a parasitic resonance would
spoil.

### SIM 9 rev 2 — the same LNA on 5 V

One resistor: **RB1 1.2k → 910**, which restores the base to 1.9 V so I_E
stays at ~20 mA. With the old divider at 5 V, I_E would have dropped to
~15 mA. That costs about a dB of S21 and, worse, shifts the 50 Ω input match
that SIM 7's alignment depends on. The price of the lower rail is headroom,
and this stage shows it the most: the collector now sits at **2.58 V**
(measured; was ~3.5 V), leaving V_CE ≈ 1.55 V. I checked this against what is
needed. The largest signal this stage ever sees is strong local FM broadcast
*after* the filter's −40 dB, about 4 mVpp at the output. So the >300× swing
margin is still far more than enough, and dissipation drops to ~31 mW.
Measured differences against 6 V: S21 15.92 → 15.75 dB, flatness
0.4 → 0.5 dB (the lower V_CB raises C_cb by ~20 %, which is the direction the
physics predicts). Both are inside real part-to-part tolerance.

**A note on noise.** A feedback amplifier is not the lowest-noise topology
(~4–5 dB NF), and I would not trust LTspice noise figures anyway. It does not
matter much here. At 137 MHz the galactic background is higher than the
receiver's own noise, and the bench goal (decoding a replayed recording
through attenuators) does not depend on NF at all. This stage has to deliver
match, gain and stability, and it does.

Like SIM 7, this block is **50 Ω in and out, so the miniVNA can measure it
directly** against this plot.

### SIM 9 — what the layout does to it (September 2026)

The PCB verification (step F in `pcb/DESIGN_LOG.md`) found the LNA's emitter bypass
C49 routed 20 mm from the transistor. That is about 12 nH in series with the
3.5 Ω of RE1 + re. Re-running this testbench with an inductor stepped in the
emitter lead shows the cost: S21 at 137.9 MHz **15.75 dB (0 nH), 15.1 (2 nH),
14.5 (3.5 nH), 13.4 (6 nH), 12.2 (8.5 nH), 11.6 (10 nH), 10.7 (12 nH),
9.5 (15 nH)**. The input impedance moves from 35 − j13 Ω (the "38 Ω / VSWR
1.31" of rev 2 is the scalar |Vb| gauge of that same complex value) through
47 + j9 at 4.5 nH to 66 + j27 Ω at 10 nH. The BPF, aligned into 50 Ω, would
have seen VSWR 1.7. The gain plateau below 100 MHz does not move, so
stability is untouched. The board's emitter cluster was re-placed (5.2 mm of
copper, ~4.4 nH with via and ESL), so on the bench expect **S21 ≈ 14.1 dB,
Zin ≈ 47 + j9 Ω, VSWR ≈ 1.2**. The rev 1 rule of thumb "3.5 nH costs 2.4 dB"
was a hand estimate that ignored the Rf shunt feedback. The simulated figure
is 1.2 dB.

## SIM 8 — the mixer

**Why not a BF998 model.** The plan was a dual-gate MOSFET, but LTspice has
no BF998 model, and a hand-written one would make the simulation confirm
whatever number I typed into it. A **single-balanced switching mixer** (half
a Gilbert cell, the top half of the classic SA602) gets its conversion gain
from *structure* instead. Chopping the signal current with the LO multiplies
it by a square wave, so conv-gm = gm_eff/π, a formula I can check against the
run. It is built from three of the same `QRF` transistors already validated
in six other simulations. On the PCB, build it as drawn or drop in a BF998:
the RF, LO and IF interfaces are identical.

**How it works.** Q1 is a degenerated transconductor (100 Ω unbypassed, the
same approach as the rest of the receiver). Q2/Q3 on top form a differential
switch steered by the LO on Q2's base (Q3's base is the same DC bias,
AC-grounded). Q1's signal current arrives at the 12.9 MHz tank chopped
125 million times a second, and chopping *is* multiplication:
137.9 × 125 → 12.9 MHz. Q3's collector goes straight to VCC. That half of the
current is the −3 dB a single-balanced design gives up for simplicity.

**Results (rev 2, 5 V; LO amplitude and RF frequency both stepped, 8 runs):**

| LO ampl. | conv. gain @137.9 | conv. gain @112.1 (image) |
|---|---|---|
| 0.1 V | 20.2 dB | 20.2 dB |
| 0.2 V | 22.3 dB | 22.3 dB |
| 0.4 V | 22.8 dB | 22.8 dB |
| 0.8 V | **22.9 dB** | **22.8 dB** |

The table shows two things. **The plateau**: above ~0.4 V of LO the gain is
flat to 0.02 dB. Switching is complete, and the operating point sits on the
flat part of the curve (the SIM 5b lesson), with the LO chain's 1.68 V
(1.02 V at the −20 % corner) giving ~4× margin. **The image**: 112.1 MHz
converts within **0.04 dB** of the wanted signal. The mixer cannot see the
difference (no mixer can), and this measures directly that SIM 7's 37.6 dB is
the receiver's whole image protection. Bias health: Q1's emitter DC moves less
than 0.25 mV across the whole LO drive range, so there is no rectification.
The switch pair's common-emitter node does drift up 1.69 → 1.90 V with drive,
but that is just the pair *following the higher base*, which is normal and
not a fault. Settling proven with spaced windows.

### SIM 8 rev 2 — the same mixer on 5 V

For a stacked stage, a rail change is more than retyping the supply, because
both bias dividers are *ratios* of VCC. At 5 V the old values would have
dropped Q1's base from 1.3 V to 1.08 V (I_E down ~35 %, conversion gain down
~2 dB) and the switch-pair bases from 2.5 V to 2.1 V. That squeezes Q1's V_CE
under 0.9 V, close to saturation on LO downswings. The fix is the same recipe
as SIM 4: recompute the dividers to hold the **operating point**, not the
resistor values. RB 47k/13k → **33k/12k** (1.33 V, the same pair every SIM 4
IF stage uses) and RT 18k/13k → **15k/15k** (2.5 V exactly). Measured result:
conversion gain up 0.15 dB (the new divider is slightly stiffer, so I_E
landed a bit higher). Plateau, image blindness and bias health are all
unchanged.

**I also learned something about the solver here.** At the hardest switching
point (LO = 0.8 V) the transient hung. LTspice's default trapezoidal
integrator *rings* numerically on hard switching edges, and the log showed
the timestep pushed down to femtoseconds ("tolerance relaxed … 1.0e-15
seconds") while it fought its own oscillation. `.options method=Gear` is an
integrator that damps numerical ringing instead of sustaining it. It took the
full 8-run sweep from stuck to **7.6 seconds**. Gear's damping is artificial,
so it is only safe when the real resonators are sampled much finer than they
ring. Here the only high-Q element is the 12.9 MHz IF tank at ~775 points per
cycle. My rule of thumb: **hard-switching circuits (mixers, limiters driven
deep) get `method=Gear`; high-Q amplitude measurements keep the default
trapezoidal.**

### SIM 4 rev 3 — four stages on 5 V

Two changes made together, because they interact.

**The supply.** See the section below: 6 V was a repair that got copied, and
5 V is what USB and the ESP32 already provide. This is the block that made the
change risky. A cascode stacks two V_CE plus the tank swing, and keeping
rev 2's dividers at 5 V would have left the *lower* transistor only ~0.69 V
of V_CE. Two divider changes fixed it, both toward standard values: cascode
bias **22k/18k → 8.2k/10k** (stiffer, so four upper base currents pull it
down only 0.19 V) and base bias **47k/13k → 33k/12k** (restoring I_C to
1.04 mA, which the old divider would have halved at 5 V). Result: lower
V_CE = **1.32 V**, which is *more* headroom than the 6 V version had, and the
measured cascode mid-node came out at **1.8546 V** against 1.84 V predicted.

**The fourth stage.** The mixer measured 22.7 dB instead of the 12 dB I first
assumed, so one more stage was all the budget needed. I also considered a
second LNA stage and **rejected** it. It would put full limiter drive at
−115 dBm, below the ~−113 dBm noise floor, so the limiter would be driven by
noise alone. Gain past the noise floor gives nothing and costs stability
margin.

| | rev 2 (3 stages, 6 V) | rev 3 (4 stages, 5 V) |
|---|---|---|
| total gain | 70.5 dB | **95.8 dB** |
| per stage | 23.1 / 23.1 / 24.6 | **24.28 / 24.27 / 24.26 / 23.05** |
| −3 dB bandwidth | 236 kHz | 164 kHz |
| peak | 12.94 MHz | **12.900 MHz** |
| V(b1) | −1.22 dB | −1.26 dB |
| limiting starts at | ~400 µV | **~22 µV** |

Three stage gains are identical to two decimal places, and V(b1) is still
below 0 dB, so there is no regeneration at 96 dB on one board. Limiting
holds: 20 dB of input change produces 1.6 dB of output change. The first tank
stays perfectly linear (×4.97, ×5.99, ×9.95 for inputs of ×5, ×6, ×10) even
22 dB past the limiting threshold, so the compression happens where it
should, at the end. The **cascode mid-node moves 2.4 mV across a 50 dB input
range**. That node standing still is exactly why the Miller path is gone.

Tank capacitors read 68.7 pF in the simulation. That is an *alignment
target*, not a part. On the board each tuned tank is a standard fixed cap
plus a trimmer (56 pF + 5–30 pF here), turned until the peak lands on
12.9 MHz. Everything else in this block is strict E12/E24.

## The supply rail: how 6 V happened, and why it became 5 V

This is a good example of a decision that was correct once and then stopped
being questioned.

6 V was **never an architectural choice. It was a repair.** In SIM 5 the
multiplier's collector swung 17.5 Vpp, past a real BFR93A's 12 V V_CEO. A
tuned collector swings *above* the supply (flywheel effect), so the fix was
to drop the rail to 6 V and raise the damping. Peak collector voltage came
down to ~10.6 V, safely inside ratings. That fix was right.

The mistake was **copying it everywhere without checking it again**. Nine
more blocks were designed on 6 V only because the first one needed it, and
nothing else in the receiver ever needed it.

5 V is the better rail for one practical reason that matters more than
anything else: **it is what USB delivers and what the ESP32 already runs
on**. So the whole receiver takes one cable and no extra regulator. I checked
it against every block. The multiplier gets *more* breakdown margin at 5 V.
The IF cascodes needed two divider changes and ended up with more headroom
than before. The audio chain's bias ladder is set by junction drops and does
not care about the rail at all. The passive blocks (SIM 1, 3, 7) have no
supply to change, but I audited them anyway: every physical value is
E12/E24, a documented hand-wound coil, or a fixed-NP0-plus-trimmer alignment
target per the PCB rule.

What I take from this (it cost nothing here, but it could have cost a
rebuild): a constraint added to fix one block does not automatically belong
to the others. Write down *why* a number was chosen, so the next block can
check whether the reason still applies.

### September 2026 — the rail is 4.6 V, and `sim12` now says so

The ESP32-DevKitC's 5V header pin is `EXT_5V`: USB VBUS through a BAT760
Schottky, which drops 0.32–0.35 V at the ~110 mA the module and receiver draw.
A `.op` of `sim12` at 4.6 V showed collector currents down 16.5 % (median of
20 transistors). That is more than the "0.2 V → 4 %" estimate, because V_BE
is not ratiometric, and it costs about 8 dB of IF gain. Instead of losing
that margin, the bias dividers were re-centred for 4.6 V (upper resistors
recomputed, E24: 33k/12k → 27k/11k on the IF and mixer bases, 8.2k → 6.8k on
vb2, 15k → 13k on vb2n, 11k → 9.1k oscillator, 12k → 11k buffer, 910 → 820
LNA). `sim12_full_receiver.asc` uses `V2_S = 4.6` from now on. Every
current-setting stage is back within +2.5 % of its design point, total draw
40.7 mA. The block simulations above still read 5.0 V and were not re-run, so
`sim12` is the authority. Full table in `../pcb/DESIGN_LOG.md`.



## Integration: SIM 10, 11, 12 — where the standalone testbenches lied

Every block was characterized against an *assumed* neighbour. The detector
was tested against an abstract 33 kΩ sine source, the filter against 33 kΩ
terminations that stood in for "the mixer" and "the IF stage", and the mixer
against a 6.8 kΩ bench tank. Before the stages could be drawn into one
schematic, three seams between blocks needed measuring. An audit of the
passive blocks found all three.

**SIM 10: limiter → detector.** The real drive is SIM 4's clipped ±1.2 V
behind the diode clamp ∥ 100 kΩ, not a clean sine behind 33 kΩ. Interface
decision: make the 33 kΩ a **physical series resistor**. Then the source
impedance the tank sees is 33 k + (clamp ∥ 100k ∥ 10k) ≈ 33.2 kΩ, and SIM 1's
characterization automatically holds. Measured: **S-curve peak still at
exactly 12.95 MHz** (the C1 = 66.7 pF alignment target survives), flank
through the carrier linear at 1.96 mV/kHz (±17 kHz of deviation → ~67 mVpp
of audio, matching SIM 1), tank drive 0.51 V. The detected DC at the carrier
came out at **0.228 V**, which is the same pedestal the audio chain was
designed around. The harmonics of the clipped drive do not matter. H3 lands
at 38.7 MHz, far outside the tank's Q≈80 window. The tank *is* the filter,
which is why slope detectors tolerate square drive.

**SIM 11: mixer → double-tuned filter → first cascode stage.** Two problems
solved. First, SIM 8's 6.8 kΩ tank resistor only existed on the test bench.
In the receiver the filter's first resonator hangs directly on the mixer
collector. Second, **the filter's output tap had to be re-sized**. SIM 3's
BOM note assumed a bare-transistor r_π of 1.3 kΩ (tap at 20 % of turns). But
the real SIM 4 stage input (divider ∥ degenerated cascode base) is ≈6.1 kΩ,
which a 20 % tap would reflect as 152 kΩ. The filter would sit almost
unloaded, Q₂ ≈ 147, with the bandwidth squeezed to ~124 kHz. Fix: tap at
**13/27**, the same 0.507 µH + 0.588 µH split every SIM 4 tank already uses,
so there is one coil recipe for the entire IF strip. It reflects 26 kΩ and
restores Q₂ ≈ 81, k_crit ≈ 0.011, and the ~200 kHz design bandwidth.
Measured in situ: **5 mV of RF → 53.6 mV at the first IF base = +20.6 dB**.
That is four dB *better* than the composed paper figure
(22.8 − 6.2 = 16.6 dB), because the in-situ tank sits higher in impedance
than the 6.8 kΩ bench load. Selectivity is **−29.6 dB at +500 kHz** (the
filter alone measured −27.9). Every bias is untouched: the mixer's emitter DC
is identical to five digits with the new load, and the stage current is
1.03 mA against the 1.04 mA design.

The verification workflow was useful again on these two files. Before
anything was run, it caught the tank capacitor of SIM 11 floating 16 grid
units above its wires. That was a displaced symbol with both pins dangling,
which is the really dangerous kind of geometry bug. (How these checks are
best done, and which kind of "catch" turns out to be real, was itself revised
during the assembly step below.)

**SIM 12: the whole receiver in one schematic.** It was assembled
*programmatically*. Each verified block was moved into its own vertical band
(a pure y-offset of the source file), test sources were removed by explicit
lists, blocks were joined **only by net labels**, and every instance name got
a block suffix. Two new design decisions were made at assembly and are in the
file. The first is the **LO tap**: the ×5 output tank's capacitor splits into
14 pF + 47 pF. The series 10.79 pF keeps 125 MHz, and the ratio 0.23 delivers
~0.39 V to the mixer, its measured plateau point. The second is the cascode
bias divider serving all **four** stages, which is its actual design point. A
full-chain transient is out of scope on purpose (2400 Hz audio against 0.1 ns
RF steps, and a crystal that takes 1 ms to start). What the master schematic
runs is **`.op`**, which checks every bias network on the single 5 V rail in
one go. Result: **every node matches its block sim**. The cascode mid-nodes
match to six digits (1.85459 V vs 1.8545865 standalone), the IF emitters to
all printed digits (0.527018 V), and four stage bases are identical at
1.24307 V. This shows the assembly kept each block's netlist exactly. Total
receiver draw: **41.6 mA from 5 V ≈ 208 mW**, one USB port with room to
spare. (An earlier reading of 39 mA was an artifact. A leftover `.ic` had
clamped the oscillator dead during that `.op`. The kick line now stays
commented and is re-enabled only for transient runs.)

**Two method improvements came out of the assembly. Both are worth more than
the schematic itself:**

1. **`LTspice.exe -netlist file.asc` is the definitive geometry check.** It
   makes LTspice itself write out the netlist without simulating, so you get
   the ground truth for free. All coordinate-based re-derivation (ours and
   the review agents') is now only a pre-filter. The generated netlist is
   what gets audited, line by line.
2. **An old rule, corrected by evidence:** a wire drawn *exactly* between a
   component's two pins is **not a short**. LTspice absorbs it and puts the
   component in series, the same as dropping a part onto a wire in the
   editor. Netlisting `sim5` proved it: that file has carried two such
   overlay wires through every one of its measured runs (`RB base 0 10k`, no
   short). The real geometry trap is the *displaced symbol with floating
   pins*, and the netlist shows those right away as dangling auto-numbered
   nodes. One review "fatal" on this file was traced to exactly this false
   positive before any fix was applied. So check the evidence before acting
   on a diagnosis that only sounds right.

One quirk to remember for future measurement work: LTspice gives each net
one canonical name, so two seam labels are hidden by older labels on the same
net (`tapB` won over `n_rf1`, `b2` over `n_t1`). The connectivity is correct,
but `.meas` must use the canonical names. Also, `.ic` initial conditions
**clamp `.op`**, so the oscillator kick line is kept as a comment and
re-enabled only for transient runs.

## SIM 13 — the money shot: FM in, audio out

This is the demodulation test the whole receiver exists for. A **true
APT-format FM signal** (12.9 MHz carrier, FM by 2400 Hz at ±17 kHz deviation,
modulation index 7.083) is injected at the IF-chain input. It goes through
the four cascode stages, the limiter, the slope detector and the full audio
chain to the ADC node. (I inject at the IF because FM survives frequency
conversion untouched, the RF half is already measured in SIM 11, and
137.9 MHz in a 2 ms run would need 4×10⁹ timesteps. Nobody simulates a
receiver that way.) Two amplitude steps 20 dB apart, **100 µV and 1 mV**,
both deep in limiting.

**Results.** The ADC node reads a clean 2400 Hz sine: fundamental ~0.96 V /
0.79 V, in-band THD **8.5 % / 10.6 %** (mostly H2). The key numbers: the
limiter output moves **1.3 %** over the 20 dB input range, the detected
audio moves **0.5 dB** (124 → 117 mVpp), and the ADC signal in matched
windows moves **0.03 dB**. So twenty decibels of input change become half a
decibel. This is what the 96 dB of gain and the limiter were built to do, and
here it is measured end to end.

**Finding 1: the signal-acquisition transient.** Rev 1 started from the
no-carrier DC point. When the carrier appeared, the detector pedestal stepped
0 → 0.3 V, but the 100 µF emitter bypass of the audio gain stage held its old
bias. So the whole step fell on the 150 Ω degeneration, and the stage sat in
saturation for the entire window (the ADC read −0.55 V). This is *real
receiver behaviour*. The first ~50–100 ms of audio after a carrier appears
are garbage while the audio coupling capacitors (τ ≈ 23 ms) settle to the new
pedestal. That does not matter in a ten-minute pass, but now it is
documented. The test presets the settled state with `.ic V(audio)=0.345`. The
small remaining mismatch (~30–45 mV) explains the raised ADC baseline and the
step-2 window drift in the reported numbers.

**Finding 2: the audio chain runs at 2× its design drive.** The detector
delivers ~120 mVpp, not the 60 mVpp SIM 2 was designed around. The real
limiter drives the detector tank harder than SIM 1's characterization
source, and the S-curve slope grows with drive. So Q4 works near its swing
ceiling, with H2 at 8–10 % instead of the designed 3.9 %. The fix is one
resistor (raise RE4A 150 → ~330 Ω, which halves the audio gain and re-centres
the swing). I flagged it for the bench instead of applying it blind, because
the real levels there will have their own tolerances, and the trimming
decision should be made on measured hardware.

*What happened next.* The overdrive was actually fixed the same day in a
different way. SIM 2 rev 3b changed RC4 10 kΩ → 3.3 kΩ and RE4B 2.7 kΩ →
820 Ω for exactly this 120 mVpp drive. The SIM 13 re-run with those values
read THD 1.56 / 2.43 % and 0.75 / 0.69 Vpp at the ADC (the THD figures in the
results paragraph above are from the run before 3b). The RE4A note was just
never removed.

**September 2026: RE4A 150 → 270 Ω, for the real rail.** At 4.6 V instead of
5.0 V, Q4's collector sits ~0.2 V lower, so the headroom that rev 3b gained
got smaller. The sim12 audio chain was run on its own at 4.6 V with the
detector's 2400 Hz content stepped 60 / 89 / 120 mVpp (89 is the measured
SIM 13 value, the others cover its tolerance) and the pedestal 0.27 / 0.31 V:

| RE4A | Q4 V_CE minimum, worst case | ADC swing at 89 mVpp | ADC swing at 60 mVpp | THD at 89 mVpp |
|---|---|---|---|---|
| 150 Ω | 0.43 V (near saturation) | 0.75 Vpp | 0.51 Vpp | 1.2 % |
| 220 Ω | 0.74 V | 0.54 Vpp | 0.37 Vpp | 0.7–0.8 % |
| **270 Ω** | **0.92 V** | **0.45 Vpp (~560 counts)** | **0.30 Vpp (~380 counts)** | **0.6 %** |
| 330 Ω | 1.09 V | 0.38 Vpp | 0.25 Vpp (~320 counts) | 0.4–0.5 % |

270 Ω doubles the worst-case headroom and still leaves the ADC ~380 counts
at the lowest drive. That is well above the 256 grey levels APT needs and
above the ESP32 ADC's noise. 330 Ω would cut that margin for headroom the
stage no longer needs. SIM 13 re-run end to end with 270 Ω (5 V block sim):
THD **1.10 / 1.82 %**, ADC **0.45 / 0.42 Vpp** centred on 1.24–1.31 V, and the
20 dB input step is still erased at the detector. `sim12`, `sim13`, the
schematic and the board (R49) all use 270 Ω.

## Gain budget, end to end

Now **every block is measured**, and the mixer→filter→IF seam is measured
*in situ* (SIM 11) instead of composed from standalone figures:

| stage | | running total |
|---|---|---|
| input BPF (SIM 7) | −2.2 dB | −2.2 |
| LNA (SIM 9) | +15.8 dB | +13.6 |
| mixer + IF filter, to the first IF base (SIM 11, in situ) | +20.6 dB | +34.2 |
| IF chain (SIM 4, rev 3) | +95.8 dB | **+130 dB** |

The detector needs ~1.2 V, so full limiter drive happens at about **−106 dBm
at the receiver input** (~22 µV at the IF chain). The 4 dB found at the
mixer/filter seam show up directly in the sensitivity threshold.

**The first test is done by cable, not over the air.** A Pluto plays back a
recorded NOAA APT pass into the receiver through an attenuator chain. There
is no antenna and nothing is transmitted. In practice the source has to be
brought down by about 100 dB, which is done in two places. The Pluto's own
TX gain is adjustable over roughly 90 dB in software, and a fixed pad
(20–30 dB in a couple of sections) takes the rest and gives a defined 50 Ω
source. Working with a known, repeatable signal is the whole reason to start
here. Every fault found on the bench is then the receiver's fault, not the
sky's.

The same budget is what makes over-the-air reception possible later, and
that is why I designed it to this number. A QFH collects roughly **−90 dBm**
from a Meteor pass overhead and **−100 dBm** near the horizon. The noise
floor in this bandwidth is about **−113 dBm**, so a usable signal starts
around −100 dBm. Full limiting at −106 dBm means the limiter is saturated for
*every* signal worth decoding. That is exactly the behaviour you want from an
FM receiver with no AGC.

Earlier revisions of this table stopped at +100.7 dB and −77 dBm, and
recorded that the chain was "about 23 dB short" for live satellite work. That
gap is now closed by the fourth IF stage. It was the cheapest 24 dB
available, because it is a copy of an already-validated block.

## What simulation deliberately does not cover

- **Noise figure**: generic transistor models give unrealistic NF numbers at
  VHF, so it is measured in the lab instead.
- **Stability of the 105 dB chain**: decided by physical layout and
  shielding, not by the netlist.
- **Absolute VHF gain**: only treated as an indication. The bench (RF probe +
  calibrated attenuators + Pluto) gives the real numbers, including the final
  measured receiver sensitivity.

## References

- P. Horowitz, W. Hill, *The Art of Electronics*: envelope detectors, RC time
  constant trade-offs.
- W. Hayward, R. Campbell, B. Larkin, *Experimental Methods in RF Design*
  (ARRL). Discrete homebrew receiver practice: tuned amplifier chains,
  crystal oscillators, frequency multipliers, dual-gate MOSFET mixers.
- *The ARRL Handbook for Radio Communications*: FM slope detection, superhet
  frequency planning, image rejection.
- NOAA, *User's Guide for Building and Operating Environmental Satellite
  Receiving Stations*: APT signal format (2400 Hz subcarrier, ±17 kHz
  deviation, 2 lines/s).
- [Signal Identification Wiki — APT](https://www.sigidwiki.com/wiki/Automatic_Picture_Transmission_(APT))
  as a quick signal parameter reference.
- [LTspice](https://www.analog.com/en/resources/design-tools-and-calculators/ltspice-simulator.html)
  (Analog Devices): all simulations. 1N5711-type Schottky model parameters
  are from the vendor datasheet values commonly distributed with SPICE tools.
- **Claude (Anthropic)**: AI assistant I used as a design and simulation
  pair-programmer throughout this receiver project. Schematics and
  measurement decks were drafted step by step from requirements we
  developed together, and every claim was checked against my own simulation
  runs (and, later, the bench). Design decisions and results are verified,
  not assumed.
- Slope-detector theory and the max-slope detuning point f₀/(2√2·Q): standard
  resonance-curve analysis, see ARRL Handbook FM detection chapter.

## License / attribution

This is my project. I set the goals and the requirements (a fully discrete
receiver with no ICs in the signal path), I made or approved every design
decision, and the building and bench testing are mine. It builds on
well-documented amateur-radio practice (see the References above). The simulation files are
plain LTspice `.asc` schematics. Each sheet has a short header (what it tests, the
result, where it is explained), and the longer notes I first wrote on the
sheets while working are collected in [`sim_notes.md`](sim_notes.md).

I used Claude (Anthropic) as an AI assistant. It drafted most of the LTspice
schematics and testbenches from my requirements and helped me analyse the
results. I checked the results and decided what went into the design.

The antenna half of the project (`../qfh_matlab`) is different, because its
code is not originally mine. It is a MATLAB port of two programs that are
freely available online: John Coppens' QFH calculator
([jcoppens.com](https://www.jcoppens.com/ant/qfh/calc.en.php), `qfhcalc.js`,
released under GPL-2.0) and QFH2nec
([github.com/oceantrotter/QFH2nec](https://github.com/oceantrotter/QFH2nec),
GPL-3.0), which itself adapts the Coppens calculator code. That is why
`qfh_matlab` is published under GPL-3.0. The full credits are in its README.
