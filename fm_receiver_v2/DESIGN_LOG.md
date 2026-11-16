# Receiver version 2: design log

This is the step-by-step record of the second version of my 137.9 MHz FM
receiver. Version 1 is in [`../fm_receiver`](../fm_receiver) and its board in
[`../pcb`](../pcb). Both stay as they are.

Status (2026-11-16): every block is designed and simulated, from the antenna
to the ESP32's ADC, including the supply. The independent check, the parts
list, the schematic, the board, the reviews before the order and the files for
JLCPCB are done (sections below, and [`../pcb_v2`](../pcb_v2)). The boards were
ordered on 2026-11-16 (5 boards, 2 assembled by JLCPCB, connectors included);
nothing is tested or measured yet. This log is written in the order things
happened: where a later section corrects an earlier number, the later one
counts. The short version is in [`README.md`](README.md), the cost in
[`COST.md`](COST.md).

## Why a second version

Version 1 works in simulation, but its board became expensive and risky to
build:

- It puts 96 dB of gain at one frequency (12.9 MHz) on seven hand-wound
  toroids that stand in one open row. A study showed that the strip could
  oscillate, so the board grew to 210 × 75 mm with two shield fences.
- It has 11 hand-wound coils and 11 trimmers to align.
- JLCPCB quoted about €140 to assemble two boards. One likely reason: its
  100 µF capacitor is a "Standard only" part, and one such part moves the
  whole order to the expensive assembly type.

## Goal

JLCPCB assembles the board completely, and the order (5 boards, 2 of them
assembled) costs less than €50 before shipping and tax. There are no coils to
wind and nothing to tune.

Limits that follow from JLC's prices (read on 13 November 2026):

- board at most 100 × 100 mm (5 boards cost $5.30; one millimetre more and the
  price jumps to $11–13);
- Economic assembly only, so no part that JLC flags "Standard only";
- at most 4 "Extended" part types ($3.07 fee each); Basic and Preferred parts
  carry no fee.

## The test it is built for

The NOAA satellites that sent this signal are switched off, so the receiver's
job is a bench test. My ADALM-Pluto replays a recorded NOAA pass at
137.9 MHz. The signal goes through SMA attenuators and a cable into the
receiver's antenna input. The ESP32 samples the audio, and software turns the
samples into the picture. If I can read the picture, the receiver works.

What that asks of the design, and where it is checked:

| Need | Why | Check |
|---|---|---|
| Works from about −30 dBm down to the noise | the Pluto gives up to about +7 dBm; 40 dB of attenuators leave −33 dBm, and the Pluto's own setting goes down from there | L2 |
| No damage with too little attenuation | a forgotten attenuator must not kill the LNA | N1 |
| Brightness comes through in proportion | the picture is the amplitude of the 2400 Hz tone | H3, I2 |
| Flat from 320 to 4480 Hz | fine detail sits in the side frequencies of the tone, up to ±2080 Hz | I1, H3 |
| Tolerates about ±10 kHz of frequency error | Pluto ±25 ppm, my two crystals, and the Doppler shift inside the recording | the second IF is 132 kHz wide and the detector has no tuned circuit; an offset only shifts a DC level that is blocked |
| Nothing above 39.6 kHz at the ADC | the ESP32 samples at 44.1 kHz, and those frequencies would fold back onto the picture | I1 |

## What stays the same

- No ICs in the signal path. Every stage is built from transistors, so I can
  understand each one.
- 137.9 MHz, FM with ±17 kHz deviation. The picture is in the amplitude of
  the 2400 Hz APT tone (audio from 320 to 4480 Hz).
- One USB cable through the ESP32 DevKitC. Its ADC (GPIO36) digitizes the
  audio: pedestal 1.26 V, swing inside 0.5–2.0 V, source below 10 kΩ.
- Image rejection of at least 30 dB.
- Test by cable: the Pluto replays a recorded NOAA pass through attenuators,
  and the result is the picture.
- The 25 MHz crystal × 5 oscillator, the LNA and first-mixer circuits and the
  audio filter of version 1 are the starting point for the same blocks here.

## What changes

| | Version 1 | Version 2 |
|---|---|---|
| Conversions | one: 137.9 → 12.9 MHz | two: 137.9 → 12.9 → 1.418 MHz |
| Coils | 7 toroids and 4 air coils, wound by hand | 11 small SMD inductors (3 values) |
| Trimmers | 11 | none |
| Selectivity | high-Q tanks, each tuned by hand | wide, low-Q tuned circuits that tolerate ±5 % parts |
| Gain | 96 dB at 12.9 MHz | split over 137.9 MHz, 12.9 MHz and 1.418 MHz |
| IF amplifier stage | cascode | emitter-coupled pair |
| FM detector | slope detector (a tank tuned 55 kHz off) | charge-pump detector (no tuned circuit) |
| Transistors | BFR92P everywhere | 2SC3356 at VHF, S9018 at 12.9 and 25 MHz, MMBT3904 / 3906 elsewhere |
| Oscillator level | set by the transistor | set by a diode clamp |
| Supply rail | 4.6 V straight from the DevKitC | 3.3 V from a discrete regulator that copies the DevKitC's 3V3 pin |

## Architecture

```
antenna -> tuned circuit -> LNA -> 2 tuned circuits -> mixer 1 <- 125 MHz
                                                                  (25 MHz crystal -> follower -> squarer x 5 -> 2 tuned circuits)
        -> first IF, 12.9 MHz: 4 tuned circuits, 2 emitter-coupled pairs
        -> mixer 2 <- 14.31818 MHz crystal oscillator
        -> second IF, 1.418 MHz: 2 tuned circuits, 1 tuned pair, 1 limiter pair
        -> pump-driver pair -> charge-pump detector
        -> audio: buffer, 4th-order low-pass, gain -> ESP32 ADC
supply: DevKitC 5V pin -> discrete regulator (reference: the DevKitC's 3V3 pin) -> 3.3 V rail
```

Why two conversions. Without trimmers a tuned circuit has to be wide: with
±5 % parts its centre can sit ±5 % off, so its loaded Q must stay below about
10. At 12.9 MHz that is 1.3 MHz of bandwidth, far too wide for a 43 kHz signal.
At 1.418 MHz the same Q gives about 130 kHz, which is narrower than
version 1's 210 kHz. So the first IF only has to reject the second image, and
the second IF sets the bandwidth.

Why the gain is split. Version 1's risk came from 96 dB at one frequency. Here
no frequency carries much more than about 75 dB before the limiter.

## Frequency plan

| | Frequency | How |
|---|---|---|
| Signal | 137.900 MHz | |
| First LO | 125.000 MHz | 25.000 MHz crystal × 5 |
| First IF | 12.900 MHz | 137.9 − 125 |
| First image | 112.100 MHz | 125 − 12.9 |
| Second LO | 14.31818 MHz | crystal oscillator |
| Second IF | 1.41818 MHz | 14.31818 − 12.9 |
| Second image | 15.736 MHz at the first IF (140.736 MHz at the antenna) | 14.31818 + 1.41818 |

Products of the two oscillators that could land in an IF:

| Product | Frequency | Distance |
|---|---|---|
| 2 × 14.31818 − 25 | 3.636 MHz | 2.2 MHz above the second IF |
| 4 × 25 − 7 × 14.31818 | 0.227 MHz | 1.2 MHz below the second IF, 11th order |
| 9 × 14.31818 and 10 × 14.31818 | 128.86 and 143.18 MHz | 9.0 MHz below and 5.3 MHz above the signal |
| 25 − 14.31818 | 10.682 MHz | 2.2 MHz below the first IF |
| 25 + 8 × 14.31818 | 139.545 MHz | 1.6 MHz above the signal, 9th order |

The first LO is made from the fifth harmonic of 25 MHz, so it also carries a
little of the other harmonics. Each of them converts two more frequencies into
the first IF:

| LO content | Converts | Why it matters |
|---|---|---|
| 150 MHz (6th harmonic) | 137.1 and 162.9 MHz | 137.1 MHz is the other weather-satellite channel, inside the front end's passband |
| 100 MHz (4th) | 87.1 and 112.9 MHz | 87.1 MHz is at the edge of the FM broadcast band |
| 75 and 175 MHz (3rd, 7th) | 62.1, 87.9, 162.1, 187.9 MHz | 87.9 MHz is FM broadcast |

So the 125 MHz chain has to be clean, above all at 150 MHz.

Second-crystal choices that were rejected:

- **13.560 MHz** (second IF 0.66 MHz): the second image is only 10 % away
  from 12.9 MHz. Four untrimmed tuned circuits reject it by about 25 dB,
  against 47 dB for 14.31818 MHz.
- **12.000 MHz** (second IF 0.9 MHz): 2 × 12 − 25 = 1.0 MHz, a constant
  carrier only 100 kHz from the IF.
- **11.0592 MHz** (second IF 1.84 MHz) stays as a fallback: JLC has it as a
  fee-free part, but the detector output would be about 23 % smaller.

## First checks before the design

Monte-Carlo runs with ideal stages, 300 runs each, every inductor and
capacitor drawn at random inside ±5 %, nothing trimmed. These planning decks
are in my private notes (not published).

| Check | Result |
|---|---|
| Front end, 3 tuned circuits at 137.9 MHz, inductor Q 38 | image rejection 38 dB worst case, 45 dB typical |
| First IF, 4 tuned circuits (loaded Q 10) | second-image rejection 38 dB worst case, 47 dB typical; up to 8 dB loss from mistuning |
| Second IF, 3 tuned circuits (loaded Q 7) | bandwidth about 110 kHz; up to 3.3 dB loss from mistuning |

