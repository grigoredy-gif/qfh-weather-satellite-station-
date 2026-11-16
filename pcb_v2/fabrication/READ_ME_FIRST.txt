Files for JLCPCB, receiver version 2. Made by gen/rx2_fab.py from the board file.

Upload:
- rx2_receiver_gerbers_jlc.zip   as the Gerber file
- then ONE of these two pairs as the BOM and as the placement (CPL) file:
  A. JLCPCB also solders the connectors (the SMA jack J101 and the two DevKitC sockets J1001, J1002):
       rx2_receiver_jlc_bom_with_connectors.csv   and   rx2_receiver_jlc_cpl_with_connectors.csv
  B. The connectors are soldered by hand at home:
       rx2_receiver_jlc_bom.csv                   and   rx2_receiver_jlc_cpl.csv

Board settings (option names as on JLCPCB's order page on 2026-11-14):
- Base Material FR-4, Layers 2, PCB Qty 5, Delivery Format Single PCB, PCB Thickness 1.6mm,
  PCB Color Green. The size (100 x 100 mm) comes from the Gerber file.
- Surface Finish: LeadFree HASL (HASL with lead and ENIG also work). NOT OSP, which the page lists
  first: JLCPCB's economic assembly takes only HASL or ENIG on a green 1.6 mm board. With OSP the
  order becomes Standard assembly (quote of 2026-11-14: EUR 143.52 for 2 assembled boards, of which
  EUR 88.46 is a loading fee of about EUR 1.40 for each of the 63 part lines).
- Outer Copper Weight 1 oz, Via Covering Tented, Min via hole size 0.3mm.
- Mark on PCB: Remove Mark. Gold Fingers, Castellated Holes, Edge Plating: No.
- PCB Build Time: a free one. The paid "24 hours" is not needed.
- Leave every other option as the page sets it.
- The board has four mounting holes of 3.2 mm for M3 screws. They are not plated and have their own
  drill file in the zip (rx2_receiver-NPTH.drl). The order page needs no setting for them.

PCB Assembly:
- PCBA Type Economic, Assembly Side Top Side, PCBA Qty 2.
- Confirm Parts Placement: Yes.
- Leave the other assembly options as the page sets them.
- After the upload JLCPCB must find every BOM line: 65 lines (255 parts) with pair A,
  63 lines (252 parts) with pair B. If it marks one as not found or short of stock, do not
  pick a replacement by hand: the circuit is simulated with these parts.
- Pair A costs about 12.70 dollars more than pair B for two boards. This is computed from JLCPCB's fee
  table of 2026-11-15, it is not a quote: two more Extended lines at 3.07 dollars each, hand-soldering
  labour 3.58, 86 solder joints at 0.0164, and the parts (0.40 for a jack, 0.19 for a socket). Both
  connector parts are through-hole, "Extended", and allowed in Economic assembly (JLCPCB's part pages,
  2026-11-15). JLCPCB solders them by hand.

Before paying:
- Look at JLCPCB's placement preview. Every SOT-23 part must sit with its three legs on its three
  pads. The angles in the placement file are already turned to JLCPCB's footprints (180 degrees for C2500, C20526, C7420354, C28646266, C41375130; 270 degrees for C7502686)
  and checked by script against JLCPCB's footprint data. The preview is the only check at JLCPCB itself.
- With pair A also look at the connectors in the preview: the SMA jack on its five holes at the top
  left, and one socket strip on each row of 19 holes at the bottom left.
- Measure the DevKitC that will be plugged in. The board assumes 25.40 mm between its two pin rows.
  With pair A the sockets arrive soldered, so measure before the order.

When the boards arrive:
- Measure with an ohmmeter from the centre of the SMA jack to its shell before anything else: about
  10 kohm is right (R101). The antenna track leaves the jack on the bottom side, so only ground copper
  lies under the metal base of the jack, and no tape is needed there.

Not in any BOM or placement file, on purpose: the 11 spare capacitor positions (not fitted). With
pair B also the SMA jack J101 and the two DevKitC sockets J1001 and J1002.
