%% QFH_WIRE_COMPARE - generates 2 .nec files with identical designs that
%  differ only in the conductor diameter, so the bandwidth can be
%  compared directly in 4nec2.
%
%  Open both files in 4nec2 (F2 > Open), run F7 on each, and compare
%  the SWR curves (F5) - e.g. note the frequencies where SWR crosses 2
%  in each case.
%
%  Result observed for this design (0.5 turns, W/H 0.44, 137 MHz band):
%  the difference between 1.78 mm and 2.76 mm wire is negligible - both
%  give SWR ~1.05-1.08 at the target frequency with nearly identical
%  curve widths, so the wire can be chosen on mechanical grounds alone.
clear; clc; close all;

base.freq_mhz    = 137.5;   % target frequency
base.freq_cal    = 1.0223;  % frequency calibration (see README)
base.turns       = 0.5;
base.turn_len_wl = 1.0;
base.bend_r_mm   = 15;
base.ratio       = 0.44;
base.polarity    = 'RHCP';

wires = struct('label', {'FY2.5mm2', 'FY6mm2'}, 'd_mm', {1.78, 2.76});

for k = 1:numel(wires)
    p = base;
    p.wire_d_mm = wires(k).d_mm;
    p = qfh_defaults(p);

    d = qfh_design(p);
    fprintf('\n########## %s (wire %.2f mm) ##########\n', wires(k).label, p.wire_d_mm);
    qfh_report(d, p);

    g = qfh_geometry(d, p);
    necfile = sprintf('QFH_compare_%s_d%.2fmm.nec', wires(k).label, p.wire_d_mm);
    qfh_write_nec(g, d, p, necfile);
end

fprintf('\nDone. Open both QFH_compare_*.nec files in 4nec2 and compare F5 (SWR).\n');