## Parts, chosen for JLCPCB

Checked live in JLC's parts library on 13 November 2026. Only four part types
carry the Extended fee; everything else is Basic or Preferred.

| Part | Used for | JLC part | Type |
|---|---|---|---|
| 68 nH ±2 % wirewound, 0603 (Murata LQW18AN) | 137.9 and 125 MHz tuned circuits (5) | C86135 | Extended |
| 3.3 µH ±5 %, 1008 (Q 22 at 25 MHz) | 12.9 MHz tuned circuits (4) | C6364740 | Extended |
| 100 µH ±5 %, 1210 (not shielded, see `PARTS.md`) | 1.418 MHz tuned circuits (2) | C295124 | Extended |
| 14.31818 MHz crystal, 3225, 20 pF | second oscillator | C34748 | Extended |
| 25 MHz crystal, 3225, 12 pF | first oscillator | C9006 | Basic |
| 2SC3356 (fT 7 GHz) | LNA, first mixer, squarer (7) | C28646266 | Preferred |
| S9018 (fT 800 MHz) | first IF pairs, 25 MHz oscillator, follower (6) | C41375130 | Preferred |
| MMBT3904 / MMBT3906 | everything else (17 / 5) | C20526 / C7420354 | Basic / Preferred |
| BAS70, BAV99, 1N4148W | detector and clamps, antenna protection, bias | C7502686, C2500, C81598 | Preferred, Basic, Basic |

- Capacitor values are limited to the fee-free ones. In C0G these are
  3, 4.7, 6, 6.8, 8.2, 10, 12, 15, 18, 20, 22, 27, 30, 33, 47, 56, 68, 100 and
  330 pF. This is why some tuned circuits use two capacitors.
- The netlist has about 250 parts: 101 resistors, 93 capacitors,
  35 transistors, 7 diode packages, 11 inductors and 2 crystals. At
  $0.0016 per solder joint the part count hardly changes the price; the fees
  per part type do.
- Still to confirm when the parts list is made: the fee status of 470 pF,
  4.7 nF, 10 nF and 22 µF, and the drive-level rating of both crystals (the
  design assumes 100 µW).
- *Later (2026-11-14):* the parts list settled these points. The final
  counts are 104 resistors, 92 capacitors, 38 transistors (19 MMBT3904 and
  6 MMBT3906 among them), 5 diode packages (the 1N4148W left with the bias
  fix), 11 inductors and 2 crystals: 252 parts. The capacitors above are
  Basic parts, and both crystals are rated 10 to 200 µW. See
  [`PARTS.md`](PARTS.md).

## Simulations

The sections below are in the order the blocks were designed. After an
independent check several parts changed; the section "After the independent
check" near the end lists them with the current numbers.

Conventions:

- Every block is a file `rx2_blk_*.inc`. The test decks `rx2_*.cir` include
  the blocks, so a block exists only once. Open a `.cir` in LTspice and press
  Run.
- `models.lib` holds the nominal transistor models. `models_slow.lib` holds a
  slow, low-gain corner with the same names. A deck changes corner by changing
  one line.
- Rail 3.3 V, checked at 3.0 and 3.6 V.
- The FM test signal is ±17 kHz deviation with a 2400 Hz tone
  (`SFFM`, index 7.0833). Audio level is the 2400 Hz component from `.four`;
  distortion is the partial THD (in-band harmonics only).
- Part tolerance is built into the blocks as `mc(value, tol)`. A deck sets the
  tolerances to 0 for nominal runs.
- Elements whose names end in `_x` are layout estimates (pad capacitance, via
  inductance). They are not parts.
- The two crystals are subcircuits (`XTAL25`, `XTAL14`). With `xforce=1` their
  resonant branch is open and a deck forces the crystal current instead (see
  B2). Every deck sets `xforce`.
- LTspice writes large output files, so the decks are run from a copy outside
  the repository.

### G1: the charge-pump detector (`rx2_g1_detector.cir`)

An emitter-coupled pair turns the IF into a square wave of fixed height
(tail current × collector resistor, about 1.78 V). On every rising edge a
47 pF capacitor pushes one fixed packet of charge through a PNP transistor
into the 27 kΩ load. A Schottky diode refills the capacitor on the falling
edge. The average current is packet × frequency, so the output voltage
follows the frequency. There is no tuned circuit.

| Drive (peak) | Rail | Output DC | 2400 Hz audio (peak) | THD |
|---|---|---|---|---|
| 0.1 V | 3.3 V | 1.10 V | 8.0 mV | 0.32 % |
| 0.3 V | 3.3 V | 1.49 V | 13.1 mV | 0.24 % |
| 1.0 V | 3.3 V | 1.51 V | 13.4 mV | 0.34 % |
| 0.3 V | 3.0 V | 1.41 V | 12.2 mV | 0.26 % |
| 0.3 V | 3.6 V | 1.56 V | 13.8 mV | 0.23 % |

- Static slope: two unmodulated carriers 34 kHz apart give 26.6 mV of
  difference, so 0.78 mV per kHz. That is 73 % of the ideal 1.2 % of the DC
  level. The loss comes from the last part of each charge packet arriving
  late.
- The detector needs at least 0.3 V of drive. Above that the output changes
  by 0.2 dB for 10 dB more drive.
- What sets the audio level: only the DC level at the output (here 1.5 V),
  not the size of the capacitor. The DC level is limited by the PNP's
  collector-base voltage (its base sits at 2.15 V).
- The two diodes that set the tail current make the square-wave height
  nearly independent of the rail.

### F1, F2, F3: the second-IF strip (`rx2_blk_if2.inc`)

Tuned circuit T5 is the load of the second mixer. Pair A amplifies into
tuned circuit T6. Pair B is a limiter with a resistor load. Pair C drives the
charge pump. Each tuned circuit is 100 µH (Q 30 assumed, 4 pF of
self-capacitance) with 100 pF + 10 pF.

Small-signal response, `rx2_f1_if2_ac.cir`:

| | Value |
|---|---|
| T5 at resonance | 6.6 kΩ |
| Peak of T5 and T6 together | 1.4175 MHz |
| −3 dB bandwidth of T5 and T6 together | 132 kHz (1.352 to 1.484 MHz) |
| Gain of pair A | 28.3 dB |
| Gain of pair B | 21.0 dB |
| Gain of pair C | 23.4 dB |

FM signal fed into T5 as a current, `rx2_f2_if2_fm.cir`:

| Input current (peak) | Voltage on T5 (peak) | Audio (peak) | THD |
|---|---|---|---|
| 0.03 µA | 0.2 mV | not limiting | |
| 0.1 µA | 0.66 mV | 11.3 mV | 23 % |
| 0.3 µA | 2.0 mV | 13.3 mV | 2.3 % |
| 1 µA | 6.6 mV | 13.9 mV | 1.5 % |
| 10 µA | 68 mV | 13.4 mV | 0.58 % |
| 100 µA | 0.72 V | 13.5 mV | 0.66 % |

Part tolerance, `rx2_f3_if2_tolerance.cir`, 300 runs, transistor level:

| Tolerance of the inductors | Loss at the signal frequency, worst case | Loss at ±21 kHz, worst case | Peak moves by |
|---|---|---|---|
| ±5 % (capacitors ±5 %) | 2.3 dB | 3.3 dB | ±48 kHz |
| ±10 % (capacitors ±5 %) | 4.7 dB | 6.5 dB | ±80 kHz |

So the second-IF inductors must be ±5 % parts.

### E1: the second mixer (`rx2_blk_mix2.inc`, `rx2_e1_mixer2.cir`)

The first try was the single-balanced mixer of version 1 (three
transistors). It leaked 30 mV of the 14.3 MHz LO onto T5, because the
switched bias current itself has a component at the LO frequency. T5 only
attenuates that by 36 dB, so the LO was larger than a weak signal and it
captured the limiter: at 0.1 mV in, the audio was garbage.

The mixer is now double-balanced (a Gilbert cell from six MMBT3904). The
two switched bias currents cancel at the output. What remains leaks through
the collector-base capacitance of the switching transistors and grows with
the LO level, so the LO drive is kept low.

| LO drive (peak) | Conversion gain into T5 | LO left on T5 |
|---|---|---|
| 0.05 V | 3.5 (10.9 dB) | 0.46 mV |
| 0.1 V | 5.0 (14.0 dB) | 0.92 mV |
| 0.18 V | 5.6 (14.9 dB) | 1.8 mV |
| 0.4 V | 5.9 (15.4 dB) | 4.4 mV |

Chosen drive: about 0.2 V peak. The oscillator's own divider capacitor feeds
the LO bases directly.

### E2: the second oscillator (`rx2_blk_lo2.inc`, `rx2_e2_lo2_osc.cir`)

**A simulator trap first.** The first version of this oscillator "ran at
0.20 V with 39 µW in the crystal". That result was wrong. LTspice quietly adds
damping to every inductor in a transient run unless the inductor is given an
explicit parallel resistance. A crystal's resonant branch is a 15 mH inductor,
so the simulated crystal was far lossier than a real one. With the damping
switched off (`Rpar=1e15`) the same circuit puts about 480 µW into the
crystal, roughly five times what a small crystal should get.

**The new circuit.** A Colpitts oscillator with one MMBT3904 (68 pF and
100 pF, 1.4 mA). The crystal sits between the base and a separate node. Two
Schottky diodes (BAS70) in anti-parallel clamp that node at about ±0.33 V. So
the amplitude, and with it the power in the crystal, is set by the diodes and
not by the crystal's resistance or the transistor. A 68 pF / 33 pF divider
takes about 0.2 V to the mixer.

