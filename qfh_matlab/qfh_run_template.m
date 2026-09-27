%% QFH_RUN_TEMPLATE - drilling table + printable 1:1 A4 template (PDF)
%  Uses the same design parameters as qfh_main.m (target 137.5 MHz with
%  frequency calibration, 1.78 mm wire), plus the real mast and support
%  tube diameters of the build.
%
%  The template layout is inspired by the printable template of John
%  Coppens' QFH design tool (jcoppens.com/ant/qfh) - see
%  qfh_write_template.m for details and credit.
clear; clc; close all;

params.freq_mhz     = 137.5;   % target frequency
params.freq_cal     = 1.0223;  % frequency calibration (see README)
params.turns        = 0.5;
params.turn_len_wl  = 1.0;
params.bend_r_mm    = 15;
params.ratio        = 0.44;
params.wire_d_mm    = 1.78;    % FY 2.5 mm^2 solid copper wire
params.polarity     = 'RHCP';
params.mast_d_mm    = 102.5/pi; % <-- from the MEASURED outer circumference: 102.5 mm.
                                %     (wrap test: the printed 100.5 mm strip came up
                                %     exactly 2 mm short - wrapping beats a ruler on
                                %     a round pipe, so trust the wrap measurement)
params.support_d_mm = 15.9;    % <-- your support tube diameter (5/8" pipe)
params.top_marks    = 'cardinal'; % top holes on the loop axes (Coppens-style,
                                  % easier build); 'exact' = simulated crossings

params = qfh_defaults(params);
design = qfh_design(params);

marks = qfh_drill_marks(design, params);

fprintf('\n=============== HOLES TO DRILL (top to bottom) ===============\n');
fprintf('%-6s %-8s %9s %10s %15s %7s\n', 'loop', 'position', 'depth[mm]', 'hole[mm]', 'angles[deg]', 'arms');
for i = 1:numel(marks)
    m = marks(i);
    fprintf('%-6s %-8s %9.1f %10.2f   %5.1f / %5.1f   %s / %s\n', ...
        m.loop, m.position, m.depth_mm, m.hole_d_mm, ...
        m.angles_deg(1), m.angles_deg(2), m.arms{1}, m.arms{2});
end
fprintf('==============================================================\n');
fprintf('top/bottom = wire pass-through holes; middle = support tube holes.\n');

qfh_write_template(marks, params, 'QFH_drill_template.pdf');
