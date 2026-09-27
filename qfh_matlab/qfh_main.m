%% ========================================================================
%  QFH_MAIN - QFH (Quadrifilar Helix) antenna generator for 137 MHz
%             weather satellites
%  ------------------------------------------------------------------------
%  Project: reception of 137 MHz weather-satellite imagery (RHCP),
%  receiver: ADALM-Pluto SDR. This script generates the antenna design,
%  a 3D preview in MATLAB, and a .nec file for simulation in 4nec2.
%
%  ATTRIBUTION: this is a MATLAB port that relies heavily on existing
%  work; no credit is claimed for the underlying design method:
%    - design formulas and compensation tables: John Coppens' QFH
%      calculator, https://www.jcoppens.com/ant/qfh/calc.en.php
%    - geometry construction and NEC export: QFH2nec.c,
%      https://github.com/oceantrotter/QFH2nec (GPL-3.0), itself based
%      on helix2nec, https://uuki.kapsi.fi/qha_simul.html
%  See README.md for the full reference list and the documented
%  differences from the originals.
%
%  Pipeline (each step is a separate .m subprogram):
%    1. qfh_defaults  - fills in / validates the parameters
%    2. qfh_design    - computes the antenna dimensions (port of the
%                       John Coppens calculator / QFH2nec.c)
%    3. qfh_report    - prints the dimension table (same as the website)
%    4. qfh_geometry  - builds the 3D geometry (wire list)
%    5. qfh_plot3d    - 3D visualization in MATLAB
%    6. qfh_write_nec - exports the .nec file for simulation in 4nec2
%
%  Automatic checks: run  >> qfh_selftest
%  ========================================================================
clear; clc; close all;

% --------------------------- DESIGN PARAMETERS ---------------------------
params.freq_mhz    = 137.5;  % TARGET frequency [MHz]
                             % NOTE (2026): the NOAA POES satellites (APT on
                             % 137.1 / 137.62 / 137.9125 MHz) were
                             % decommissioned in June-August 2025 and no
                             % longer transmit. The current targets in the
                             % 137 MHz band are Meteor-M N2-3 / N2-4 (LRPT,
                             % digital) on 137.1 and 137.9 MHz, also RHCP,
                             % so 137.5 remains a good band-center choice.

% Frequency calibration factor (see README, "Frequency calibration").
% The Coppens formulas are empirical: NEC2 simulation of the geometry
% they produce shows the actual resonance about 2.2% BELOW the design
% frequency (a 137.5 MHz design resonates at ~134.5 MHz). This factor
% scales the design internally so the SIMULATED resonance lands on the
% requested target frequency:
%   1.0223 = 137.5 / 134.5   (measured in 4nec2, free space; verified
%                             for both 1.78 mm and 7 mm conductors)
% Set it to 1.0 to reproduce the original, uncorrected Coppens/QFH2nec
% design (that is also what qfh_selftest uses to match the website).
params.freq_cal    = 1.0223;

params.turns       = 0.5;    % number of turns (twist)
params.turn_len_wl = 1.0;    % length of one turn [wavelengths]
params.bend_r_mm   = 15;     % bending radius of the 90-degree corners [mm]
params.ratio       = 0.44;   % width/height ratio

% Conductor diameter [mm] - SOLID copper installation wire (Romanian
% "FY" type, equivalent to H07V-U solid wire):
%   FY 1.5 mm^2  ->  d = 1.38 mm
%   FY 2.5 mm^2  ->  d = 1.78 mm   <- most common in house wiring
%   FY 4.0 mm^2  ->  d = 2.26 mm
%   FY 6.0 mm^2  ->  d = 2.76 mm
% Measure your wire with a caliper (WITHOUT insulation!) and put the
% exact value here:
params.wire_d_mm   = 1.78;

% Polarization: weather satellites transmit RHCP -> leave 'RHCP'
params.polarity    = 'RHCP';

% ---------------------- ADVANCED PARAMETERS (optional) -------------------
% If you do not set them here, qfh_defaults fills in these defaults:
% params.c_kms       = 300000; % speed of light [km/s] (Coppens convention)
% params.feed_len_mm = 10;     % length of the feed segment [mm]
% params.seg_radial  = 5;      % NEC segments on the radial arms
% params.seg_corner  = 5;      % NEC segments on each 90-degree corner
% params.seg_helix   = 20;     % NEC segments on the helical section
% params.f_start / params.f_stop / params.f_step   % frequency sweep [MHz]

params = qfh_defaults(params);

% ------------------------------- PIPELINE --------------------------------
design = qfh_design(params);          % 1) antenna dimensions
qfh_report(design, params);           % 2) construction table

geom = qfh_geometry(design, params);  % 3) 3D geometry (wires)

pngfile = sprintf('QFH_%.1fMHz_d%.2fmm.png', params.freq_mhz, params.wire_d_mm);
qfh_plot3d(geom, design, params, pngfile);   % 4) 3D view + PNG

necfile = sprintf('QFH_%.1fMHz_d%.2fmm.nec', params.freq_mhz, params.wire_d_mm);
qfh_write_nec(geom, design, params, necfile); % 5) export for 4nec2

fprintf('\nDone! Open "%s" in 4nec2 (File > Open) and run the simulation (F7).\n', necfile);
fprintf('Check: SWR/impedance at %.1f MHz and the far-field pattern (RHCP gain toward zenith).\n', params.freq_mhz);