How it is measured. The crystal's resonant branch is replaced by a current
source at 14.31818 MHz. For each amplitude the deck computes the series
resistance the oscillator can keep going. The oscillator settles where that
equals the crystal's resistance.

| Crystal resistance | Crystal current (peak) | Level at the mixer (peak) | Power in the crystal |
|---|---|---|---|
| 30 Ω | 1.47 mA | 0.23 V | 32 µW |
| 60 Ω (assumed typical) | 1.32 mA | 0.22 V | 52 µW |
| 80 Ω (worst) | 1.22 mA | 0.21 V | 60 µW |
| 60 Ω, slow transistor | 1.20 mA | 0.21 V | 43 µW |

- Start-up margin (resistance the oscillator can sustain at small amplitude,
  divided by the crystal's): 5.7 at 60 Ω, 4.3 at 80 Ω, 3.4 at 80 Ω with the
  slow transistor.
- The crystal sees about 19 pF, against its rated 20 pF. That pulls the
  frequency by a few hundred hertz.

### H1: the back half with an FM signal (`rx2_h1_backhalf_fm.cir`)

FM at 12.9 MHz goes into the second mixer; the audio comes out of the
detector. Nominal models, 3.3 V, 27 °C:

| Input at mixer 2 (peak) | Detector DC | Audio (peak) | THD |
|---|---|---|---|
| 0.1 mV | 1.38 V | not limiting yet | |
| 0.3 mV | 1.50 V | 11.6 mV | 4.2 % |
| 1 mV | 1.52 V | 13.1 mV | 1.7 % |
| 10 mV | 1.52 V | 13.8 mV | 0.28 % |

At 10 mV input, against the conditions:

| Condition | Audio (peak) | THD |
|---|---|---|
| Nominal | 13.8 mV | 0.28 % |
| Slow, low-gain transistors | 12.4 mV | 0.54 % |
| Rail 3.0 V / 3.6 V | 12.9 / 14.6 mV | 0.31 / 0.28 % |
| −10 °C / 60 °C | 15.9 / 12.1 mV | 0.32 / 0.19 % |

- The back half draws 5.7 to 7.2 mA.
- The level falls by about 0.3 % per °C, because the two bias diodes set the
  tail current. That is slow drift, not distortion.
- One early fault found here: with 10 kΩ in the reference base of pair C,
  the square-wave height depended on the transistor's current gain, and the
  slow corner lost 3.9 dB of audio. With 470 Ω it loses 0.9 dB.
- The limiter needs about 1 mV at the second mixer for clean audio. The
  stages before it must therefore bring the receiver's own noise to about
  that level, so the limiter is always saturated. That sets the gain target
  for the front half: about 70 dB from the antenna to the second mixer.

### D1, D2: the first-IF strip (`rx2_blk_if1.inc`)

Four tuned circuits at 12.9 MHz and two emitter-coupled pairs. T1 is the
load of the first mixer. T1 and T2 are coupled through a shared 330 pF
capacitor. Pair 1 amplifies into T3, pair 2 into T4, and T4 feeds the second
mixer. Each tuned circuit is 3.3 µH ±5 % in the 1008 size (Q 16 assumed) with
about 40 pF. The strip does not set the bandwidth. Its job is to reject the
second image at 15.736 MHz.

Small-signal response, `rx2_d1_if1_ac.cir` (input: 1 µA into T1):

| | Nominal | Slow transistors |
|---|---|---|
| Peak | 12.99 MHz | 12.77 MHz |
| −3 dB bandwidth | 0.74 MHz (12.60 to 13.34 MHz) | |
| T1 current to voltage at mixer 2, at 12.9 MHz | 214 kΩ | 136 kΩ |
| Gain of pair 1 / pair 2 | 25.2 / 18.9 dB | |
| Second-image rejection | 40.5 dB | 40.3 dB |

Part tolerance, `rx2_d2_if1_tolerance.cir`, 300 runs each, ±5 % on every
inductor and capacitor:

| Transistor corner | Gain at 12.9 MHz against nominal | Second-image rejection |
|---|---|---|
| Nominal | −5.4 to +1.1 dB | 31.8 dB worst, 39.4 dB typical |
| Slow | −8.4 to −3.3 dB | 35.1 dB worst, 39.4 dB typical |

The Q of the inductor is not in its data sheet at 12.9 MHz. A run with Q 12
and Q 20 instead of 16 changed the gain by about ∓4 dB and the rejection to
37 and 45 dB.

Changes on the way:

- **The pairs use the S9018, not the MMBT3904.** A 3904 pair adds about 10 pF
  to a 46 pF tuned circuit, and that capacitance is not well controlled. With
  the slow-corner 3904 the strip sat 0.3 MHz low and lost 8 dB. The S9018
  adds about 2 pF and costs no fee at JLC.
- **T1 and T2 are coupled at the bottom, not at the top.** A shared capacitor
  to ground couples less above resonance, which is where the second image
  is. A small top capacitor favours the low side.
- **Light loading.** With 10 kΩ bias resistors the loaded Q follows the
  inductor. That gave 4 dB more rejection than 4.7 kΩ.
- **The pair currents set the level.** Pair 1 runs at 1 mA. Pair 2 runs at
  0.4 mA, so it cannot put more than about 0.6 V peak on the second mixer,
  however strong the signal is.
- **The 1008-size inductor** has a self-resonance of 110 MHz against 50 MHz
  for the 0805 part, and a slightly higher Q.

### H2: both IF strips with an FM signal (`rx2_h2_ifchain_fm.cir`)

FM current at 12.9 MHz into T1, audio out of the detector:

| Input current (peak) | Voltage at mixer 2 (peak) | Audio (peak) | THD |
|---|---|---|---|
| 3 nA | 0.64 mV | 12.6 mV | 1.8 % |
| 10 nA | 2.1 mV | 13.5 mV | 1.1 % |
| 100 nA | 21 mV | 13.5 mV | 0.28 % |
| 1 µA | 0.2 V (pair 2 limits) | 13.5 mV | 0.52 % |

Both strips, the second mixer and the detector together draw 7.5 to 9.0 mA.
About 35 mV of the 14.3 MHz LO appears on T4, coupled back through the
second mixer. It does no harm: mixed with itself it lands at DC and at
28.6 MHz.

### C1: the first mixer (`rx2_blk_mix1.inc`, `rx2_c1_mixer1.cir`)

Version 1's single-balanced mixer with three 2SC3356, re-biased for 3.3 V
(1.1 mA). 1 mV at 137.9 MHz at its input, LO at 125 MHz:

| LO drive (peak) | Gain to T1 | At mixer 2 | LO on T1 | LO at pair 1 |
|---|---|---|---|---|
| 0.2 V | 3.5 (10.9 dB) | 0.36 V | 19 mV | 2.4 mV |
| 0.4 V | 3.5 | 0.36 V | 21 mV | 2.7 mV |
| 0.6 V | 3.4 | 0.35 V | 22 mV | 2.8 mV |

- The gain is flat from 0.2 to 0.6 V of LO, so the LO level is not critical.
- With 1 mV at the mixer the second pair of the first IF is already close to
  its limit (0.36 V, 3.6 % distortion). For small signals the gain from the
  mixer input to the second mixer is about 54 dB.
- The LO leak that broke the second mixer is harmless here: T1 and T2
  reduce it to 2.7 mV before the first pair.

### A1, A2, A3: the front end (`rx2_blk_fe.inc`)

Antenna → tuned circuit R1 → LNA → tuned circuits R2 and R3 → mixer input.
All three tuned circuits use the 68 nH ±2 % inductor (Q about 35 at
137.9 MHz). The LNA is version 1's feedback amplifier with one 2SC3356 at
10 mA (470 Ω feedback, 2.2 Ω in the emitter). R2 and R3 are coupled through a
shared 330 pF capacitor. A BAV99 protects the antenna input.

The numbers include board strays: 0.5 pF on every tuned-circuit node, 0.7 pF
on the antenna node and the via inductance of the bypass capacitors (see M1).
Adding them needed one change: the capacitor of R3 went from 20 to 18 pF.

Small signal, `rx2_a1_frontend_ac.cir`. "Gain" is from the antenna's EMF to
the mixer input; from the voltage on a matched antenna it is 6 dB more.

| | Nominal | Slow transistor |
|---|---|---|
| Gain at 137.9 MHz / 137.1 MHz | 14.9 / 14.9 dB | 12.4 dB |
| Peak | 137.7 MHz | |
| −3 dB band | 134.2 to 141.0 MHz | |
| Image (112.1 MHz) | −41.6 dB | −39.1 dB |
| 100 MHz / 162.9 MHz | −57 / −31 dB | |
| Input match (return loss at 137.9 MHz) | 18.1 dB | 15.1 dB |
| Noise figure, `rx2_a3_frontend_noise.cir` | 4.4 dB | 5.2 dB |

Part tolerance, `rx2_a2_frontend_tolerance.cir`, 300 runs: inductors ±2 %,
capacitors ±5 %, small capacitors ±0.25 pF, strays ±0.3 pF.

| Transistor corner | Gain at 137.9 MHz | Image rejection | Return loss |
|---|---|---|---|
| Nominal | 10.8 to 15.4 dB, typical 14.1 | 35.2 dB worst, 40.8 typical | 15.5 dB typical, 7.7 worst |
| Slow | 8.1 to 13.1 dB, typical 11.7 | 31.7 dB worst, 38.5 typical | 13.9 dB typical, 7.0 worst |

So the image requirement (30 dB) holds in every run, and both satellite
channels (137.1 and 137.9 MHz) sit inside the passband.

### B1 to B4: the 125 MHz chain (`rx2_blk_lo1osc.inc`, `rx2_blk_lo1mul.inc`)

This block took the most work. The steps:

**First try.** A 25 MHz Colpitts oscillator, a buffer, a squarer pair and two
tuned circuits. It gave only 0.06 to 0.09 V at the mixer and its 150 MHz
content was only 22 to 29 dB down. Two causes:

1. The two tuned circuits peaked at 131 MHz and were 5.5 MHz wide.
2. A squarer makes only odd harmonics if it switches exactly at the zero
   crossings of a clean sine. The oscillator's output had 7.5 % of second
   harmonic. That shifts the crossings and makes 100 and 150 MHz. The rule
   that came out: the 150 MHz current is about 5 times the second-harmonic
   fraction of the drive.

**What the chain is now.**

- *Oscillator* (S9018, 47 pF and 100 pF, 1.4 mA). The crystal sits between
  the base and a separate node with 10 pF to ground. Only the crystal's own
  current reaches that node, and a crystal passes a clean sine: 0.5 % second
  harmonic instead of 7.5 %. A BAV99 clamps the node at about ±0.52 V, so the
  amplitude does not depend on the crystal or the transistor.
- *Follower* (S9018, 3 mA) so the squarer does not load the crystal.
- *Squarer* (two 2SC3356). Its tail is a current source (a third 2SC3356,
  8 mA), so both halves carry the same current. Both bases get the same DC
  through equal 680 Ω resistors. The output is taken from the transistor
  whose base is grounded for AC: its current pulse is flat-topped.
- *Two tuned circuits* (68 nH with 18 pF + 6.8 pF and 15 pF + 6.8 pF, coupled
  through a shared 100 pF). The first is left undamped, the second carries a
  680 Ω resistor and the mixer. Together they are 11.8 MHz wide (119.6 to
  131.4 MHz), so ±2 % inductors and ±5 % capacitors cannot move them off
  125 MHz.

**How it is measured (B2, `rx2_b2_lo1_chain.cir`).** As in E2, the crystal's
resonant branch is replaced by a 25 MHz current source. The deck steps its
amplitude and computes the resistance the oscillator can sustain; the real
oscillator settles where that equals the crystal's resistance. The same run
gives the LO at the mixer and its harmonics.

**Cross-check (B1, `rx2_b1_lo1_osc.cir`).** A start-up run with the crystal as
a real resonator (5 ms, 307 s of computing): the 25 MHz amplitude settles at
1.037 V peak-to-peak after 2 ms. The fast method predicts 1.04 V.

Result with a 40 Ω crystal:

| | Value |
|---|---|
| 25 MHz at the squarer | 0.54 V peak, second harmonic 0.5 % |
| LO at the first mixer (125 MHz) | 0.35 V peak |
| 100 MHz / 150 MHz | −53 / −54 dBc |
| 75 MHz / 175 MHz | about −40 / −34 dBc |
| Power in the crystal | 56 µW (42 µW at 25 Ω, 62 µW at 50 Ω) |
| Start-up margin | 4.4 at 40 Ω |
| Supply current of the chain | 12.6 mA |

Against the conditions (40 Ω crystal):

| Condition | LO at the mixer (peak) | Power in the crystal |
|---|---|---|
| Nominal | 0.35 V | 56 µW |
| Slow, low-gain transistors | 0.32 V | 48 µW |
| Rail 3.0 V / 3.6 V | 0.33 / 0.37 V | 48 / 64 µW |
| −10 °C / 60 °C | 0.45 / 0.27 V | 66 / 48 µW |

Part tolerance, B4 (`rx2_b4_lo1_tolerance.cir`), 100 runs: inductors ±2 %,
capacitors ±5 %, strays ±0.3 pF, and up to ±10 mV of offset between the two
squarer transistors (two transistors never match exactly, and an offset
shifts the switching instants).

| | Worst | Typical | Best |
|---|---|---|---|
| LO at the mixer (peak) | 0.28 V | 0.35 V | 0.38 V |
| 150 MHz | −39.7 dBc | −47 dBc | −60 dBc |
| 100 MHz | −46 dBc | −51 dBc | −55 dBc |
| 175 MHz / 75 MHz | −31 / −37 dBc | −33 / −40 dBc | |

The first mixer's gain is flat from 0.2 to 0.6 V of LO (C1), so every case
above is inside that window.

### I1, I2: the audio chain (`rx2_blk_audio.inc`)

Detector output → PNP follower → two identical low-pass sections → gain
stage → ESP32 ADC pin.

- The three followers alternate PNP, NPN, PNP. Each one shifts the DC level
  by one base-emitter voltage, up, down and up again, so the chain needs no
  coupling capacitor until the gain stage.
- Each low-pass section is a Sallen-Key stage around a follower: 15 kΩ,
  5.6 kΩ, 4.7 nF and 1 nF (8 kHz, Q about 0.8). Together with the detector's
  own 12.5 kHz corner they give a flat band and a steep fall above it.
- The gain stage (one MMBT3904, gain about 20) is AC-coupled on both sides,
  so its own DC drift never reaches the ADC. The level at the ADC pin comes
  from a divider on the DevKitC's 3V3 pin (82 kΩ / 51 kΩ, 1.265 V).

A lesson from the first try. A follower's gain is a little below 1 (0.91 to
0.95 here). A sharp Sallen-Key section (Q 1.3 to 1.7) needs a gain of exactly
1: with 0.91 its Q fell to 0.6 and the passband drooped by 2 dB. Two equal
gentle sections do not have this problem.

