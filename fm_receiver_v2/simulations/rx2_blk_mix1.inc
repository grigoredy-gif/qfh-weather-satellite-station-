* rx2_blk_mix1.inc - first mixer: 137.9 MHz in, 12.9 MHz out into tuned circuit T1
* Single-balanced, three RF transistors: the circuit of version 1, re-biased for 3.3 V.
* Nodes: m1in (signal in), lo1 (125 MHz drive), t1 (output: collector feeds T1 of the first-IF strip), vcc, vb
* Qx turns the input voltage into a current; Qxa/Qxb switch it at the LO rate.
* Rsta, the snubber Rsnb + Csnb and Rcxa are the UHF stability parts version 1 needed for this transistor pair.
Cx1 m1in bx 100p
Rbx vb bx 10k
Qx qxc qxb qxe 0 QRF
Xqx_x emx bx ex1 qxc qxb qxe SOT23X PKG={pkg}
Rex1 ex1 ex2 100
Rex2 ex2 0 200
Cex2 ex2 0 1n
* switching pair, bases at about 2.0 V
Rsx1 vcc vbx 10k
Rsx2 vbx 0 15k
Cvbx vbx 0 100n
Rbxa vbx bxa 10k
Rbxb vbx bxb 10k
Cbxb bxb bxbg 1n Rser=0.15
Lbxb_x bxbg 0 0.7n
Rsnb bxb snb 47
Csnb snb 0 1n
Clo1 lo1 lo1c 100p
Rsta lo1c bxa 47
Qxa qxac qxab qxae 0 QRF
Xqxa_x cxa bxa emx qxac qxab qxae SOT23X PKG={pkg}
Rcxa vfx cxa 100
Qxb qxbc qxbb qxbe 0 QRF
Xqxb_x t1 bxb emx qxbc qxbb qxbe SOT23X PKG={pkg}
Rfx vcc vfx 47
Cfx2 vfx 0 100n
* Lbxb_x is a layout estimate (via inductance of the base bypass capacitor), not a part.
