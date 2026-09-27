# lrpt_decoder — a from-scratch Meteor-M LRPT analysis chain in MATLAB

I wrote these tools in August 2026 to answer one question my station kept
raising: *SatDump's Viterbi locks on Meteor-M N2-3 (137.9 MHz) with BER 0.03,
so why does the deframer never sync and why are there no images?*

> **Correction (9 August 2026):** the first conclusion I drew from these tools
> was wrong. The satellite was fine. My signal was too weak. Details below.

## What I thought at first

Working one tool at a time, I found a fully standard CCSDS link layer (OQPSK
72k, K=7 r=1/2 convolutional coding 171/133 octal, NRZ-M, per-frame CCSDS
randomizer, ASM `1ACFFC1D`, AOS headers ver 1 / SCID 0 / VCID 5 with live
counters). But the frames seemed to come 424 bytes (counter +1) and 1148 bytes
(counter +2) apart instead of in standard 1024-byte CADUs, and the payload
looked like random data. So I concluded that the satellite was sending a
nonstandard mode that no public decoder could turn into images.

## What was actually going on

After searching some forums (r/meteorsatellites), I found out that the
satellite was online and working: other people were receiving images from
Meteor-M N2-3 and N2-4 in the same weeks. Several fellow enthusiasts gave me
the same answers:

- **My signal was too weak and too inconsistent.** The "~10 dB SNR" I trusted
  was SatDump's *peak* SNR, which includes noise spikes. The *mean* SNR was
  only **1.763 dB**, below the ~3–4 dB the deframer needs to lock. "Viterbi
  but no deframer" is the typical sign of a very inconsistent signal.
- **The strange frame sizes were not real.** The 424/1148-byte spacings were
  artifacts of an error-ridden stream, where many ASM detections were simply
  missed.
- **My gain was set badly.** The advice was to start low and raise the gain
  during the pass until the mean SNR is at its best.
- **My location was bad for reception, and the ADALM-Pluto is not ideal for
  this use.** Its input is unfiltered, so FM broadcast (88–108 MHz) overloads
  it and creates intermodulation products, and without an LNA it is quite deaf
  at 137 MHz. The fix is an LNA plus a 137 MHz SAW filter in front of it, which
  is exactly what the input stages of my own receiver do (see
  [`../fm_receiver/`](../fm_receiver/), SIM 7 and SIM 9).
- On top of that, N2-3 was reported to have a degraded antenna, so it is a
  weak satellite to start with.

So the station software and SatDump were fine; the signal was the problem.
The tools themselves still work and are useful for looking inside a weak or
strange recording. Only the conclusion I first drew from them was wrong.

## The tools (run them in this order)

| # | Tool | Question it answers |
|---|------|---------------------|
| 1 | `lrpt_sync.m` | baseband → synchronized symbols. Doppler tracking, open-loop symbol timing from the 72 kHz clock line, OQPSK + plain-QPSK branches, constellation quality metrics |
| 2 | `lrpt_frame_hunt.m` | do CCSDS frames exist? Correlates the encoded-ASM 52-chip template across 96 demod-ambiguity variants; self-tests the encoder against SatDump's correlator constant |
| 3 | `lrpt_loop_test.m` | is it a repeating test loop or changing data? |
| 4 | `lrpt_viterbi_peek.m` | state-seeded Viterbi decode after each ASM; reads the AOS headers |
| 5 | `lrpt_deep_peek.m` | long decodes through whole periods; frame accounting via counters |
| 6 | `lrpt_hdr_scan.m` | exhaustive header scan (every byte offset × both randomizer conventions) |
| 7 | `lrpt_walk.m` | walks the frame chain with a size/step rule; M-PDU/APID census |
| 8 | `lrpt_frame_dump.m` | aligned hex dumps per frame class; finds constant fields by eye |
| 9 | `lrpt_prbs_test.m` | is the payload a modem test pattern? (all ITU O.150 polynomials) |

Everything is base MATLAB (R2025a, no toolboxes). The companion folder
`../baseband_tools/` has the recording-health tools (`baseband_check.m`,
`signal_id.m`, `cut_segment.m`). Run those on any capture first.

## Method notes (learned the hard way)

- **Check the mean SNR before anything else.** If the stream is below the
  decoding threshold, a deep analysis will find "structure" in its own errors.
  That is exactly what happened to me here.
- Never trust a single measurement window or a single timestep. Prove
  convergence/settling with two spaced windows.
- Anchor the analysis in the **densest-detection** region, not at the
  "strongest" correlation peak. Correlation saturates wherever the signal is
  good, so picking the strongest peak first lands on the noisy edge of the pass.
- When a decoder disagrees with the RF evidence, measure one layer deeper
  instead of re-running the decoder with one more setting. But first make sure
  the RF evidence is strong enough to mean something.

## Attribution

I (Edy Grigore) developed these tools together with **Claude (Anthropic)**,
which I used as a coding and DSP-reasoning assistant. The AI drafted the
scripts from hypotheses we came up with together, I ran them on my own
recordings, and each result decided the next step (including throwing out
several of our own wrong hypotheses along the way). The receptions, hardware,
measurements and accept/reject decisions are mine.
Protocol facts were cross-checked against: CCSDS 131.0-B / 732.0-B,
SatDump (Analog Devices / SatDump project sources), dbdexter's
`meteor_demod`, artlav's `meteor_decoder`, USRadioguy's Meteor-M pages and
the happysat status history. The correction of my first conclusion came from
the r/meteorsatellites community.