Small signal, `rx2_i1_audio_ac.cir` (from the detector's audio voltage to the
ADC pin):

| | Value |
|---|---|
| Gain at 2400 Hz | 25.5 dB (18.8 times) |
| Flatness, 320 to 4480 Hz | 25.1 to 25.7 dB (±0.3 dB) |
| −3 dB points | 55 Hz and 7.4 kHz |
| 22 kHz | 42 dB below the passband |
| 39.6 kHz (aliases onto 4.5 kHz at 44.1 kHz sampling) | 70 dB below the passband |

With the 2400 Hz tone, `rx2_i2_audio_tran.cir`:

| Detector audio (peak) | At the ADC (peak-to-peak) | Gain | THD |
|---|---|---|---|
| 6.5 mV (half deviation) | 0.24 V | 18.8 | 0.7 % |
| 13.1 mV (full deviation) | 0.49 V | 18.8 | 1.4 % |
| 26 mV (twice) | 0.98 V | 18.7 | 2.9 % |
| 52 mV (four times) | 1.8 V | 17.9 | 5.4 % |

The gain column is what matters for a picture: brightness is the amplitude of
the tone, and the amplitude comes through in proportion up to twice the full
level. The ADC pin rests at 1.266 V. The chain draws 1.7 mA through its own
100 Ω / 100 µF supply filter.

### H3: the picture test (`rx2_h3_apt_envelope.cir`)

An APT picture is the 2400 Hz tone with its amplitude following the image.
Until here every FM test used a plain tone at full strength. This run uses a
picture-like signal: the tone is amplitude-modulated to 80 % depth by a
"video" sine, and that signal frequency-modulates a 12.9 MHz carrier (peak
deviation 17 kHz) into the second mixer. At the detector output the three
lines of the signal are measured: the tone and its two side lines. For a
perfect receiver each side line is 0.400 of the tone.

| Video frequency | Lower side line | Upper side line | Expected from the detector's own 470 pF |
|---|---|---|---|
| 1040 Hz (the sync frequency) | 0.402 (at 1360 Hz) | 0.391 (at 3440 Hz) | 0.405 / 0.393 |
| 2080 Hz (the finest detail) | 0.413 (at 320 Hz) | 0.383 (at 4480 Hz) | 0.407 / 0.384 |

So the mixer, the second IF, the limiter and the detector pass the picture
content unchanged; the small differences are the detector's output
capacitor, which the audio chain's design already counts in. After the audio
chain (I1), the depth of the modulation at the ADC is right within 1.5 %,
up to the finest detail.

### J1, J2, K1: the supply (`rx2_blk_reg.inc`)

The receiver has no trimmers, so its levels must not move with the supply.
The DevKitC's 5V pin follows the USB voltage. A discrete regulator needs a
reference, and a base-emitter voltage scaled up to 3.3 V would drift by
±10 % over −10 to 60 °C.

The DevKitC already has a good 3.3 V regulator, so its 3V3 pin is used as the
reference only, filtered by 2.2 kΩ and 10 µF. The power comes from the 5V pin
through a PNP pass transistor. An NPN pair compares the rail with the
reference. A 10 Ω resistor and one more PNP limit the current.

| | Value |
|---|---|
| Rail | 3.31 V |
| Change for 4.1 to 5.2 V at the 5V pin | 0.3 mV |
| Change for 15 mA more load | −8 mV, no overshoot |
| Lowest input that still regulates | 3.85 V |
| Ripple from the 5V pin at 2400 Hz | −77 dB |
| Ripple from the 3V3 pin at 2400 Hz | −51 dB |
| Start | 3.2 V after 75 ms, no overshoot |
| Short circuit | 66 mA |

The whole receiver through the regulator, `rx2_k1_powerup.cir`: 35.9 mA from
the 5V pin, rail 3.315 V, ADC pin at 1.265 V. The LNA takes 9.9 mA and the
125 MHz chain 12.6 mA; these two are 60 % of the total.

A clone DevKitC that shows only 3.3 V on its 5V pin cannot feed this
regulator. A genuine board is needed, as for version 1.

### M1: board strays and stability (`rx2_m1_vhf_stability.cir`)

