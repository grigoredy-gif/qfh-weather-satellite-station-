# Parts list for receiver version 2

Every part of the version 2 receiver, with the number JLCPCB orders it by
(the LCSC number) and the fee class it falls in. I want JLCPCB to assemble
the board completely for less than €50 (5 boards, 2 of them assembled), so
the parts are chosen around their fee rules.

The list is not typed by hand. A script reads the eleven circuit blocks in
[`simulations/`](simulations) and writes the tables below and
[`rx2_parts.csv`](rx2_parts.csv), which has one row per part. The layout
estimates in the blocks (names ending in `_x`) are not parts and are left out.
The boards were ordered on 2026-11-16, with JLCPCB also soldering the
connectors. The schematic and the board are in [`../pcb_v2`](../pcb_v2).

## In short

| | |
|---|---|
| Parts on the board | 252, in 63 different lines, all on the top side |
| Solder joints | 551 per board |
| Lines without a fee | 59 (48 Basic, 11 Preferred) |
| Lines with the Extended fee | 4: the three inductor values and the 14.31818 MHz crystal |
| Parts that force the dearer "Standard" assembly | none |
| Computed cost, 5 boards with 2 assembled | $41.06 = €37.2 (my limit is €50) |

How JLCPCB charges for a part: **Basic** parts are free to place. **Preferred**
parts are free in economic assembly. Every other part is **Extended** and
costs $12.28 for 4 kinds ($3.07 per kind, however many pieces). A part
marked "Standard only" would move the whole order to the dearer assembly
type, so the design uses none.

## What is checked and what is assumed

**Read in JLCPCB's parts library on 2026-11-14, one part at a time, for all
63 lines:**

- the number exists, and its value and package are what the circuit needs;
- its fee class;
- that it is allowed in economic assembly;
- stock, price and minimum quantity.

**Read in the makers' data sheets:**

- Both crystals are from YXC's YSX321SL series and share one data sheet. Drive
  level: 10 to 200 µW maximum, 100 µW typical. The design puts 56 µW into the
  25 MHz crystal (75 µW at the top of the supply range) and at most 67 µW
  into the 14.31818 MHz crystal, so both are inside the rating. Series resistance:
  50 Ω maximum at 25 MHz and 80 Ω maximum at 14.3 MHz, the values the
  simulation uses as its worst case.
