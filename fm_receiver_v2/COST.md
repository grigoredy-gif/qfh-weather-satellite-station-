# Cost: from about €140 to about €36

**In short.** Having JLCPCB assemble two boards of receiver version 1 was
quoted at about €140. Version 2 was ordered on 16 November 2026 for $39.99
(about €36): five boards, two of them assembled, with the three connectors
soldered on as well. Both figures are without shipping and tax.

The saving does not come from cheaper transistors. It comes from designing the
receiver around the way the factory charges: no parts that need a person
(hand-wound coils, trimmers to adjust), almost only parts that carry no extra
fee, the cheaper of JLCPCB's two assembly services, and a small board.

This page has every figure with its source, then the price rules, then each
step that lowered the cost. The per-part cost sheet is in [`PARTS.md`](PARTS.md).

## The figures

| What | Price | Kind of figure | Date | Source |
|---|---|---|---|---|
| Version 1: 2 boards assembled by JLCPCB | about €140 | JLCPCB quote (its line items and assembly type were not recorded) | 2026-11-07 | [`../pcb/DESIGN_LOG.md`](../pcb/DESIGN_LOG.md), "the cost-down" |
| Version 1 by hand: 5 bare boards, plus LCSC parts for 2 boards | about €12, plus about $55 | JLCPCB quote for the boards; the parts list priced in LCSC's BOM tool | 2026-11-07 | [`../pcb/README.md`](../pcb/README.md), "Ordering". The coil cores, wire, one SMA jack, shipping and VAT come on top |
| Version 2, first try with the OSP surface finish: assembly of 2 boards | €143.52 (€88.46 of it a loading fee for the 63 part lines), plus €8.42 for the 5 boards | JLCPCB quote | 2026-11-14 | [`../pcb_v2/fabrication/READ_ME_FIRST.txt`](../pcb_v2/fabrication/READ_ME_FIRST.txt) |
| Version 2 without the connectors: 5 boards, 2 assembled | $41.06 = €37.2 | my computation from JLCPCB's fee table | 2026-11-14 | [`PARTS.md`](PARTS.md), "Cost" |
| The three connectors soldered by JLCPCB on 2 boards | about $12.70 more | my computation | 2026-11-15 | [`PARTS.md`](PARTS.md), "Cost" |
| Version 2 without the connectors: 5 boards, 2 assembled, HASL finish | €3.62 boards + €30.37 assembly = €33.99 | JLCPCB cart | 2026-11-14 | my cart (screenshot, not published) |
| Version 2 with the connectors: 5 boards, 2 assembled | $4.00 boards + $40.13 assembly = $44.13 | JLCPCB cart | 2026-11-15/16 | my cart (screenshot, not published) |
| Version 2 without the connectors, all 5 boards assembled | $4.00 boards + $44.47 assembly = $48.47 | JLCPCB cart | 2026-11-15/16 | my cart (screenshot, not published) |
| **Version 2, ordered: 5 boards, 2 assembled, with the connectors** | **$3.63 boards + $36.36 assembly = $39.99 (about €36)** | **JLCPCB order list** | **2026-11-16** | my order list (screenshot, not published) |

All prices are without shipping, VAT and import duty; the order list does not
show those. Dollars to euros at €1 = $1.1052 (ECB rate of 2026-11-13). The ESP32
DevKitC is not included anywhere.

Three things about these figures that I cannot fully explain:

- **Order list against cart.** The order list shows lower prices than the cart
  did for the same files: $3.63 instead of $4.00 for the boards, and $36.36
  instead of $40.13 for the assembly. I do not know why.
- **Cart against my computation.** Without the connectors I computed $41.06;
  the cart showed €33.99 (about $37.60). With the connectors I computed about
  $53.80; the cart showed $44.13. I do not have the cart line by line, so I can
  point to only one difference: the five bare boards were $4.00 in the cart and
  $5.30 in my computation.
- **What the connectors cost.** The cart showed €30.37 for assembling two
  boards without them (14 November) and $40.13 with them (15 or 16 November).
  At the cart's own exchange rate (€3.62 = $4.00) that is $33.57 against
  $40.13: about $6.60 for the three connectors on two boards.

The boards have not arrived yet, so it is still possible that something on the
bench costs extra (a second order, a rework part).

## How JLCPCB charges for assembly

These are the rules as I read them on JLCPCB's price pages on 13 to
15 November 2026. They change from time to time.

- **Two assembly services.** "Economic" assembly: $8.18 setup and $1.53 for the
  stencil per order. "Standard" assembly: $25.56 setup, $8.21 for the stencil,
  and $1.53 for every different part type on the board.