The VHF blocks now contain estimates of what the board adds: 0.5 pF on every
tuned-circuit node, 0.7 nH of via inductance in series with the bypass
capacitors that matter, 1 nH in series with the shared coupling capacitors.

They exposed a real fault. A 1 nF and a 100 nF capacitor in parallel on the
same node, each with its own via, form a resonance at about 135 MHz: the
100 nF is already an inductor there and the 1 nF is still a capacitor. On the
LNA's emitter this put a 5 dB dip in the middle of the passband. On the
squarer's supply feed it moved the 125 MHz tuned circuit by 2.7 MHz.

Rules that follow, for the schematic and the board:

- Never a small and a large capacitor in parallel on the same VHF node.
- Where the impedance matters (the LNA's emitter): two equal 1 nF capacitors.
- Supply feeds: one 100 nF after the feed resistor.
- A bypassed base gets one capacitor plus a damped branch (47 Ω + 1 nF).
- No resistor in series with the base of a transistor whose collector
  carries a tuned circuit. 47 Ω there added about 3 pF to the 125 MHz tuned
  circuit, and that capacitance changes with the bias.

Stability check. Front end, first mixer and 125 MHz chain at their DC
operating point; short current pulses hit six sensitive nodes; trapezoidal
integration with 5 ps steps so the simulator damps nothing. Every node rings
down (for example the LNA collector: 456 µV, 2.6 µV, 0 in three successive
windows). No parasitic oscillation. The damping parts are a 100 Ω base
stopper on the follower, 33 Ω between follower and squarer, and snubbers on
the bypassed bases.

### L1: unwanted responses (`rx2_l1_spurs.cir`)

Antenna to the second mixer's input, with the real 125 MHz chain as the LO.
A carrier is put on the antenna at one frequency per run, and the 12.9 MHz
voltage at the second mixer is measured. The wanted signal (137.9 MHz)
arrives with a gain of 67.7 dB from the antenna's EMF (73.7 dB from the
voltage on a matched antenna). Everything else, relative to that:

| Antenna frequency | How it gets to 12.9 MHz | Response |
|---|---|---|
| 112.1 MHz | the image | −41 dB |
| 137.1 MHz (the other satellite channel) | the LO's 150 MHz content | −68 dB |
| 162.9 MHz | the LO's 150 MHz content | −87 dB |
| 112.9 / 87.1 MHz | the LO's 100 MHz content | −91 / −106 dB |
| 162.1 / 187.9 MHz | the LO's 175 MHz content | −69 / −82 dB |
| 62.1 / 87.9 MHz | the LO's 75 MHz content | −113 / −102 dB |
| 131.45 MHz | half-IF response | −67 dB |
| 12.9 MHz straight in | IF feedthrough | below −120 dB |

- The floor of this method is about −128 dB (a run at 95 MHz, where nothing
  should come through).
- The 137.1 MHz figure is for a well-matched squarer. In the tolerance run
  (B4) the 150 MHz content is up to 14 dB above nominal, so the worst case
  is about −54 dB.
- The second image (140.74 MHz at the antenna) is not in this run, because
  it is rejected after this point: 40.5 dB by the first IF (D1) plus about
  2.5 dB by the front end.
- The 12.9 MHz component is measured by correlation with a sine and a
  cosine. Inside a `.meas`, `sin(2*pi*f*time)` gives wrong numbers, so the
  deck builds the two products in behavioural sources. A separate
  calculation from the saved waveform agrees within 1 dB.

Gain and noise, from the antenna to the limiter:

| | Value |
|---|---|
| Antenna EMF → first mixer input | 14.9 dB |
| First mixer input → second mixer input | 52.8 dB |
| Noise figure | 4.4 dB |
| Receiver noise in the 132 kHz second IF, referred to the antenna | −118 dBm |
| That noise at the second mixer | about 1.3 mV rms |
| The limiter is clean above | about 1 mV at the second mixer (H1) |

So the receiver's own noise already saturates the limiter, as intended: the
audio level does not depend on the signal level.

### L2: the whole receiver with FM (`rx2_l2_whole_fm.cir`)

Everything from the antenna to the detector output in one run: front end,
both mixers with their real oscillator waveforms (both crystal currents
forced), both IF strips, limiter and detector. The input is a 137.9 MHz
carrier with ±17 kHz FM at 2400 Hz. These are the longest runs in the project:
LTspice needs steps of about 50 ps for 1 ms of signal, and a weak-signal run
takes over an hour.

| At the antenna input | Detector DC | Audio (peak) | Distortion |
|---|---|---|---|
| −121 dBm (0.2 µV) | 1.470 V | 12.8 mV | 4.6 % |
| −101 dBm (2 µV) | 1.472 V | 13.2 mV | 0.6 % |
| −27 dBm (10 mV) | 1.467 V | 12.9 mV | 0.6 % |

- The audio level is the same within 0.3 dB over a 94 dB range of input
  level. That is what the limiter is for, and it matters for the test: the
  attenuator setting will not change the picture's brightness.
- At −121 dBm the signal at the second mixer is about 1.4 mV, right at the
  limiter's knee, so the distortion is higher there (compare H1). A run like
  this has no noise in it: it shows gain, limiting and distortion, not
  sensitivity. In the real receiver its own noise (−118 dBm in the IF
  bandwidth) decides how weak a signal still gives a clean picture.
- At −27 dBm the first IF limits hard (1.4 V peak-to-peak at the second
  mixer) and the picture signal still comes through.
- The distortion figures are after removing a slow drift of the DC level
  (0.5 to 1.9 mV per cycle), which is the receiver still settling after
  switch-on in these short runs. LTspice's own figure counts that drift as
  distortion (3.8 % at −27 dBm).
- The detector's DC level is 1.47 V here against 1.50 to 1.52 V in the
  IF-only runs, because the 125 MHz chain takes a little current from the
  shared bias reference.

### N1: too much signal (`rx2_n1_overload.cir`)

The Pluto can give about +7 dBm. This run puts a 137.9 MHz carrier straight
into the antenna input, as if attenuators were missing.

| At the antenna input | −27 dBm | −7 dBm | +7 dBm | Limit of the 2SC3356 |
|---|---|---|---|---|
| Reverse base-emitter voltage of the LNA | none | none | 1.1 V | 3 V |
| Peak collector current of the LNA | 11 mA | 25 mA | 42 mA | 100 mA |
| Power in the LNA transistor | 16 mW | 13 mW | 5 mW | 200 mW |
| Peak current in the protection diodes | 0.02 mA | 0.2 mA | 2.2 mA | 200 mA |
| Voltage at the mixer input (peak) | 0.15 V | 0.76 V | 1.06 V | |

Nothing is over its limit, even at full Pluto power with no attenuator. The
receiver is of course overdriven there; for a clean picture the input should
be between about −100 and −30 dBm (see L2).

## After the independent check (2026-11-13)

Two reviewers (AI agents, report only) went through every block and every
deck. They found no blocker, three major risks and about ten smaller points.
Each finding was reproduced by simulation before anything was changed. This
section records what changed. **Where an earlier section gives a different
value, this section is the current one.** Every deck was re-run on the final
blocks; the whole-chain results are under "The whole chain on the final
blocks" below.

### The bias reference: two references instead of two diodes

The finding: every stage current hung on the forward voltage of two 1N4148W.
With each diode 63 mV off, the detector output went from 1.52 V to 0.81 V or
2.25 V (reproduced).

The first idea was one MMBT3904 connected as a diode on top of a resistor.
The junction drops then cancel and the stage currents stay constant. But the
detector then drifted by +0.63 % per °C (1.27 V at −10 °C, 2.00 V at 60 °C).
The cause: the charge pump loses two junction drops per cycle, in its
Schottky diode and in its PNP, and those drops fall as it warms up. The old
diodes drifted the other way and were hiding that.

So there are two references now (`rx2_blk_bias.inc`):

- `vb`, 1.17 V: 1.1 kΩ from the rail, one MMBT3904 as a diode, 270 Ω. For
  every pair, both mixers and the squarer's current source.
- `vbd`, 1.27 V: 4.7 kΩ from the rail, one MMBT3904 and one MMBT3906 as
  diodes in series. Only for the pump driver (pair C, `Rec` 390 Ω, `Rcc`
  1.1 kΩ). It falls with temperature as the pump's losses do.

