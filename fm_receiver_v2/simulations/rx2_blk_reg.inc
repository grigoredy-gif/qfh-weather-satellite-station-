* rx2_blk_reg.inc - 3.3 V rail: discrete regulator that copies the DevKitC's 3V3 pin
* Nodes: v5 (DevKitC 5V pin, 4.2 to 5 V), v3ref (DevKitC 3V3 pin), vcc (receiver rail, about 3.28 V)
* The power comes from the 5V pin through the PNP pass transistor Qrp. The voltage is set by the 3V3 pin,
* filtered by Rr1 and Cr (7 Hz), so the ESP32's own supply noise does not reach the receiver.
* Qre1 and Qre2 compare the rail with that reference and drive Qrp. Rrs and Qrl limit the current to about 65 mA.
Rrs v5 pe 10
Qrl pb pe v5 0 QP
Qrp vcc pb pe 0 QP
Rpb pe pb 1.5k
Qre1 pb vref ret 0 QN
Qre2 pe vcc ret 0 QN
Rret ret 0 1.2k
Rr1 v3ref vref 2.2k
Cr vref 0 10u
Cin v5 0 10u
Cout vcc 0 100u Rser=5m