- The quality factor of the three inductors (section "Inductor quality
  factors" below).
- The pin order of the 2SC3356, the BAS70 and the BAV99 (table further down).

**Not read from a data sheet:** the pin order of the S9018, MMBT3904 and
MMBT3906 (taken from JLCPCB's symbol for the part).

**Assumed, or not checked:**

- The cost is computed from JLCPCB's published fee table (page dated
  2026-10-22) and the library prices. It is not a quote.
- How much capacitance the large ceramic capacitors lose under DC voltage
  (section below).
- Footprints. They are in the schematic and the board, see [`../pcb_v2`](../pcb_v2).

## The parts

### Resistors (104 parts, 30 values)

| Value | Package | Qty | Blocks | LCSC | Part | Class |
|---|---|---|---|---|---|---|
| 2.2 Ω | 0603, 1 % | 1 | front end | C22939 | 0603WAF220KT5E, UNI-ROYAL | Basic |
| 10 Ω | 0603, 1 % | 2 | front end, regulator | C22859 | 0603WAF100JT5E, UNI-ROYAL | Basic |
| 22 Ω | 0603, 1 % | 2 | 125 MHz chain (2) | C23345 | 0603WAF220JT5E, UNI-ROYAL | Basic |
| 33 Ω | 0603, 1 % | 2 | front end, 125 MHz chain | C23140 | 0603WAF330JT5E, UNI-ROYAL | Basic |
| 47 Ω | 0603, 1 % | 8 | 125 MHz chain (3), mixer 1 (3), second IF and detector, audio | C23182 | 0603WAF470JT5E, UNI-ROYAL | Basic |
| 100 Ω | 0603, 1 % | 16 | 25 MHz oscillator, 125 MHz chain (2), mixer 1 (2), first IF (3), mixer 2 (3), 14.318 MHz oscillator, second IF and detector (3), audio | C22775 | 0603WAF1000T5E, UNI-ROYAL | Basic |
| 120 Ω | 0603, 1 % | 1 | front end | C22787 | 0603WAF1200T5E, UNI-ROYAL | Basic |
| 200 Ω | 0603, 1 % | 1 | mixer 1 | C8218 | 0603WAF2000T5E, UNI-ROYAL | Basic |
| 270 Ω | 0603, 1 % | 1 | bias references | C22966 | 0603WAF2700T5E, UNI-ROYAL | Basic |
| 390 Ω | 0603, 1 % | 2 | 125 MHz chain, second IF and detector | C23151 | 0603WAF3900T5E, UNI-ROYAL | Basic |
| 470 Ω | 0603, 1 % | 3 | front end, 25 MHz oscillator, second IF and detector | C23179 | 0603WAF4700T5E, UNI-ROYAL | Basic |
| 560 Ω | 0603, 1 % | 1 | second IF and detector | C23204 | 0603WAF5600T5E, UNI-ROYAL | Basic |
| 680 Ω | 0603, 1 % | 4 | 125 MHz chain (3), 14.318 MHz oscillator | C23228 | 0603WAF6800T5E, UNI-ROYAL | Basic |
| 1 kΩ | 0603, 1 % | 2 | front end, mixer 2 | C21190 | 0603WAF1001T5E, UNI-ROYAL | Basic |
| 1.1 kΩ | 0603, 1 % | 3 | second IF and detector (2), bias references | C22764 | 0603WAF1101T5E, UNI-ROYAL | Preferred |
| 1.2 kΩ | 0603, 1 % | 3 | first IF (2), regulator | C22765 | 0603WAF1201T5E, UNI-ROYAL | Basic |
| 1.5 kΩ | 0603, 1 % | 3 | second IF and detector, audio, regulator | C22843 | 0603WAF1501T5E, UNI-ROYAL | Basic |
| 1.8 kΩ | 0603, 1 % | 2 | front end, second IF and detector | C4177 | 0603WAF1801T5E, UNI-ROYAL | Basic |
| 2.2 kΩ | 0603, 1 % | 4 | front end, 125 MHz chain, audio, regulator | C4190 | 0603WAF2201T5E, UNI-ROYAL | Basic |
| 2.7 kΩ | 0603, 1 % | 1 | audio | C13167 | 0603WAF2701T5E, UNI-ROYAL | Basic |
| 3 kΩ | 0603, 1 % | 2 | second IF and detector, audio | C4211 | 0603WAF3001T5E, UNI-ROYAL | Basic |
| 4.7 kΩ | 0603, 1 % | 2 | 125 MHz chain, bias references | C23162 | 0603WAF4701T5E, UNI-ROYAL | Basic |
| 5.6 kΩ | 0603, 1 % | 2 | audio (2) | C23189 | 0603WAF5601T5E, UNI-ROYAL | Basic |
| 10 kΩ | 0603, 1 % | 21 | front end, mixer 1 (4), first IF (5), mixer 2 (5), second IF and detector (5), audio | C25804 | 0603WAF1002T5E, UNI-ROYAL | Basic |
| 15 kΩ | 0603, 1 % | 5 | 125 MHz chain, mixer 1, mixer 2, audio (2) | C22809 | 0603WAF1502T5E, UNI-ROYAL | Basic |
| 22 kΩ | 0603, 1 % | 5 | 25 MHz oscillator (2), 14.318 MHz oscillator (2), audio | C31850 | 0603WAF2202T5E, UNI-ROYAL | Basic |
| 27 kΩ | 0603, 1 % | 2 | second IF and detector, audio | C22967 | 0603WAF2702T5E, UNI-ROYAL | Basic |
| 33 kΩ | 0603, 1 % | 1 | 125 MHz chain | C4216 | 0603WAF3302T5E, UNI-ROYAL | Basic |
| 51 kΩ | 0603, 1 % | 1 | audio | C23196 | 0603WAF5102T5E, UNI-ROYAL | Basic |
| 82 kΩ | 0603, 1 % | 1 | audio | C23254 | 0603WAF8202T5E, UNI-ROYAL | Basic |

### Capacitors (92 parts, 22 values)

| Value | Package | Qty | Blocks | LCSC | Part | Class |
|---|---|---|---|---|---|---|
| 3 pF | 0603, C0G 50 V, ±0.25 pF | 1 | first IF | C46219 | 0603CG3R0C500NT, FH | Preferred |
| 4.7 pF | 0603, C0G 50 V, ±0.25 pF | 2 | first IF, second IF and detector | C1669 | 0603CG4R7C500NT, FH | Preferred |
| 6 pF | 0603, C0G 50 V, ±0.25 pF | 1 | front end | C37474 | 0603CG6R0C500NT, FH | Preferred |
| 6.8 pF | 0603, C0G 50 V, ±0.25 pF | 7 | front end (2), 125 MHz chain (2), first IF (2), second IF and detector | C1679 | 0603CG6R8C500NT, FH | Preferred |
| 8.2 pF | 0603, C0G 50 V, ±0.25 pF | 1 | front end | C1685 | 0603CG8R2C500NT, FH | Preferred |
| 10 pF | 0603, C0G 50 V, 5 % | 1 | 25 MHz oscillator | C1634 | CL10C100JB8NNNC, Samsung | Basic |
| 12 pF | 0603, C0G 50 V, 5 % | 1 | front end | C38523 | CL10C120JB8NNNC, Samsung | Basic |
| 15 pF | 0603, C0G 50 V, 5 % | 1 | 125 MHz chain | C1644 | CL10C150JB8NNNC, Samsung | Basic |
| 18 pF | 0603, C0G 50 V, 5 % | 2 | front end, 125 MHz chain | C1647 | CL10C180JB8NNNC, Samsung | Basic |
| 33 pF | 0603, C0G 50 V, 5 % | 3 | first IF (2), 14.318 MHz oscillator | C1663 | CL10C330JB8NNNC, Samsung | Basic |
| 47 pF | 0603, C0G 50 V, 5 % | 4 | 25 MHz oscillator, first IF (2), second IF and detector | C1671 | CL10C470JB8NNNC, Samsung | Basic |
| 68 pF | 0603, C0G 50 V, 5 % | 2 | 14.318 MHz oscillator (2) | C28262 | CL10C680JB8NNNC, Samsung | Preferred |
| 100 pF | 0603, C0G 50 V, 5 % | 7 | 25 MHz oscillator, 125 MHz chain, mixer 1 (2), 14.318 MHz oscillator, second IF and detector (2) | C14858 | CL10C101JB8NNNC, Samsung | Basic |
| 330 pF | 0603, C0G 50 V, 5 % | 2 | front end, first IF | C1664 | CL10C331JB8NNNC, Samsung | Basic |
| 470 pF | 0603, X7R 50 V, 10 % | 1 | second IF and detector | C1620 | 0603B471K500NT, FH | Basic |
| 1 nF | 0603, X7R 50 V, 10 % | 15 | front end (3), 125 MHz chain, mixer 1 (3), first IF (2), mixer 2, second IF and detector (2), audio (3) | C1588 | CL10B102KB8NNNC, Samsung | Basic |
| 4.7 nF | 0603, X7R 50 V, 10 % | 2 | audio (2) | C53987 | 0603B472K500NT, FH | Basic |
| 10 nF | 0603, X7R 50 V, 10 % | 11 | 25 MHz oscillator, 125 MHz chain (2), first IF (2), mixer 2 (2), second IF and detector (4) | C57112 | 0603B103K500NT, FH | Basic |
| 100 nF | 0603, X7R 50 V, 10 % | 18 | front end, 25 MHz oscillator, 125 MHz chain (4), mixer 1 (2), first IF (3), mixer 2 (2), 14.318 MHz oscillator, second IF and detector (4) | C14663 | CC0603KRX7R9BB104, YAGEO | Basic |
| 1 µF | 0603, X5R 50 V, 10 % | 3 | second IF and detector, audio (2) | C15849 | CL10A105KB8NNNC, Samsung | Basic |
| 10 µF | 0603, X5R 10 V, 10 % | 4 | regulator (2), bias references (2) | C19702 | CL10A106KP8NNNC, Samsung | Basic |
| 100 µF | 1206, X5R 6.3 V, 20 % | 3 | audio (2), regulator | C15008 | CL31A107MQHNNNE, Samsung | Basic |

### Inductors (11 parts, 3 values)

| Value | Package | Qty | Blocks | LCSC | Part | Class |
|---|---|---|---|---|---|---|
| 68 nH | 0603, wirewound, 2 % | 5 | front end (3), 125 MHz chain (2) | C86135 | LQW18AN68NG00D, Murata | Extended |
| 3.3 µH | 1008, wirewound, 5 % | 4 | first IF (4) | C6364740 | AHW2520C-3R3JTF, APV | Extended |
| 100 µH | 1210, wirewound, not shielded, 5 % | 2 | second IF and detector (2) | C295124 | NLV32T-101J-EF, TDK | Extended |

### Transistors (38 parts, 4 types)

| Value | Package | Qty | Blocks | LCSC | Part | Class |
|---|---|---|---|---|---|---|
| 2SC3356 | SOT-23, NPN | 7 | front end, 125 MHz chain (3), mixer 1 (3) | C28646266 | 2SC3356, hongjiacheng | Preferred |
| S9018 | SOT-23, NPN | 6 | 25 MHz oscillator, 125 MHz chain, first IF (4) | C41375130 | S9018, hongjiacheng | Preferred |
| MMBT3904 | SOT-23, NPN | 19 | mixer 2 (6), 14.318 MHz oscillator, second IF and detector (6), audio (2), regulator (2), bias references (2) | C20526 | MMBT3904, Jiangsu Changjing | Basic |
| MMBT3906 | SOT-23, PNP | 6 | second IF and detector, audio (2), regulator (2), bias references | C7420354 | MMBT3906, hongjiacheng | Preferred |

### Diodes (5 parts, 2 types)

| Value | Package | Qty | Blocks | LCSC | Part | Class |
|---|---|---|---|---|---|---|
| BAS70 | SOT-23, Schottky, single | 3 | 14.318 MHz oscillator (2), second IF and detector | C7502686 | BAS70, hongjiacheng | Preferred |
| BAV99 | SOT-23, two diodes in series | 2 | front end, 25 MHz oscillator | C2500 | BAV99,215, Nexperia | Basic |

### Crystals (2 parts, 2 types)

| Value | Package | Qty | Blocks | LCSC | Part | Class |
|---|---|---|---|---|---|---|
| 14.31818 MHz | 3225, load 20 pF | 1 | 14.318 MHz oscillator | C34748 | X32251431818MSB4SI, YXC | Extended |
| 25 MHz | 3225, load 12 pF | 1 | 25 MHz oscillator | C9006 | X322525MOB4SI, YXC | Basic |

## Pin order of the parts with three or four pads

| Part | Pin 1 | Pin 2 | Pin 3 | Source |
|---|---|---|---|---|
| 2SC3356 (C28646266) | base | emitter | collector | data sheet of this maker |
| S9018, MMBT3904, MMBT3906 | base | emitter | collector | JLCPCB's symbol for the part |
| BAS70 (C7502686) | anode | not connected | cathode | data sheet of this maker |
| BAV99 (C2500) | anode of diode 1 | cathode of diode 2 | common point | Nexperia's data sheet |
| Both crystals | crystal | ground | crystal (pad 4: ground) | data sheet |

Each BAV99 works as two diodes in opposite directions from a signal node to
ground: pin 3 goes to the node, pins 1 and 2 go to ground.

## Large ceramic capacitors under DC voltage

The 100 µF and 10 µF parts are small ceramic capacitors (X5R). With a DC
voltage across them they hold less than the printed value, and the
simulations use the printed value. So I ran the regulator, power-up and audio
decks again with lower values: 40 µF instead of 100 µF on the 3.3 V rail and
on the audio supply, 5 µF instead of 10 µF at the regulator's reference, 3 µF
instead of 10 µF at the 5 V input. These lower values are estimates for this
kind of part. They are not read from the makers' curves.

Result: the regulator stays stable (no ringing after a load step), the rail
and the supply current do not change, and the audio response moves by
0.01 dB at 320 Hz. One number gets worse: ripple from the DevKitC's 3V3 pin
reaches the rail 44 dB down at 2400 Hz instead of 51 dB. The circuit stays as
it is.

## Inductor quality factors

The quality factor (Q) of an inductor sets how much signal its tuned circuit
loses. The simulation needs Q at the frequency the part works at. The data
sheets give it at another frequency, so the comparison needs a step in
between.

| Inductor | The simulation uses | The data sheet says |
|---|---|---|
| 68 nH, Murata LQW18AN68NG00 | 35 at 138 MHz and at 125 MHz | at least 38 at 200 MHz. Scaled with the square root of frequency: at least 32 at 138 MHz and 30 at 125 MHz. Murata's typical curve for the 75 nH part of the same series lies about 15 % above its minimum |
| 3.3 µH, APV AHW2520C-3R3 | 16 at 12.9 MHz | 22 at 25 MHz. Scaled the same way: 16 at 12.9 MHz |
| 100 µH, TDK NLV32T-101J-EF | 30 at 1.4 MHz | at least 20 at 0.8 MHz. TDK's typical curve for this part: 28.5 at 0.8 MHz and 32.5 at 1.418 MHz |

The values in the simulation are inside what the data sheets support. I also
ran the decks with the parts at their minimum:

- every 68 nH part at its minimum: the front end loses 0.7 dB of gain and
  0.6 dB of image rejection, and the 125 MHz drive falls from 0.36 V to
  0.34 V;
- both 100 µH parts at their minimum (about 23 at 1.4 MHz): the second IF
  loses 1.1 dB and is 140 kHz wide instead of 131 kHz.

The TDK data sheet corrects one assumption. The 100 µH part resonates with
itself at 10 MHz or higher, so it has at most 2.5 pF of self-capacitance. The
simulation assumes 4 pF. With 2 pF the two 1.418 MHz tuned circuits sit about
11 kHz higher (centre 1.428 MHz). The level at the signal changes by +0.3 dB
and the passband stays 130 kHz wide, so the capacitor values stay as they
are. If the centre turns out high on the real board, the spare pad at each
of the two tuned circuits takes a small correction capacitor (about 2 pF).

## Parts that are not in the simulation

The two connector types are not in the cost table below. The order files exist
with and without them ([`../pcb_v2/fabrication`](../pcb_v2/fabrication)); the
order of 2026-11-16 has JLCPCB solder them.

| Part | Qty | Number | State |
|---|---|---|---|
| Antenna connector, SMA, 50 Ω, vertical jack | 1 | LCSC C496549 (BWSMA-KE-Z001) | through-hole, Extended at JLCPCB, allowed in economic assembly, about $0.40 |
| Sockets for the ESP32 DevKitC (38 pins) | 2 | LCSC C2932678 (1 × 19, 2.54 mm, 8.5 mm high) | through-hole, Extended at JLCPCB, allowed in economic assembly, about $0.19 each |
| Spare capacitor pads | 11 | no part | one empty 0603 footprint at each tuned circuit, for a correction capacitor if the tuning is off |
| Test points | | no part | none on the board: the pads of the 0603 parts are large enough to probe |

The ESP32 module itself is "Standard only" at JLCPCB. That is why the DevKitC
stays a separate board.

## Cost

This is my computation, without the connectors. JLCPCB's cart for these files
showed €33.99 on 2026-11-14 (€3.62 for the boards, €30.37 for the assembly),
about €3 below it. The order of 2026-11-16, with JLCPCB also soldering the three
connectors, came to $39.99 in JLCPCB's order list. All cost figures with their
sources are in [`COST.md`](COST.md).

5 boards, 2 of them assembled, economic assembly, all parts on the top side,
2 layers, 100 × 100 mm. Prices in US dollars as JLCPCB shows them;
€1 = $1.1052 (ECB rate of 2026-11-13). Shipping, VAT and duty are not counted.

| Item | USD |
|---|---|
| 5 bare boards, 2 layers, 100 × 100 mm, lead-free finish | 5.30 |
| Assembly setup (economic assembly) | 8.18 |
| Stencil | 1.53 |
| Extended fee, 4 kinds × $3.07 | 12.28 |
| Soldering, 551 joints × 2 boards × $0.0016 | 1.76 |
| Parts for 2 boards, with minimum quantities and spares | 11.56 |
| Placement check by JLCPCB (optional) | 0.45 |
| **Total** | **41.06** (€37.2) |

- **The parts cost more than the first estimate** ($11.56 against about
  $8.50). JLCPCB bills at least 20 pieces of every resistor and small
  capacitor line, also when the two boards need 2. Lines that are billed at
  their minimum make up $4.95 of the $11.56.
- **A fee line that is not counted.** The fee table has a second soldering
  line, "pre-reflow soldering", at $0.016 per joint. My JLCPCB cart for
  another board shows no such fee, so it is left out here.
- **The connectors are not in this table.** If JLCPCB solders the antenna
  connector and the two sockets, two boards cost about $12.70 more: two more
  Extended kinds at $3.07 each, hand-soldering labour $3.58, 86 solder joints
  at $0.0164, and $1.57 for the parts (computed from JLCPCB's fee table as
  read on 2026-11-15; both parts are in stock there and allowed in economic
  assembly).
- The billed quantity per line is the larger of JLCPCB's minimum and
  "needed plus spares". That rule is my reading of their help pages.

## Before ordering

*The boards were ordered on 2026-11-16; this list is kept as it was.*

- Check the stock of the three thin lines again: 3.3 µH (1,385 pieces on
  2026-11-14; two boards need 12), 100 µH (1,002; need 8) and the
  14.31818 MHz crystal (2,957; need 5).
- If the 100 µH is gone: TDK NLCV32T-101K-EF (C165807) has the same
  footprint but ±10 % instead of ±5 %, and the tolerance runs were made
  with ±5 %. If the 3.3 µH is gone: the 0805 part C19633916 has a different
  footprint and a lower self-resonance, so it is not a drop-in.
- ~~Get the real quote and compare it with the table above.~~ Done: €33.99 in
  JLCPCB's cart on 2026-11-14; ordered on 2026-11-16 for $39.99 with the
  connectors (see [`COST.md`](COST.md)).

Edy Grigore
