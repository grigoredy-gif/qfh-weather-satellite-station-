* rx2_blk_bias.inc - the two bias references
* Nodes: vcc, vb, vbd
* vb (about 1.17 V): shared by every emitter-coupled pair, both mixers and the squarer's current source.
*   One MMBT3904 connected as a diode on top of a 270 ohm resistor. The voltage across a stage's tail resistor is
*   vb minus one base-emitter drop, so the two junction drops cancel and what is left is the resistor drop
*   (about 0.5 V, a fixed fraction of the rail). Stage currents hold within a few percent over temperature.
* vbd (about 1.27 V): for the pump driver (pair C in rx2_blk_if2.inc) only. An MMBT3904 and an MMBT3906 as diodes
*   in series. The charge pump loses two junction drops per cycle (its Schottky diode and its PNP), and those
*   drops fall as the board warms up. vbd falls with them, so the square wave shrinks by the same amount and
*   the detector output stays where it is.
Rref vcc vb 1.1k
Qref vb vb vbr 0 QN
Rrefs vbr 0 270
Cref vb 0 10u
Rrefd vcc vbd 4.7k
Qrd1 vbd vbd vbdm 0 QN
Qrd2 0 0 vbdm 0 QP
Crefd vbd 0 10u