| | Before | Now |
|---|---|---|
| Stage currents, −10 to 60 °C (`rx2_o1_bias_dc.cir`) | ±13 % | ±3.5 %; squarer current flat |
| Detector DC at −10 / 27 / 60 °C | 1.30 to 1.78 V over all corners | 1.284 / 1.271 / 1.259 V |
| Audio at −10 / 27 / 60 °C | 15.9 / 13.8 / 12.1 mV | 10.7 / 10.4 / 10.1 mV |
| Reference junctions off by ±63 mV | detector −47 % / +48 % | detector ∓0.6 % (all MMBT3904 shifted) |
| All MMBT3906, or the BAS70, off by ±63 mV | not measured (same pump) | ±10.5 % and ∓10.7 % (the pump's own two drops) |
| Rail 3.0 to 3.6 V | detector ±5 % | detector ±3 %, stage currents ±11 % |

- The stage currents now follow the rail. The regulator holds the rail.
- A shift of all MMBT3904 against the S9018 and 2SC3356 (±63 mV) moves the
  first-IF pairs, the first mixer and the squarer by about ±10 %. None of
  those levels is critical.
- The detector now sits at 1.27 V with 10.4 mV peak of audio (it was 1.52 V
  and 13.4 mV). That leaves 0.8 V below the PNP's base. The audio stage
  makes up the difference.

### The squarer: a damping resistor

The finding: with the lead inductance of a SOT-23 package the squarer can
oscillate near 1.7 GHz. The stability deck M1 used bare transistor models in
the balanced state, the most stable case.

M1 now has a package model around all nine VHF transistors (leads 1.3, 1.3
and 0.5 nH, pin capacitances 0.08, 0.16 and 0.07 pF; estimates, not vendor
data) and runs the squarer in three states: one side on, balanced, the other
side on. At the nominal estimate everything rings down. With 1 pF on the
emitter node `eq`, or the leads 1.5 times longer, or twice the pin
capacitance, the squarer oscillated at full amplitude (0.5 to 1 V
peak-to-peak).

The fix: 47 Ω (`Rqs`) between `eq` and the current source's collector, and
the base divider raised (`Rqb2` 4.7 kΩ) to give the headroom back. All those
cases now ring down, also with twice the lead inductance and with the slow
models. Only 2 pF on `eq` still oscillates, so `eq` must stay small on the
board. The LO level is unchanged.

### The IF strips: stray coupling from the output back to the input

The finding: the 12.9 MHz strip oscillated with 0.1 pF from its output (T4)
back to T2, or with a magnetic coupling factor of 0.002 between the
inductors of T2 and T4. New decks: `rx2_p1_if1_stray_kick.cir` and
`rx2_p2_if2_stray_kick.cir`. A pulse starts a ring-down; one stray coupling
is added per run.

| 12.9 MHz strip | As found (pair 1 at 1 mA) | Now (`Rei1` 1.2 kΩ, 0.4 mA) |
|---|---|---|
| Stray capacitance T4 → T2 | 0.05 pF stable, 0.07 pF oscillates | 0.1 pF stable, 0.15 pF oscillates |
| Coupling factor, inductors of T2 and T4 | 0.003 stable, 0.005 oscillates | 0.002 stable (both signs), 0.005 oscillates with one sign |
| Stray capacitance T4 → T3 (across pair 2) | 1 pF oscillates | 0.5 pF stable, 1 pF oscillates |

| 1.418 MHz strip | Threshold |
|---|---|
| Stray capacitance from the pump driver's output `c2` to T5 | 0.004 pF stable, 0.005 pF on the edge, 0.007 pF oscillates |
| Stray capacitance T6 → T5 | 1 pF stable, 2 pF oscillates |
| Coupling factor, inductors of T5 and T6 | 0.007 stable (both signs), 0.01 oscillates |

- Pair 1 of the first IF lost 4.5 dB (128 kΩ from T1 current to the second
  mixer, was 214 kΩ). The second mixer got it back: its emitter resistors
  are 100 Ω instead of 220 Ω, so its gain is 19.2 dB instead of 14.9 dB. The
  second mixer sits in neither strip's loop, so the gain is safe there.
- The 1.418 MHz strip has 73 dB from T5 to the 1.65 V square wave at `c2`.
  That is why 0.005 pF is enough. The board must keep `c2` away from T5 (see
  the layout rules).

### Tuned circuits re-centred with the board's strays

| Block | Change | Result |
|---|---|---|
| Front end | 1.5 nH from each inductor's grounded pad to the ground plane is now in the block; `Cr1b` 6 pF, `Cr2a` 6.8 pF, `Cr2b` 12 pF; the two redundant 1 nF capacitors are gone | peak 137.5 MHz, −3 dB 133.7 to 141.6 MHz, 13.3 dB from the antenna's EMF at both channels, image −37.8 dB, return loss 17 dB, noise figure 4.7 dB (slow 5.8 dB); with 0.7 or 2.5 nH instead: 13.2 / 13.1 dB |
| First IF | 0.5 pF of stray on each tuned circuit | peak 12.935 MHz, 0.73 MHz wide, second image −41.8 dB |
| Second IF | the second mixer is now connected in F1 to F3 (its collectors pulled the pair 18 kHz low); 1 pF of stray per tuned circuit; `C5b` 4.7 pF, `C6b` 6.8 pF | T5 at 1.4185 MHz, the pair at 1.417 MHz, 131 kHz wide, T5 6.5 kΩ |

Without re-tuning, the front end's peak had fallen from 137.6 to 136.2 MHz.
Centring it cost 1.6 dB of gain and 3.8 dB of image rejection.

Part tolerance. The tolerance decks now have two extra runs in which every
part sits at the same end of its tolerance, as when a whole reel is off one
way (the blocks call `tolv()` and `strv()`; the deck parameter `sd` chooses
random or same-way).

| Deck | 300 random runs | All parts low / all parts high |
|---|---|---|
| A2 front end, gain at 137.9 MHz (nominal 13.3 dB) | at least 9.3 dB, typical 12.8 dB; image at least 32.0 dB | 8.5 dB / 7.9 dB; image 38.3 / 26.6 dB |
| D2 first IF, loss at 12.9 MHz | at most 5.0 dB, typical 1.5 dB; second image at least 35.6 dB | 5.4 dB / 8.7 dB; second image 29.7 / 39.9 dB |
| F3 second IF, loss at the signal | at most 2.1 dB (3.4 dB at ±21 kHz) | 3.0 dB / 3.0 dB (4.8 dB at ±21 kHz) |

The same-way corners cost gain, not function: the limiter follows, and the
level at the detector does not change.

### The 125 MHz chain, measured after it has settled

The squarer's bases settle with 7 µs (10 nF with 680 Ω), and the 100 and
150 MHz content depends on that balance. B2 measured at 2 to 4 µs. It now
runs 42 µs and measures the last 2 µs. The offset between the two squarer
transistors is a block parameter (`voq`, 0 nominally), so B4 runs as stored.

| | Nominal | Rail 3.0 V / 3.6 V | Slow transistors |
|---|---|---|---|
| LO at the mixer (peak) | 0.363 V | 0.305 / 0.419 V | 0.330 V |
| 100 MHz | −52.3 dBc | −51 / −53 dBc | −50 dBc |
| 150 MHz | −48.9 dBc | −46 / −51 dBc | −47 dBc |

The crystal gets 56 µW with a 40 Ω crystal. The reviewers found up to 75 µW
at 3.6 V and −10 °C, and 58 to 67 µW in the 14.318 MHz crystal with the real
mixer as its load. Both crystals' drive-level ratings must be confirmed
before ordering. *(Confirmed on 2026-11-14: both are rated 10 to 200 µW,
see [`PARTS.md`](PARTS.md).)*

### Audio stage and ADC pin

- The gain stage is re-biased (`Rg1` 27 kΩ, `Rgc` 3 kΩ, `Rge1` 47 Ω, `Rge2`
  1.5 kΩ, `Cge` 100 µF): collector at 1.68 V nominally and 1.61 to 1.83 V
  from 3.0 V / −10 °C to 3.6 V / 60 °C, slow transistors included (it was
  0.98 to 1.38 V). Twice the full level compresses by 2 %.
- Gain from the detector to the ADC pin 27.5 dB: 0.49 V peak-to-peak for
  the 10.4 mV of full deviation. 0.44 V and 0.53 V at those two corners,
  0.34 V with slow transistors at 3.0 V / −10 °C.
- Distortion at full level 2.4 % (it was 1.4 %; the stage has more gain
  now). Its harmonics lie above the picture band. A two-transistor feedback
  stage would lower it; it is not needed for a picture.
- Relative to 2400 Hz: −0.3 dB at 320 Hz, +0.2 dB at 4480 Hz; −3 dB at
  7.4 kHz; 22 kHz 42 dB down, 39.6 kHz 69 dB down.
- The rest level at the ADC pin (1.20 V) now comes from the filtered audio
  supply, not from the 3V3 pin. Ripple on the 3V3 pin reaches the ADC pin
  90 dB down at 2400 Hz and 55 dB down at 320 Hz (it was 26 and 23 dB).
- At power-up the ADC pin peaks at 1.57 V and is at its rest level within
  0.4 s (K1).

### The supply

Unchanged. A dead short on the rail puts 66 mA × 4.0 V = 0.27 W into the
SOT-23 pass transistor, about 100 °C above ambient, inside its 150 °C limit.
A fold-back limit was considered and left out: it would need the start-up
peak (57 mA) checked again. The whole receiver now draws 37.1 mA.

### Numbers on the final blocks

| Deck | Result |
|---|---|
| C1 | first mixer gain into T1 3.5; from the mixer input to the second mixer 242 (47.7 dB) |
| E1 | second mixer 9.1 (19.2 dB) at 0.18 V of LO; 1.8 mV of LO left on T5 |
| F2 | audio 8.7 mV / 21 % at 0.65 mV on T5; 10.3 mV / 2.6 % at 1.9 mV; 10.9 mV / 1.8 % at 6.5 mV; 10.3 mV / 0.44 % at 66 mV; 10.2 mV / 0.50 % at 0.71 V |
| G1 | 1.230 V and 10.0 mV at 0.3 V of drive, THD 0.29 %; 1.192 V / 9.6 mV at 3.0 V; 1.263 V / 10.4 mV at 3.6 V; static slope 0.60 mV per kHz |
| H1 | at the second mixer: 0.1 mV → 9.9 mV / 8.9 %; 0.3 mV → 10.6 mV / 2.1 %; 1 mV → 11.0 mV / 1.4 %; 10 mV → 10.2 mV / 0.39 % |
| H2 | current into T1: 3 nA → 10.5 mV / 2.3 %; 10 nA → 11.1 mV / 1.2 %; 100 nA → 10.2 mV / 0.39 %; 1 µA → 10.2 mV / 0.47 % |
| H3 | side lines 0.391 and 0.402 at 1040 Hz, 0.383 and 0.413 at 2080 Hz: unchanged |
| K1 | 3.315 V, 37.1 mA, start-up peak 56.9 mA |
| N1 | at +7 dBm: reverse base-emitter voltage 1.15 V, peak current 47 mA |

With more gain in the second mixer the limiter's knee moved down: 0.3 mV at
the second mixer now gives 2.1 % distortion (it was 4.2 %).

### The whole chain on the final blocks

**B1, real crystal start-up.** 1.034 V peak-to-peak at the squarer's input
from 2 ms on. The fast method with the forced crystal current gives 1.036 V.

**B4, the 125 MHz chain with tolerances.** 60 runs with random part values
and a random offset of up to ±10 mV between the squarer transistors, plus
two runs with every part off the same way and the full 10 mV. Measured after
the squarer has settled.

| | Lowest | Typical | Highest |
|---|---|---|---|
| LO at the mixer (peak) | 0.284 V | 0.356 V | 0.387 V |
| 100 MHz | | −49.0 dBc | −40.5 dBc |
| 150 MHz | | −42.8 dBc | −31.9 dBc |

These are worse than the earlier B4 figures (150 MHz typically −47 dBc, at
worst −39.7 dBc). The earlier runs measured before the squarer had settled.

**L1, unwanted responses.** The wanted signal now arrives at the second
mixer with 60.7 dB from the antenna's EMF. It was 67.7 dB: 1.6 dB less in the
front end, 4.5 dB less in the first IF, and 0.9 dB that is not traced. After
this point the second mixer adds 4.3 dB more than before.

| Antenna frequency | How it gets to 12.9 MHz | Response |
|---|---|---|
| 112.1 MHz | the image | −36.6 dB |
| 137.1 MHz (the other satellite channel) | the LO's 150 MHz content | −55.0 dB |
| 162.9 MHz | the LO's 150 MHz content | −83 dB |
| 112.9 / 87.1 MHz | the LO's 100 MHz content | −85 / −106 dB |
| 162.1 / 187.9 MHz | the LO's 175 MHz content | −66 / −79 dB |
| 62.1 / 87.9 MHz | the LO's 75 MHz content | −113 / −104 dB |
| 131.45 MHz, 100 µV at the antenna | half-IF response | −71 dB |
| 12.9 MHz straight in | IF feedthrough | −121 dB |
| 95 MHz (nothing expected) | the floor of the method | −124 dB |

- The 137.1 MHz figure is for perfectly matched squarer transistors. With
  B4's typical mismatch it is about −49 dB, with the worst about −38 dB. It
  is 13 dB worse than the earlier −68 dB; the settled measurement of the LO
  explains 5 dB of that, the rest is not tracked down. It does not matter
  for the bench test (one signal). On a real antenna it only matters if both
  channels are in use at once.

Gain and noise, from the antenna to the limiter:

| | Value |
|---|---|
| Antenna EMF → first mixer input | 13.3 dB |
| First mixer input → second mixer input | 47.7 dB |
| Noise figure | 4.7 dB |
| Receiver noise in the 131 kHz second IF, referred to the antenna | −118 dBm |
| That noise at the second mixer | about 0.6 mV rms |
| The limiter is clean above | about 0.3 mV at the second mixer (H1) |

So the receiver's own noise still saturates the limiter, with more margin
than before: the gain that left the first IF came back after the second
mixer's input.

**L2, the whole receiver with FM.**

| At the antenna input | Detector DC | Audio (peak) | Distortion |
|---|---|---|---|
| −121 dBm (0.2 µV) | 1.266 V | 10.9 mV | 4.8 % |
| −101 dBm (2 µV) | 1.273 V | 10.5 mV | 1.0 % |
| −27 dBm (10 mV) | 1.268 V | 10.2 mV | 1.2 % |

- The audio level is the same within 0.6 dB over 94 dB of input level.
- The distortion figures are LTspice's own, over two cycles. They include a
  small settling drift (0.4 to 0.5 mV per cycle), which accounts for most of
  the 1 %. The back half alone, in a longer run, gives 0.39 % (H1).
- At −121 dBm the signal at the second mixer is about 0.6 mV, near the
  limiter's knee. As before, these runs have no noise in them.
- A trap in the post-processing: a Fourier window that is 0.004 % short of
  a whole number of cycles leaks 0.1 mV of the 1.27 V DC level into every
  harmonic. It looked like 3 % distortion.

### Layout rules that came out of this

1. Each IF strip in a straight line: input at one end, output at the other.
   Nothing from the output side runs back along the strip.
2. First IF: T2 and T4 at least 15 to 20 mm apart, neighbouring inductors
   at right angles, ground pour and vias between the stages, the input and
   the output of each pair kept apart.
3. Second IF: the pump driver's output `c2` is the dangerous node. T5 and
   its inductor go to one end, the pump driver and the detector to the
   other, 25 mm or more away, with solid ground under and between. `c2` and
   the pump capacitor's other node as short as possible. The two 100 µH
   inductors apart and at right angles.
4. Squarer: the emitter node (two emitters and the 47 Ω resistor) as small
   as possible, well under 1 pF.
5. The 1 nF capacitor at the ADC pin sits at the DevKitC pin, away from T6
   and `c2`. At 44.1 kHz sampling the 1.418 MHz IF would alias to about
   7 kHz.
6. A spare, unpopulated capacitor pad on each front-end tuned circuit.

### Notes for the firmware

- Sample at 44.1 kHz with the ADC's continuous (DMA) mode. `analogRead` in a
  loop is too slow, and at 11 kHz the audio filter gives no protection
  against aliasing.
- The 6 dB attenuation setting (about 0.15 to 1.75 V) fits the signal (1.20 V
  ± 0.25 V) and gives finer steps than the 11 dB setting.

### Corrections to earlier sections

- **Weakest usable input.** L2 has no noise in it, so "−121 dBm" there is
  not a sensitivity. A run with the receiver's own noise added (by a
  reviewer, on the circuit before these changes, one noise sample) gave:
  tone at 86 % with 2 dB of signal-to-noise at −115 dBm, full level with
  12 dB at −112 dBm, clean from −109 dBm. So the weakest usable input is
  about −112 dBm (0.56 µV), and about 3 dB worse in the slow corner. (A later estimate that also counts
  the noise of the first mixer and the first IF comes out about 3 dB worse:
  see "Reviews before the order".)
