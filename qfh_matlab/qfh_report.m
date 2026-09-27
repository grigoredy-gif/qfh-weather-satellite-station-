function qfh_report(design, params)
%QFH_REPORT Prints the computed dimensions of the QFH antenna.
%   The same table as on John Coppens' website (jcoppens.com/ant/qfh),
%   plus the cutting lengths for construction.

nfo = design.info;
L = nfo.large;
S = nfo.small;

fprintf('\n================ QFH DESIGN @ %.3f MHz ================\n', params.freq_mhz);
if abs(params.freq_cal - 1) > 1e-12
    fprintf(['Frequency calibration: x%.4f -> effective design frequency ' ...
             '%.3f MHz\n(so that the simulated resonance lands on the ' ...
             '%.3f MHz target; see README)\n'], ...
            params.freq_cal, design.f_design_mhz, params.freq_mhz);
end
fprintf('Polarization %s | wire %.2f mm | bend radius %.1f mm | W/H %.2f | %g turns\n', ...
        upper(params.polarity), params.wire_d_mm, params.bend_r_mm, ...
        params.ratio, params.turns);
fprintf('------------------------------------------------------------\n');
fprintf('Wavelength:              %8.1f mm\n', nfo.wavel);
fprintf('Compensated wavelength:  %8.1f mm\n', nfo.wavelc);
fprintf('Bending correction:      %8.1f mm\n', nfo.bendcorr);

fprintf('\n%-36s %11s %11s\n', '', 'LARGE LOOP', 'SMALL LOOP');
rowfmt = '%-36s %11.1f %11.1f\n';
fprintf(rowfmt, 'Total wire length [mm]',            L.total,  S.total);
fprintf(rowfmt, 'Total compensated length [mm]',     L.totalc, S.totalc);
fprintf(rowfmt, 'Vertical separator [mm]',           L.vert,   S.vert);
fprintf(rowfmt, 'Compensated vertical sep. [mm]',    L.vertc,  S.vertc);
fprintf(rowfmt, 'Antenna height H [mm]',             L.H,      S.H);
fprintf(rowfmt, 'Internal diameter Di [mm]',         L.Di,     S.Di);
fprintf(rowfmt, 'Horizontal separator D [mm]',       L.D,      S.D);
fprintf(rowfmt, 'Compensated horizontal Dc [mm]',    L.Dc,     S.Dc);

fprintf('\nWire cutting (physical loop length, no reserve):\n');
fprintf('  large loop: %.0f mm   |   small loop: %.0f mm\n', L.total, S.total);
fprintf('  (add ~30-50 mm of reserve at each end for the connections)\n');
fprintf('============================================================\n');
end