- **What forces Standard assembly.** A single part marked "Standard only" in
  JLCPCB's library, or a board option that Economic assembly does not take. On
  a green 1.6 mm board, Economic assembly takes only the HASL or ENIG surface
  finish. The order page offers OSP first.
- **Part classes.** "Basic" parts are free to place. "Preferred" parts are free
  in Economic assembly. Every other part is "Extended" and costs $3.07 per
  part type, however many pieces of it there are.
- **Soldering.** $0.0016 per joint for parts the machine places. Through-hole
  parts are soldered by hand: $3.58 per order plus $0.0164 per joint.
- **Parts.** JLCPCB sells at least about 20 pieces of each cheap resistor or
  capacitor, also when two boards need 2.
- **The board.** Five 2-layer boards up to 100 × 100 mm cost $5.30 in the
  table I used; above about 102 mm the price jumps to $11 to $13.

## Where the saving comes from

### 1. Economic assembly instead of Standard assembly

This is the largest single step. Standard assembly charges for every part
type. The first quote for version 2 was made with the OSP finish, which the
order page offers first, and it came out as Standard assembly: €143.52 for
assembling two boards, of which €88.46 was a loading fee of about €1.40 for
each of the 63 part lines. The same files with the HASL finish came out as
Economic assembly: €30.37 in the cart for assembling two boards.

Version 1's quote of about €140 was probably also Standard assembly: one of its
parts, a 100 µF capacitor, is "Standard only" at JLCPCB. Version 2 has no such
part. The ESP32 module itself is "Standard only" too, which is one reason the
ESP32 stays on its own DevKitC board, plugged into two sockets.

### 2. No coils to wind and no trimmers

Version 1 has 11 coils wound by hand (7 on toroid cores, 4 air coils) and
11 trimmer capacitors. A factory cannot wind the coils, and every trimmer has
to be set by hand on the bench. Trimmers were also among the dearest small
parts: from $0.49 to $3.63 each.

Version 2 uses 11 small SMD inductors in three values and fixed capacitors
only. That is possible only because every tuned circuit is wide enough that
parts within their tolerance cannot push it off the signal: with ±5 % parts
and nothing to adjust, a tuned circuit needs a loaded Q below about 10. At
12.9 MHz that makes it about 1.3 MHz wide, for a signal that needs only about
43 kHz, so far too much noise would get through. Version 2 therefore converts
the signal a second time, to 1.418 MHz, where the same Q gives about 130 kHz.
The [README](README.md#what-the-simulation-shows) shows the tolerance runs
behind this.

### 3. Parts chosen from JLCPCB's fee-free classes

Of the 63 part lines, 48 are Basic and 11 are Preferred, so 59 carry no fee.
Four are Extended: the three inductor values (68 nH, 3.3 µH and 100 µH) and
the 14.31818 MHz crystal. That is 4 × $3.07 = $12.28. Many values in the
circuit were chosen so that a Basic part exists for them.

Version 1 went the same way late, in its own cost-down of 7 November: its
Extended lines went from 19 to 8 (my count then; a later check at JLCPCB found
10), and the computed cost of parts and fees for two boards from about $124 to
about $50. The quote that followed was still about €140.

### 4. A small board

Version 2 is 100 × 100 mm, the largest size in JLCPCB's cheapest price step.
Version 1 is 210 × 75 mm.

### 5. Parts on one side only

Every part of version 2 is on the top side. JLCPCB assembles one side, with one
stencil.

### 6. The connectors: soldered by JLCPCB after all

The SMA antenna jack and the two socket strips for the DevKitC are through-hole
parts. JLCPCB solders those by hand and charges for it: two more Extended part
types, $3.58 per order and a fee per joint. My computation from the fee table
said $12.70 for two boards, so at first I planned to solder them myself. In
the cart the difference was about $6.60, so the order includes them. This is
not a saving; it is a convenience that costs little.

## What did not get cheaper

- The parts themselves cost a little more than first estimated: $11.56 instead
  of about $8.50, because JLCPCB sells at least about 20 pieces of each cheap
  line. Lines billed at their minimum make up $4.95 of the $11.56.
- Version 2 has more parts than version 1 (255 with the connectors, against
  205), because it has a second mixer, a second oscillator, a regulator and two
  bias references. The joint fee is so low that this costs less than $2.

## Not counted anywhere above

My own time, the test equipment (I use a multimeter, an oscilloscope and an
ADALM-Pluto that I already have), the ESP32 DevKitC, shipping and tax.

Edy Grigore
