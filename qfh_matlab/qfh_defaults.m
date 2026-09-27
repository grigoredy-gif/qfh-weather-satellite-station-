function params = qfh_defaults(params)
%QFH_DEFAULTS Fills in missing parameters with defaults and validates them.
%
%   params = QFH_DEFAULTS(params)
%   params = QFH_DEFAULTS()        - all default values
%
%   Main fields:
%     freq_mhz     - target frequency [MHz]
%     freq_cal     - frequency calibration factor (design frequency =
%                    freq_mhz * freq_cal); 1.0 = original Coppens design,
%                    see README "Frequency calibration" for the story
%     turns        - number of turns (twist)
%     turn_len_wl  - length of one turn [wavelengths]
%     bend_r_mm    - bending radius of the corners [mm]
%     wire_d_mm    - conductor diameter [mm]
%     ratio        - width/height ratio
%     polarity     - 'RHCP' (weather satellites) or 'LHCP'
%
%   Advanced fields:
%     c_kms        - speed of light [km/s]; 300000 = the convention used
%                    by the Coppens website (physically 299792.458, the
%                    difference is ~0.07%)
%     feed_len_mm  - length of the feed segment [mm]
%     seg_radial   - NEC segments on the radial arms
%     seg_corner   - NEC segments on each 90-degree corner
%     seg_helix    - NEC segments on the helical section
%     f_start, f_stop, f_step - frequency sweep for the simulation [MHz]
%     show_mast, mast_d_mm    - the mast in the 3D view (visual only)

if nargin == 0, params = struct(); end

params = setdef(params, 'freq_mhz',    137.5);
params = setdef(params, 'freq_cal',    1.0);
params = setdef(params, 'turns',       0.5);
params = setdef(params, 'turn_len_wl', 1.0);
params = setdef(params, 'bend_r_mm',   15);
params = setdef(params, 'wire_d_mm',   1.78);
params = setdef(params, 'ratio',       0.44);
params = setdef(params, 'polarity',    'RHCP');

params = setdef(params, 'c_kms',       300000);
params = setdef(params, 'feed_len_mm', 10);
params = setdef(params, 'seg_radial',  5);
params = setdef(params, 'seg_corner',  5);
params = setdef(params, 'seg_helix',   20);
params = setdef(params, 'f_start',     params.freq_mhz - 5);
params = setdef(params, 'f_stop',      params.freq_mhz + 5);
params = setdef(params, 'f_step',      0.25);
params = setdef(params, 'show_mast',   true);
params = setdef(params, 'mast_d_mm',   25);
params = setdef(params, 'support_d_mm', 15.9);   % 5/8" pipe (template only)
params = setdef(params, 'top_marks', 'cardinal'); % template top holes: 'cardinal'/'exact'

% ----- validation (the ranges from QFH2nec.c, with one exception:
%       wire_d_mm is extended down to 0.5 mm for thin wires; the C code
%       requires >= 1 mm. The deltal compensation table covers 0..16 mm,
%       so the extension is numerically safe) -----
mustbe(params.freq_mhz >= 10 && params.freq_mhz <= 5000, ...
       'freq_mhz outside the range 10..5000 MHz');
mustbe(params.freq_cal >= 0.8 && params.freq_cal <= 1.2, ...
       'freq_cal outside the range 0.8..1.2 (sanity check)');
mustbe(params.turns >= 0.1 && params.turns <= 50, ...
       'turns outside the range 0.1..50');
mustbe(params.turn_len_wl >= 0.1 && params.turn_len_wl <= 5, ...
       'turn_len_wl outside the range 0.1..5');
mustbe(params.bend_r_mm >= 1 && params.bend_r_mm <= 1000, ...
       'bend_r_mm outside the range 1..1000 mm');
mustbe(params.wire_d_mm >= 0.5 && params.wire_d_mm <= 50, ...
       'wire_d_mm outside the range 0.5..50 mm');
mustbe(params.ratio >= 0.1 && params.ratio <= 2, ...
       'ratio outside the range 0.1..2');
mustbe(any(strcmpi(params.polarity, {'RHCP','LHCP'})), ...
       'polarity must be ''RHCP'' or ''LHCP''');
mustbe(params.feed_len_mm > 0, 'feed_len_mm must be > 0');
mustbe(params.mast_d_mm > 0 && params.support_d_mm > 0, ...
       'mast_d_mm and support_d_mm must be > 0');
mustbe(any(strcmpi(params.top_marks, {'cardinal', 'exact'})), ...
       'top_marks must be ''cardinal'' or ''exact''');
mustbe(params.f_step > 0 && params.f_stop >= params.f_start, ...
       'invalid frequency sweep (f_start/f_stop/f_step)');
for f = {'seg_radial', 'seg_corner', 'seg_helix'}
    v = params.(f{1});
    mustbe(v >= 1 && v == round(v), sprintf('%s must be an integer >= 1', f{1}));
end

if params.wire_d_mm > 15
    warning('qfh:wire', ...
        'The Coppens compensation table saturates at 15 mm (15 mm is used effectively).');
end
end

% =========================================================================
function s = setdef(s, f, v)
if ~isfield(s, f) || isempty(s.(f))
    s.(f) = v;
end
end

function mustbe(cond, msg)
if ~cond
    error('qfh:params', '%s', msg);
end
end
