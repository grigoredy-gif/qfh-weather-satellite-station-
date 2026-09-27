# Discrete FM receiver for 137.9 MHz weather-satellite signals

This is the receiver half of my weather-satellite project. The antenna half (a
QFH antenna with a MATLAB design toolchain) is in [`../qfh_matlab`](../qfh_matlab),
and the circuit board for this receiver is in [`../pcb`](../pcb).

**Goal:** a superheterodyne receiver for the 137.9 MHz weather-satellite band,
built **entirely from discrete parts**: transistors, diodes, coils and
capacitors, with no ICs in the signal path. It demodulates the FM signal down
to the 2400 Hz APT audio tone, and an ESP32's ADC digitizes that audio so
software can turn it into an image. The NOAA satellites that sent APT were
switched off in 2025, so I test with recorded passes played back through an
ADALM-Pluto SDR.

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

## How it works

```
antenna
   |
band-pass filter 137.9 MHz ---- two coupled air coils, rejects the 112.1 MHz image
   |
LNA (BFR92P) ------------------ about 15 dB of gain, 50 ohm input
   |
mixer <---- LO 125 MHz <------- 25 MHz crystal oscillator > buffer > x5 multiplier
   |
IF filter 12.9 MHz ------------ two coupled toroid tanks, about 200 kHz wide
   |
IF amplifier ------------------ four tuned cascode stages, about 96 dB
   |
limiter > slope detector ------ FM becomes the 2400 Hz audio tone
   |
audio low-pass + level shift -> ESP32 ADC (44.1 kHz) -> APT image in software
```

| Parameter | Value | Why |
|---|---|---|
| RF input | 137.9 MHz | weather-satellite band |
| Crystal | 25 MHz | cheap and standard |
| LO | 125 MHz (25 × 5) | low-side injection |
| **IF** | **12.9 MHz** | 137.9 − 125 |
| Image | 112.1 MHz | lands in the quiet gap between FM broadcast (< 108 MHz) and airband (> 118 MHz) |
| FM deviation | ±17 kHz | APT specification |
| Audio | 2400 Hz subcarrier | the picture is in its envelope |

**The stages, in short:**

- **Band-pass filter.** Two tuned circuits with 82 nH air coils, coupled
  magnetically by their spacing. At 137.9 MHz a coil tap would sit at 0.65 of a
  turn, so a capacitive divider (8.2 pF over 56 pF) does the 50 ohm matching.
  Its main job is to remove the image at 112.1 MHz before it reaches the mixer.
- **LNA.** One BFR92P with shunt feedback and emitter degeneration. It sets
  the noise figure of the whole receiver.
- **Local oscillator.** A 25 MHz crystal Colpitts oscillator, a buffer, and a
  class-C stage that picks out the 5th harmonic (125 MHz) with two coupled
  tanks. A crystal plus a multiplier replaces a PLL: the crystal gives the same
  stability, and I avoid the programmable divider, which is the one block you
  cannot build without ICs.
- **Mixer.** One transistor turns the RF voltage into a current, and a
  transistor pair switched by the LO steers that current into the IF tank. It
  gives about 20 dB of conversion gain.
- **IF filter and amplifier.** Two coupled toroid tanks set the bandwidth, then
  four cascode stages with tapped toroids give about 96 dB of gain. The cascode
  blocks the feedback path through each transistor's collector-base
  capacitance, which is what makes four tuned stages at the same frequency
  possible at all.
- **Limiter and slope detector.** Diodes clip the IF so only the frequency is
  left. A tank tuned slightly off the carrier turns the frequency swing into an
  amplitude swing, and a Schottky diode (1N5711) recovers the audio.
- **Audio chain.** Two Sallen-Key sections built around emitter followers (a
  4th-order Butterworth low-pass), a gain stage, and a divider that centres the signal at 1.26 V in the ESP32 ADC's
  linear range (GPIO36). It has its own RC-filtered supply, so the ESP32's
  current bursts stay out of the audio.
- **Supply.** The ESP32-DevKitC's 5V pin, which is really about **4.6 V**
  (USB VBUS minus a Schottky diode on the module), through a ferrite bead and a
  1000 µF bulk capacitor. The whole receiver draws about 40.7 mA.

## Key design decisions

1. **IF = 12.9 MHz** so the image falls where nothing strong transmits. A simple
   two-resonator filter is then enough, instead of a complex front end.
2. **Crystal × 5 instead of a synthesizer**, to keep the "no ICs" rule without
   losing frequency stability.
3. **Capacitive dividers instead of coil taps** at 137.9 MHz, because the tap
   would need a fraction of a turn.
