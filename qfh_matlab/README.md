# qfh_matlab — QFH antenna generator for 137 MHz weather satellites

This is a MATLAB toolchain that designs a **QFH (Quadrifilar Helix) antenna**.
It draws the antenna in 3D and exports a **`.nec` file for electromagnetic
simulation in [4nec2](https://www.qsl.net/4nec2/)**. I made it to receive
137 MHz weather-satellite images (RHCP) with an ADALM-Pluto SDR.

> **Satellite status (2026):** the NOAA POES satellites (analog APT) were
> switched off in June–August 2025 and **no longer transmit**. The
> 137 MHz satellites to target now are **Meteor-M N2-3 / N2-4 (digital LRPT)**
> on 137.1 and 137.9 MHz. They are also RHCP, so the antenna itself does
> not change. The decoding is done with SatDump. A 137.5 MHz design covers
> both frequencies without problems.

## Motivation

In my first year of Electrical Engineering at the University of Twente, the
Module 4 project was to design an antenna and a transmitter PCB. I really
enjoyed that field, together with the courses that went with it: High Frequency
Electronics, and Electromagnetostatics and Electrodynamics. After the module I
wanted to go deeper than the project allowed, so I decided to design my own
antenna and my own receiver for the 137 MHz weather satellites.

For the receiver I wanted to do everything analog, without any integrated
circuits in the signal path, so that I have to understand every stage at
component level. This toolchain is the antenna half of the project. The
receiver half is in [`../fm_receiver`](../fm_receiver).

The plan had to change along the way. The NOAA satellites whose analog APT
signal my receiver was designed for were switched off in 2025, and the
Meteor-M satellites that are still up send a digital signal that an analog FM
receiver cannot decode. So I test the two halves separately: this antenna with
an SDR on the Meteor-M satellites, and the receiver with recorded NOAA passes
played back into it through an ADALM-Pluto.

The next step is to close the loop with my own hardware on both ends. I want to
build a second QFH antenna and a transmitter, which should be easier than the
receiver, and send information between the two stations with frequency
modulation, using my own PCBs and my own antennas at both ends. That link has
to run on a frequency I'm allowed to transmit on, because 137 MHz is
receive-only for me.

## Attribution

This toolchain is my project, but I did not invent the design method, and the
original code is not mine. It is a MATLAB port of programs that are freely
available online:

- **[John Coppens' QFH calculator](https://www.jcoppens.com/ant/qfh/calc.en.php)**:
  the online QFH calculator on John Coppens' website. Its JavaScript source
  (`qfhcalc.js`) is released under **GPL-2.0**. The empirical design formulas,
  the conductor-diameter compensation tables and the dimension conventions all
  come from there. My printable mast-drilling template is also directly
  inspired by the one his design tool generates (wrap-around strips with
  real-size hole circles).
- **[QFH2nec](https://github.com/oceantrotter/QFH2nec)** (`QFH2nec.c`,
  **GPL-3.0**): the wire-by-wire geometry and the NEC2 card export are a
  direct port of this program, which itself adapts the Coppens calculator
  code.
- **[helix2nec](https://uuki.kapsi.fi/qha_simul.html)**: the original
  bifilar-helix-to-NEC generator that QFH2nec is based on.
- **NEC2**: the simulation engine underneath, developed by G. Burke and
  A. Poggio at Lawrence Livermore National Laboratory.

The port was validated against the original: `QFH2nec.c` was compiled with
gcc and the generated NEC geometry was compared line by line. **All 127 GW
cards match with exactly zero coordinate difference** (with
`freq_cal = 1.0`, `c_kms = 299792`, `feed_len_mm = 2`).

The MATLAB code was mostly written with **Claude (Anthropic)** as an AI coding
assistant: the port itself, the plotting/export code, the self-test suite and
the drilling-template generator. I checked the results against the compiled C
original, the output of the Coppens website and, in the end, the antenna I
built from these drawings and measured with a VNA. The antenna itself, its
construction, the measurements and every accept/reject decision are mine.

Edy Grigore

The code comments were first written in Romanian during development and later
translated to English for publication.

## What this port adds on top of the originals

- A modular MATLAB pipeline with parameters (each step is its own `.m` file)
- A 3D view of the antenna in MATLAB (+ PNG export)
- **Frequency calibration** (see the section below). The original
  formulas give a resonance ~2.2% below the requested frequency, and
  this port can correct for it
- A printable 1:1 A4 **drilling template** for the mast. MATLAB makes
  the PDF itself, with wrap-around strips, real-size hole circles and a
  calibration bar. The layout is inspired by the template of the Coppens
  design tool
- An automatic **self-test suite** with 62 checks. It reproduces the
  reference values from the Coppens website, checks that the geometry is
  continuous, validates the .nec structure, and checks the calibration
  math and the drilling-template geometry
- Extra geometry checks that the C original does not have (guards
  against degenerate geometry: `H > 2R`, feed length vs. loop size)
- Two bugs in `QFH2nec.c` that came up during porting (fixed here and
  described below)

## Frequency calibration (`freq_cal`)

**The problem.** The Coppens design formulas are empirical. When I
simulate the geometry they give in NEC2 (free space), the real resonance
is about **2.2% below** the design frequency. For example, a 137.5 MHz
design has its SWR minimum at ≈134.5 MHz.

**The fix.** The whole geometry scales with the wavelength. So if I
design at a slightly *higher* frequency, the resonance moves up
linearly. The `freq_cal` parameter does this internally:

```
effective design frequency = freq_mhz × freq_cal
freq_cal = 137.5 / 134.5 ≈ 1.0223     (derived from the NEC2 sweep)
```

**Verification.** With `freq_cal = 1.0223`, the 4nec2 simulation of the
137.5 MHz target design gives **SWR ≈ 1.05 at 137.5 MHz** (reflection
coefficient ≈ −33 dB), and the SWR minimum sits right on the target. I
checked the factor for both 1.78 mm and 7 mm conductors.

**Why I did not change the Coppens formulas themselves.** They were
calibrated on real, built antennas. Those include effects that a
free-space NEC2 model does not see (feedline, mast, insulation, real
corner shapes). So the difference is a *modeling offset*, not just an
error in the original formulas. I kept the correction as a separate,
documented factor (default **1.0** = the same output as Coppens/QFH2nec).
This way you can choose either convention, and `qfh_selftest` still
checks the port against the website values with `freq_cal = 1.0`. For a
real build, the final trim should be based on a VNA measurement at the
feedpoint.

## Usage

1. Open MATLAB and `cd` into this folder.
2. Edit the parameters in `qfh_main.m` (target frequency, wire diameter…).
3. Run:

   ```matlab
   qfh_main
   ```

   This gives you the dimension table in the Command Window, the 3D
   figure (+ PNG) and the `QFH_137.5MHz_dX.XXmm.nec` file.

4. Open the `.nec` file in 4nec2 (`File > Open 4nec2 in/out file`) and
   run the simulation with `F7` (choose *Far Field pattern*). Then check:
   - impedance / SWR at 137.5 MHz (main window + the SWR plot);
   - the far-field pattern: the main lobe should point to zenith (theta = 0);
   - polarization: the **RHCP** gain must be the strongest toward zenith
     (in 4nec2: *Far field > Polarization > LHCP/RHCP*).

## Files

| File                  | Role                                                       |
|-----------------------|------------------------------------------------------------|
| `qfh_main.m`          | main script, set your parameters here                      |
| `qfh_defaults.m`      | fills in / validates parameters                            |
| `qfh_design.m`        | dimension computation (port of `compute_design` / Coppens) |
| `qfh_report.m`        | construction dimension table                               |
| `qfh_geometry.m`      | 3D geometry: wire list (port of `make_helix`)              |
| `qfh_plot3d.m`        | 3D visualization in MATLAB                                 |
| `qfh_write_nec.m`     | `.nec` export (GW/FR/EX/RP cards)                          |
| `qfh_selftest.m`      | automatic tests (design vs. website, geometry, .nec, calibration) |
| `qfh_drill_marks.m`   | drill positions on the mast (wire + support-tube holes)    |
| `qfh_write_template.m`| printable 1:1 A4 drilling template (PDF, Coppens-inspired) |
| `qfh_run_template.m`  | generates the template for your mast/support diameters     |
| `qfh_wire_compare.m`  | generates two .nec files to compare conductor diameters    |

## Verification

```matlab
qfh_selftest
```

Test A reproduces the exact values of the Coppens website calculator for
the reference configuration (137.5 MHz, 7 mm conductor): H1=731.8,
Di1=315, H2=695.8, Di2=299.1, etc. Tests B–E check geometry continuity,
the exported `.nec` structure, the frequency-calibration math and the
drilling-template geometry. As an extra check, the uncalibrated drill
depths (`freq_cal = 1.0`, 1.78 mm wire) match the values in the template
PDF that the Coppens website generates itself, to within 0.1 mm (e.g.
bottom station 687.8 mm, middle station 343.9 mm).

## Conductor diameter (solid copper installation wire)

| Cross-section (FY / H07V-U) | Diameter |
|-----------------------------|----------|
| 1.5 mm²                     | 1.38 mm  |
| 2.5 mm²                     | 1.78 mm  |
| 4.0 mm²                     | 2.26 mm  |
| 6.0 mm²                     | 2.76 mm  |

Measure your wire with a caliper (without the insulation) and set
`params.wire_d_mm`. The diameter goes into the compensation factor, so
all dimensions are recomputed correctly for your wire. When I simulated
1.78 vs 2.76 mm, the electrical difference was negligible for this
design. So you can choose the wire for mechanical reasons.

## Notes

- **Polarization**: weather satellites transmit RHCP. The QFH radiates
  in *backfire* mode (the lobe comes out of the feed end, upward), so
  the winding direction is opposite to the polarization. The code
  handles this automatically (negative `turns`), the same way as
  QFH2nec.c. You can switch to `LHCP` with `params.polarity`.
- **Bugs found in `QFH2nec.c` while porting** (fixed in this port):
  1. the wire radius is halved twice (once in `compute_design`, once in
     `main`), so the C program writes a radius of `d/4` instead of `d/2`
     into the .nec file;
  2. `h[0].Theta` is used uninitialized (stack garbage). The reference
     build used for the validation was patched with `Theta = 0`.
- **Speed of light**: the Coppens website uses c = 300000 km/s and the C
  code uses 299792. Here the website value is the default (0.07%
  difference). You can change it with `params.c_kms`.
- **Other intentional differences from the C original**: the diameter
  check also accepts thin wires (0.5–50 mm; C requires ≥ 1 mm). The feed
  length can be set (`feed_len_mm`, default 10 mm; C hardcodes 2 mm).
  There are also guards against degenerate geometry (H > 2R etc.) that
  do not exist in C.
- **Template top-hole convention**: the drilling template puts the top
  wire holes on the cardinal axes of the loops (0°/180° and 90°/270°).
  This matches the Coppens template and makes the build easier, and at
  the top the wires are bent a bit toward the offset feed point anyway.
  The *simulated* model keeps the exact QFH2nec feed geometry, where the
  slanted top radials cross the mast wall at ~11.6°/78.4° (default
  build). The difference is ~3 mm of arc at the mast wall (~0.0014 λ),
  which is electrically negligible. Set `params.top_marks = 'exact'` if
  you want to mark the simulated wall crossings instead.
- **Mast circumference**: measure it by wrapping a paper strip or a
  string around the mast. This is much more accurate than holding a
  ruler across a round pipe. Then set `params.mast_d_mm = circumference/pi`,
  and the template strips meet exactly on the seam.
- **Real feed**: when you build it, feed the antenna through an *infinite
  balun* (the coax goes up inside the mast) or add a common-mode choke
  (5–8 turns of coax, ~10–15 cm diameter, right below the feedpoint).
  The impedance of the antenna itself is close enough to 50 Ω, so no
  matching network is needed for reception.

## License

GPL-3.0. This project is a derivative work of GPL-licensed code
(`QFH2nec.c`, GPL-3.0; `qfhcalc.js`, GPL-2.0), so it is published under the
GPL as well. See [LICENSE](LICENSE).