- **Half-IF response (L1).** It is a second-order response, so it depends on
  the level: −72 dB for 100 µV at the antenna, −58 dB for 1 mV.
- **H2.** The "voltage at mixer 2" column was calculated, not measured, and
  "0.2 V (pair 2 limits)" was wrong: that point is still linear; the limit
  is 0.7 V peak. The 14.3 MHz LO on T4 measures 34 mV peak now.
- **Picture depth (H3 with I1).** The earlier "within 1.5 %" was 1.9 % for
  the audio chain of that time. With the present chain the depth at 2080 Hz
  is 1.4 % low (side lines 0.398 and 0.391 of the tone, ideal 0.400).
- **G1** now includes the blocks instead of its own copy of the detector.

### What this round taught

- A flat bias is not always the right bias: the old diodes' drift was
  cancelling the charge pump's drift. Check what a "fault" is compensating
  before removing it.
- A kick test with bare transistor models in one operating state proves
  little. Add the package and try every state.
- Gain at one frequency needs a feedback budget in femtofarads, not just a
  gain budget in decibels.
- Monte-Carlo runs with independent draws miss the case where a whole reel
  is off one way.
- LTspice: a `.meas` window that ends exactly at the stop time picks up the
  first point of the next `.step`. It looked like a 0.2 V oscillation.
- LTspice does not allow a `.func` named `mc` or `flat`; tolerance functions
  need their own names.

## Found while laying out the board (2026-11-14)

Two questions came up when I had to decide where the blocks go on the board.
Both were answered with a simulation. The circuit is not changed; the answers
became layout rules 7 and 8. The board itself is described in
[`../pcb_v2/README.md`](../pcb_v2/README.md).

### The second IF can lock itself through the first IF

`rx2_q1_harmonic_lock.cir`

The pump driver makes a 1.65 V square wave at the second IF (node `c2`). A
square wave has odd harmonics, and two numbers happen to fit:

- the second oscillator divided by ten, 14.31818 / 10 = 1.431818 MHz, lies
  inside the second-IF passband (1.35 to 1.48 MHz);
- nine times that, 12.886 MHz, lies inside the first-IF passband.

So if a little of the ninth harmonic of `c2` reaches the first IF, the first
IF amplifies it, mixer 2 turns it back into 1.431818 MHz, and the limiter
keeps running on its own signal. The earlier stray tests (P1, P2) only looked
inside each strip, so they could not see this path from one strip to the
other.

The deck has both IF strips, mixer 2 and the detector. A burst at 12.886 MHz
starts the limiter, then the input is switched off. A stray capacitor from
`c2` to one node of the first IF decides whether the square wave dies away or
stays:

| Stray capacitor from `c2` to | Dies away with | Stays with |
|---|---|---|
| `t1` (first tuned circuit) | 0.0002 pF | 0.0003 pF |
| `t2` | 0.0003 pF | 0.001 pF |
| `t3` | 0.001 pF | 0.003 pF |
| `m2in` (last tuned circuit) | 0.01 pF | 0.03 pF |

For comparison, rule 3 below was written for 0.005 pF from `c2` to T5. The
path into the start of the first IF is about twenty times more sensitive.

What the test does not show: the simulation has no noise. On the real board
the limiter always runs on noise, and a leak would have to be stronger than
that noise before it takes over. So the numbers in the table are on the safe
side, but I do not know by how much.