4. **Cascode IF stages**, because 96 dB of gain at one frequency oscillates
   easily, and the cascode removes the main internal feedback path.
5. **Limiter + slope detector** as the FM demodulator: the simplest discrete
   option, and the one I most wanted to understand.
6. **A fixed capacitor plus a trimmer in every tank**, split so that the trimmer
   lands mid-range even with ±10 % coils and the board's own parasitics.
7. **Design for the real rail.** When I found out the supply is 4.6 V and not
   5.0 V, I re-centred every bias network instead of accepting ~8 dB less IF
   gain.

## Simulations (LTspice)

I simulated every block on its own first, then the connections between blocks,
then the whole receiver. All files are in this folder; each sheet has a short
header saying what it tests.

| Sim | What it checks | Key result |
|---|---|---|
| SIM 1 | slope detector | S-curve peak at 12.95 MHz; ~60 mVpp of 2400 Hz, THD 0.78 % |
| SIM 2 | audio filter and ADC interface | flat to 0.70 dB, 45.7 dB down at 22 kHz |
| SIM 3 | IF filter | 200.5 kHz bandwidth at critical coupling |
| SIM 4 | IF amplifier + limiter | 95.8 dB gain; +20 dB in gives only +1.6 dB out |
| SIM 5 | ×5 multiplier | 1.68 V of 125 MHz; 4th and 6th harmonics −36.7 / −42.1 dB |
| SIM 6 | crystal oscillator + buffer | starts and limits at 409.7 mVpp; 2.33 Vpp from the buffer |
| SIM 7 | input band-pass filter | 39.5 dB image rejection, 2.4 dB loss |
| SIM 8 | mixer | 22.8 dB conversion gain |
| SIM 9 | LNA | S21 15.8 dB (about 14 dB expected with the board layout) |
| SIM 10–11 | block interfaces | +20.6 dB from the mixer to the first IF stage |
| SIM 12 | the full receiver on one rail | every bias point matches the block sims; 40.7 mA at 4.6 V |
| SIM 13 | FM in, audio out | a 20 dB input change becomes 0.5 dB at the detector; clean 2400 Hz at the ADC |

End to end the gain is about **130 dB** (−2.2 dB filter, +15.8 dB LNA,
+20.6 dB mixer and IF filter, +95.8 dB IF strip), so the limiter is fully
driven from about −106 dBm at the input. A QFH antenna delivers roughly
−90 dBm from a satellite pass. Most block simulations were run at 5.0 V
before I found the real rail; `sim12` is the one re-centred for 4.6 V and is the
design authority for the PCB.

## Status

- **Done:** every block simulated, the interfaces checked, and the full receiver
  simulated from FM input to the ADC.
- **Done:** the PCB is designed and checked (see [`../pcb`](../pcb)).
- **Next:** order the board, build it, align it one block at a time, and feed it
  a recorded APT pass from the Pluto.

## What I learned

- **A testbench only answers the question you ask it.** Blocks that looked
  finished on their own changed once they were connected: the IF tap had to be
  re-sized and the mixer delivered 4 dB more than the numbers on paper.
- **Check the real supply.** The "5 V" pin on the ESP32 board is 4.6 V, and that
  alone moved the transistor currents by about 16 %.
- **A catalogue beats a schematic.** Trimmer ranges I had specified do not exist
  as real parts, and the transistor I first picked (BFR93A) is obsolete.
- **At VHF the layout is part of the circuit.** A few nanohenries of copper
  moved a filter's trimmer out of range, and 20 mm of track in the LNA's
  emitter would have cost 4–5 dB of gain.
- **Tuned collectors swing above the supply rail.** My first multiplier design
  swung past the transistor's voltage rating.
- **Read the right number.** The wanted spectral line, not the raw
  peak-to-peak; and on the reception side, the mean SNR, not the peak.
- **Predictions can be wrong.** I expected over-coupling the input filter to
  improve image rejection. It made it worse, and I understood why only after
  the simulation.

## Files

| File | What it is |
|---|---|
| `sim*.asc` | the LTspice simulations (short header on each sheet) |
| `sim12_full_receiver.asc` / `.net` | the full receiver, the design authority for the PCB |
| [`DESIGN_LOG.md`](DESIGN_LOG.md) | the complete step-by-step design log, with every result and revision |
| [`sim_notes.md`](sim_notes.md) | the notes I first wrote on the simulation sheets |

## License / attribution

This is my project. I set the goals and the requirements (a fully discrete
receiver with no ICs in the signal path), I made or approved every design
decision, and the building and bench testing are mine. It builds on
well-documented amateur-radio practice; the references are in the design log.

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

Edy Grigore
