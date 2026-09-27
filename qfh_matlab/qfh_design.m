function design = qfh_design(params)
%QFH_DESIGN Computes the dimensions of the QFH antenna.
%
%   design = QFH_DESIGN(params)
%
%   Port of compute_design() from QFH2nec.c
%   (https://github.com/oceantrotter/QFH2nec), which is in turn adapted
%   from John Coppens' QFH calculator (jcoppens.com, qfhcalc.js).
%   All lengths are in mm, measured from the center of the conductor.
%
%   design.loops(1) - SMALL loop (0.975 x lambda_c) - theta0 = 0
%   design.loops(2) - LARGE loop (1.026 x lambda_c) - theta0 = pi/2
%   design.info     - derived dimensions (for the report / construction)
%   design.f_design_mhz - effective design frequency after calibration
%
%   Frequency calibration: the effective design frequency is
%   freq_mhz * freq_cal. The Coppens formulas are empirical and NEC2
%   simulation shows their resonance ~2.2% below the design frequency,
%   so freq_cal = 1.0223 shifts the simulated resonance onto the target
%   (see README). Since the whole geometry scales with the wavelength,
%   this is equivalent to designing at a slightly higher frequency.
%
%   RHCP note: weather satellites transmit RHCP. The resonant QFH
%   radiates in "backfire" mode (the main lobe leaves through the feed
%   end, i.e. upward), and the polarization sense is OPPOSITE to the
%   winding sense of the helix. Therefore, for RHCP toward zenith, the
%   helix winds left (negative turns) - exactly as in QFH2nec.c.

f_design = params.freq_mhz * params.freq_cal;   % effective design frequency
wd    = params.wire_d_mm;
R     = params.bend_r_mm;
ratio = params.ratio;
turns = params.turns;
nrwl  = params.turn_len_wl;

switch upper(params.polarity)
    case 'RHCP', tsign = -1;   % as in QFH2nec.c / the Coppens calculator
    case 'LHCP', tsign = +1;
    otherwise
        error('qfh:polarity', 'polarity must be RHCP or LHCP');
end

wavel  = params.c_kms / f_design;  % wavelength [mm]
wd_eff = min(wd, 15);              % the compensation table saturates at 15 mm
wavelc = nrwl * wavel * deltal(wd_eff);   % compensated wavelength
bendcorr = 2*R - pi*R/2;           % correction for the rounded corners

% --- LARGE loop (electrically longer => resonates below f0) ---
totL  = wavelc * 1.026;
totLc = totL + 4*bendcorr;
DL    = 0.5 * totLc / (1 + sqrt(1/ratio^2 + (turns*pi)^2));
HL    = DL / ratio;

% --- SMALL loop (electrically shorter => resonates above f0) ---
totS  = wavelc * 0.975;
totSc = totS + 4*bendcorr;
DS    = 0.5 * totSc / (1 + sqrt(1/ratio^2 + (turns*pi)^2));
HS    = DS / ratio;

% geometric sanity checks (the small loop is the binding one: DS<DL, HS<HL)
if DS/2 <= R
    error('qfh:geom', ...
        'The bending radius (%.1f mm) is too large for the loop diameter (%.1f mm).', R, DS);
end
if HS <= 2*R
    error('qfh:geom', ...
        ['The small loop height (%.1f mm) must be > 2 x the bending radius ' ...
         '(%.1f mm), otherwise the helix self-intersects. Reduce bend_r_mm or ratio.'], HS, 2*R);
end
if params.feed_len_mm/2 >= DS/2 - R
    error('qfh:geom', ...
        'feed_len_mm (%.1f mm) is too large for the loop (maximum %.1f mm).', ...
        params.feed_len_mm, 2*(DS/2 - R));
end

% the order (small, then large) and theta0 are identical to QFH2nec.c
loops(1) = mkloop(HS, DS, R, tsign*turns, 0,    wd/2, 'small loop');
loops(2) = mkloop(HL, DL, R, tsign*turns, pi/2, wd/2, 'large loop');

info.wavel    = wavel;
info.wavelc   = wavelc;
info.bendcorr = bendcorr;
info.large    = mkinfo(totL, totLc, DL, HL, R, wd);
info.small    = mkinfo(totS, totSc, DS, HS, R, wd);

design.loops        = loops;
design.info         = info;
design.f_design_mhz = f_design;
design.params       = params;
end

% =========================================================================
function lp = mkloop(H, D, R, turns, theta0, wire_r, name)
lp = struct('H', H, 'D', D, 'R', R, 'turns', turns, 'theta0', theta0, ...
            'offset', 0, 'wire_r', wire_r, 'name', name);
end

function s = mkinfo(total, totalc, D, H, R, wd)
s.total  = total;             % electrical length of the loop wire
s.totalc = totalc;            % total compensated length
s.D      = D;                 % horizontal separator (center-to-center)
s.H      = H;                 % loop height
s.vert   = (totalc - 2*D)/2;  % vertical separator
s.vertc  = s.vert - 2*R;      % compensated vertical separator
s.Di     = D - wd;            % internal diameter (between inner faces)
s.Dc     = D - 2*R;           % compensated horizontal separator
end

function v = deltal(diam)
% lengthening factor as a function of conductor diameter [mm]
% (original table from qfhcalc.js / John Coppens; index 0..16 mm)
tbl = [1.045 1.053 1.060 1.064 1.068 1.070 1.070 1.071 ...
       1.071 1.070 1.070 1.070 1.070 1.069 1.069 1.068 1.067];
k = floor(diam);                                   % integer part, 0..15
v = tbl(k+1) + (tbl(k+2) - tbl(k+1)) * (diam - k); % linear interpolation
end