What I did about it: the first IF is a column down the east edge of the
board, and the second IF is a row that runs west from mixer 2. Measured on
the finished board from copper to copper, `c2` ends up 52.6 mm from the
nearest tuned node of the first IF (the track from mixer 1 to T1), with the
ground plane under everything and ground pour and vias between. (An earlier
version of this log said 60 mm or more. That was the distance between the
parts, not between the copper.) A rough estimate for two small conductors on
a grounded board, far apart compared with its thickness, is
C1 · C2 · h² / (2π ε0 εr² d³). With 0.6 pF and 1.5 pF to ground, h = 1.6 mm
and d = 52.6 mm it gives about 0.000015 pF, a tenth of the 0.0002 pF that
still dies away. It is an estimate, not a measurement. If the receiver still
shows a steady carrier with no antenna signal, this is the first thing to
look at.

### The squarer's first transistor needs its bypass capacitor close by

`rx2_m1_vhf_stability.cir`, run with extra layout inductances

On one copper layer the two squarer transistors can be placed in two ways.
Either the emitters sit next to each other and the collectors point to
opposite sides, or both collectors point the same way and the emitter link
has to go around a base pad. I tried both in the stability deck:

| Extra layout estimate | Result |
|---|---|
| 2 nH or 4 nH between the collector of `Qq1` and its bypass capacitor `Cfq2` | rings down |
| 8 nH or 15 nH in the same place | oscillates (0.26 to 0.5 V at the emitter node) |
| emitter link with 3 + 3 nH, 5 + 5 nH, 7 + 7 nH or 10 + 2 nH, with 0.5 or 1 pF on the emitter node | rings down |

So a long collector track is the dangerous one, and a longer emitter link is
harmless. On the board both collectors point the same way: `Lta` is a rung
between the two collector lines, `Cfq2` sits about 2 mm from the collector of
`Qq1`, and the emitters are joined by a U-shaped track of about 13 mm. With
6 + 6 nH in the emitter link and 0.8 pF on the emitter node the 125 MHz level
at the mixer drops by 4 % (`rx2_b2`, 0.726 V peak-to-peak instead of 0.758 V).

### Layout rules 7 and 8

7. The pump driver and the detector at least 50 mm from the tuned circuits of
   the first IF, with unbroken ground between.
8. The collector of `Qq1` reaches `Cfq2` within about 4 mm of track.

### Measured on the finished board

`../pcb_v2/gen/rx2_measure.py`, and a second check by two AI agents that were
not given my reasoning (2026-11-14). Distances are from copper to copper.

| Rule | Asks for | On the board |
|---|---|---|
| 3 | `c2` at least 25 mm from T5 | 30.8 mm |
| 7 | pump driver and detector at least 50 mm from the tuned nodes of the first IF | `c2` 52.6 mm, the pump node `x` 55.2 mm, the detector 58.4 mm. The pump driver's emitter node and base node are 45.4 and 46.6 mm away. That is under 50 mm. The emitter node carries a far smaller signal than `c2`. The base node carries the limiter's output (about 1.5 V peak to peak with a strong signal), but it does no harm: see "Reviews before the order" |
| 8 | `Qq1` collector to `Cfq2` within about 4 mm | 2.9 mm of track |

Two things on the board differ from what the blocks assume. By a hand
estimate both stay inside what the tolerance runs already cover:

- The first tuned node of the second IF (`t5`) has 63.6 mm of track, because
  it joins two collectors of mixer 2. That is about 3.5 pF to ground where
  the block has 1 pF, so T5 sits about 16 kHz low (1.1 %).
- `t1` and `m2in` have about 1.4 pF where the blocks have 0.5 pF. That is
  about 1 % low at 12.9 MHz, in a passband more than 1 MHz wide.

One supply track on the bottom layer (11.7 mm) runs under the track from
mixer 1 to T1, which crosses it 0.9 mm from its end. The ground under the
tuned circuits of both IF strips has no break.

## Reviews before the order (2026-11-15)

Two rounds of review by AI agents that were not given my reasoning, three
agents each. Neither found a fault.
Nothing in the circuit or on the board was changed. The numbers that add to
this log:

**Oscillators.** Seen from the crystal, the 25 MHz circuit is a negative
resistance of 212 Ω (112 Ω with slow transistors, a 3.0 V rail and 3 pF across
the crystal), against a crystal loss of 50 Ω at most. The 14.318 MHz circuit
has 238 Ω at that corner against 80 Ω at most. A start-up run with an 80 Ω
crystal reaches full level in 2 ms.

**As built.** With the stray capacitances of the layout and the data-sheet
values of the inductors: front end 12.4 dB (design 13.3), first mixer and first
IF 47.1 dB (47.7), oscillator level at the first mixer 0.340 V (0.363), crystal
drive 56 to 62 µW. The whole receiver gives 10.0 mV of audio at −27 dBm and
10.5 mV at −101 dBm, the same as the design.

**Stray capacitances from the copper.** One reviewer solved the electric field
of the real copper numerically (finite differences, tested on two cases with a
known answer). To ground: `t1` 1.35 pF, `t2` 1.6, `t3` 1.7, `m2in` 1.9, `t5`
4.0, `t6` 1.75 pF, and 0.92 pF on the squarer's emitter node `eq`. With these
the first IF peaks at 12.68 MHz and is 1.5 dB down at 12.9 MHz; the front end
peaks 1.1 MHz low and is 0.7 dB down. Between nodes, every coupling that has a
limit in this log is 70 to 3000 times under it (`c2` to `t1`: 0.0000028 pF
against 0.0002 pF). With all 36 couplings in the self-lock deck at once the
strips are quiet at 1, 3 and 10 times the computed values and locked at 30
times. So the margin against self-lock is between 10 and 30, and the model may
be wrong by about a factor of 3. A signal from about −101 dBm takes the limiter
over even at 100 times.

**Rule 7, corrected.** The pump driver's base node carries the limiter's
output, about 1.5 V peak to peak with a strong signal, not a small signal as I
wrote before. It still does no harm: with the stray taken from that node the
loop dies away for every value tried, up to 0.01 pF, and the computed stray is
0.000006 pF.

**Sensitivity, corrected.** The noise figure of 4.7 dB is the front end alone.
With the noise of the first mixer and the first IF it is about 6.5 dB (a
calculation on simulated stage values, about ±0.7 dB). The noise in the
131 kHz second IF is then about −116 dBm at the antenna. Estimated: the picture
is clean from about −106 dBm and readable down to about −109 dBm. This replaces
the −112 dBm above.

**For the bench.** The ADALM-Pluto has to be set to its 70 MHz to 6 GHz range
to send at 137.9 MHz. The firmware has to sample continuously, at 20 000
samples per second or more. At the time of the reviews the antenna track ran
for 1.2 mm under the metal base of the SMA jack with only solder mask between.
That piece was moved to the bottom side on 2026-11-15 (board README, "Two
changes after the reviews"), so no tape is needed under the jack.
A spare capacitor position can only lower a tuned circuit; to raise the first
IF, fit smaller values for `Ct1b` to `Ct4b`.

## What the simulations taught

- LTspice damps every inductor in a transient run unless `Rpar` is given. A
  crystal model needs `Rpar=1e15`, or its oscillator looks tame when it is
  not.
- An oscillator's amplitude can be found in seconds: force the crystal
  current, and look for the amplitude at which the circuit can just sustain
  the crystal's resistance.
- Take an oscillator's output behind the crystal: the crystal is its own
  filter.
- A diode clamp makes the oscillator level independent of the crystal and
  the transistor, so the loop gain can be generous.
- A squarer is only as symmetric as its drive: second harmonic in, 100 and
  150 MHz out.
- A 1 nF and a 100 nF bypass in parallel resonate near 135 MHz with their
  via inductance.
- An emitter follower's gain below 1 spoils a sharp Sallen-Key section.
- A single-balanced mixer leaks its LO onto the IF tuned circuit; at the
  second mixer that captured the limiter.
- An MMBT3904 pair is a bad load for a small 12.9 MHz tuned circuit (10 pF
  of poorly controlled capacitance).
- A shared capacitor to ground between two tuned circuits rejects better
  above resonance; a top capacitor rejects better below.
- LTspice refuses a `.step` with a single value. With a start time in `.tran`
  it counts the saved time from 0, so a `.meas` window given in real time
  finds no data and fails.
- A `.meas` that contains `sin(...*time)` silently gives wrong numbers. For a
  correlation, build the product in a behavioural source and average that.

## Next steps

1. ~~Independent check of the simulations.~~ Done, fixes applied and every
   deck re-run (see "After the independent check").
2. ~~Parts list with JLC order numbers and the cost sheet (target: under €50).
   Confirm the drive-level rating of both crystals.~~ Done 2026-11-14
   ([`PARTS.md`](PARTS.md), [`COST.md`](COST.md)).
3. ~~Schematic from the netlists, then the board (at most 100 × 100 mm, all
   parts on the top side), with the bypass rules above.~~ Done 2026-11-14
   ([`../pcb_v2`](../pcb_v2)).
4. ~~Board check, JLC files, bring-up plan.~~ Done 2026-11-15.
5. ~~Order the boards.~~ Ordered on 2026-11-16 (5 boards, 2 assembled by
   JLCPCB, connectors included; [`COST.md`](COST.md)).
6. Bring the boards up on the bench one block at a time, then write the ESP32
   firmware (see "Notes for the firmware").

## Attribution

I set the goal for version 2 (JLC-assembled, under €50, nothing to tune) and
approved the plan. The architecture and the simulations are worked out with
Claude (Anthropic) as an AI assistant, and I review each step.

Edy Grigore
