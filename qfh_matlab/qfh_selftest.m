function qfh_selftest
%QFH_SELFTEST Automatic checks for the qfh_matlab pipeline.
%
%   A) the design reproduces the values of the Coppens calculator
%      (reference screenshot: 137.5 MHz, 7 mm conductor, ratio 0.44,
%      freq_cal = 1.0 i.e. the original, uncalibrated formulas)
%   B) the 3D geometry is continuous and has the correct dimensions
%   C) the exported .nec file is structurally valid
%   D) the frequency calibration behaves as documented (a design at
%      target f with freq_cal c is identical to an uncalibrated design
%      at f*c)
%
%   Run:  >> qfh_selftest

fails  = 0;
ntests = 0;

fprintf('=================== QFH SELFTEST ===================\n');

%% --- A: design vs. the Coppens calculator (d = 7 mm) ---
fprintf('--- A: design vs. the Coppens calculator (d=7 mm) ---\n');
pa = qfh_defaults(struct('freq_mhz', 137.5, 'turns', 0.5, 'turn_len_wl', 1, ...
                         'bend_r_mm', 15, 'wire_d_mm', 7, 'ratio', 0.44));
da = qfh_design(pa);
ia = da.info;  L = ia.large;  S = ia.small;

check('wavelength',                  ia.wavel,    2181.8, 0.12);
check('compensated wavelength',      ia.wavelc,   2336.7, 0.12);
check('bending correction',          ia.bendcorr, 6.4,    0.06);
check('large: total length',         L.total,     2397.4, 0.12);
check('large: vertical separator',   L.vert,      889.6,  0.12);
check('large: compensated length',   L.totalc,    2423.2, 0.12);
check('large: comp. vertical sep.',  L.vertc,     859.6,  0.12);
check('large: antenna height H1',    L.H,         731.8,  0.12);
check('large: internal diam. Di1',   L.Di,        315,    0.6);
check('large: horizontal sep. D1',   L.D,         322,    0.6);
check('large: comp. horizontal Dc1', L.Dc,        292,    0.6);
check('small: total length',         S.total,     2278.3, 0.12);
check('small: vertical separator',   S.vert,      845.8,  0.12);
check('small: compensated length',   S.totalc,    2304,   0.6);
check('small: comp. vertical sep.',  S.vertc,     815.8,  0.12);
check('small: antenna height H2',    S.H,         695.8,  0.12);
check('small: internal diam. Di2',   S.Di,        299.1,  0.12);
check('small: horizontal sep. D2',   S.D,         306.1,  0.12);
check('small: comp. horizontal Dc2', S.Dc,        276.1,  0.12);

%% --- B: geometry continuity (default parameters, 1.8 mm wire) ---
fprintf('--- B: geometry continuity ---\n');
pb = qfh_defaults(struct('wire_d_mm', 1.8));
db = qfh_design(pb);
gb = qfh_geometry(db, pb);

nwl = 3 + 4*pb.seg_corner + 2*pb.seg_helix;   % wires per loop
checktrue('total number of wires', numel(gb.wires) == 2*nwl + 1);
checktrue('feed_idx is the last wire', gb.feed_idx == numel(gb.wires));

for k = 1:2
    base = (k-1)*nwl;
    armA = [base+1, base+(3:2:nwl-1)];
    armB = [base+2, base+(4:2:nwl-1)];
    ok = true;
    for j = 1:numel(armA)-1
        ok = ok && norm(gb.wires(armA(j)).p2 - gb.wires(armA(j+1)).p1) < 1e-9;
        ok = ok && norm(gb.wires(armB(j)).p2 - gb.wires(armB(j+1)).p1) < 1e-9;
    end
    checktrue(sprintf('loop %d: helix arms are continuous', k), ok);

    wbot = gb.wires(base + nwl);
    checktrue(sprintf('loop %d: bottom radial connects to both arms', k), ...
        norm(wbot.p1 - gb.wires(armA(end)).p2) < 1e-9 && ...
        norm(wbot.p2 - gb.wires(armB(end)).p2) < 1e-9);

    zz = arrayfun(@(w) min(w.p1(3), w.p2(3)), gb.wires(base + (1:nwl)));
    check(sprintf('loop %d: depth = -H', k), min(zz), -db.loops(k).H, 1e-9);

    % on the helical section the radius must be exactly D/2
    hix = base + (2 + 2*pb.seg_corner) + (1:2*pb.seg_helix);
    rr  = arrayfun(@(w) hypot(w.p2(1), w.p2(2)), gb.wires(hix));
    check(sprintf('loop %d: helix radius = D/2', k), ...
          max(abs(rr - db.loops(k).D/2)), 0, 1e-9);

    % physical conductor length ~ designed electrical length
    Ltot = sum(arrayfun(@(w) norm(w.p2 - w.p1), gb.wires(base + (1:nwl))));
    if k == 1, ref = db.info.small.total; else, ref = db.info.large.total; end
    checktrue(sprintf('loop %d: wire length %.0f mm ~ designed %.0f mm', k, Ltot, ref), ...
              abs(Ltot - ref)/ref < 0.015);
end

fw = gb.wires(gb.feed_idx);
check('feed wire length', norm(fw.p2 - fw.p1), pb.feed_len_mm, 1e-9);

%% --- C: structurally valid .nec file ---
fprintf('--- C: the .nec file ---\n');
necf = fullfile(tempdir, 'qfh_selftest.nec');
qfh_write_nec(gb, db, pb, necf);

txt = string(splitlines(strtrim(fileread(necf))));
gwl = cellstr(txt(startsWith(txt, 'GW ')));
checktrue('number of GW lines', numel(gwl) == numel(gb.wires));
checktrue('first line is CM', startsWith(txt(1), 'CM'));
checktrue('CE present', any(strcmp(txt, 'CE')));
checktrue('GE 0 present', any(strcmp(txt, 'GE 0')));
checktrue('last line is EN', strcmp(txt(end), 'EN'));

exl = txt(startsWith(txt, 'EX '));
checktrue('exactly one EX card', numel(exl) == 1);
ext = sscanf(char(exl(1)), 'EX %d %d');
checktrue('EX is on the feed wire', ext(2) == gb.feed_idx);

frl = txt(startsWith(txt, 'FR '));
frv = sscanf(char(frl(1)), 'FR %d %d');
checktrue('FR has 41 frequencies (f0 +/- 5 MHz, 0.25 step)', frv(2) == 41);

gwnum = cellfun(@(s) sscanf(s, 'GW %f %f %f %f %f %f %f %f %f'), gwl, ...
                'UniformOutput', false);
checktrue('all GW have 9 numeric fields', all(cellfun(@numel, gwnum) == 9));
allv = [gwnum{:}];
checktrue('all GW values are finite', all(isfinite(allv(:))));
checktrue('wire radius in .nec = d/2 [m]', ...
          all(abs(allv(9,:) - pb.wire_d_mm/2000) < 1e-12));

%% --- D: frequency calibration ---
fprintf('--- D: frequency calibration ---\n');
cal = 1.0223;
pd1 = qfh_defaults(struct('freq_mhz', 137.5, 'freq_cal', cal));
pd2 = qfh_defaults(struct('freq_mhz', 137.5 * cal));
dd1 = qfh_design(pd1);
dd2 = qfh_design(pd2);
check('effective design frequency recorded', dd1.f_design_mhz, 137.5*cal, 1e-9);
check('calibrated D (small) = uncalibrated D at f*cal', ...
      dd1.loops(1).D, dd2.loops(1).D, 1e-9);
check('calibrated H (small) = uncalibrated H at f*cal', ...
      dd1.loops(1).H, dd2.loops(1).H, 1e-9);
check('calibrated D (large) = uncalibrated D at f*cal', ...
      dd1.loops(2).D, dd2.loops(2).D, 1e-9);
check('calibrated H (large) = uncalibrated H at f*cal', ...
      dd1.loops(2).H, dd2.loops(2).H, 1e-9);
checktrue('default freq_cal is 1.0 (faithful Coppens design)', ...
          qfh_defaults().freq_cal == 1.0);

%% --- E: drilling marks (Coppens-style template geometry) ---
fprintf('--- E: drilling marks ---\n');
pe = qfh_defaults(struct('wire_d_mm', 1.78, 'mast_d_mm', 32, 'support_d_mm', 15.9));
de = qfh_design(pe);
me = qfh_drill_marks(de, pe);

checktrue('6 hole stations (3 per loop)', numel(me) == 6);
okpair = true;
for i = 1:numel(me)
    okpair = okpair && abs(mod(me(i).angles_deg(2) - me(i).angles_deg(1), 360) - 180) < 1e-9;
end
checktrue('every hole pair is 180 deg apart', okpair);

for k = 1:2
    if k == 1, nm = 'small'; else, nm = 'large'; end
    sel = me(strcmp({me.loop}, nm));
    dt = sel(strcmp({sel.position}, 'top')).depth_mm;
    dm = sel(strcmp({sel.position}, 'middle')).depth_mm;
    db = sel(strcmp({sel.position}, 'bottom')).depth_mm;
    check(sprintf('%s loop: top depth = 0', nm),      dt, 0,                  1e-9);
    check(sprintf('%s loop: middle depth = H/2', nm), dm, de.loops(k).H/2,    1e-9);
    check(sprintf('%s loop: bottom depth = H', nm),   db, de.loops(k).H,      1e-9);

    % default 'cardinal' convention: top holes on the loop axis (theta0)
    aT = sel(strcmp({sel.position}, 'top')).angles_deg(1);
    check(sprintf('%s loop: top hole on the cardinal axis', nm), ...
          aT, mod(de.loops(k).theta0*180/pi, 360), 1e-9);
end

% 'exact' mode: the top hole must lie ON the slanted radial wire segment
px = pe;  px.top_marks = 'exact';
mx = qfh_drill_marks(de, px);
for k = 1:2
    if k == 1, nm = 'small'; else, nm = 'large'; end
    lp = de.loops(k);
    if k == 1, af = lp.theta0 + pi/4; else, af = lp.theta0 - pi/4; end
    P = px.feed_len_mm/2 * [cos(af), sin(af)];
    Q = (lp.D/2 - lp.R) * [cos(lp.theta0), sin(lp.theta0)];
    selx = mx(strcmp({mx.loop}, nm));
    aT = selx(strcmp({selx.position}, 'top')).angles_deg(1);
    W = px.mast_d_mm/2 * [cosd(aT), sind(aT)];
    dPQ = Q - P;  dPW = W - P;
    crossz = dPQ(1)*dPW(2) - dPQ(2)*dPW(1);
    tproj  = dot(dPW, dPQ) / dot(dPQ, dPQ);
    checktrue(sprintf('%s loop (exact mode): top hole on the radial wire', nm), ...
              abs(crossz)/norm(dPQ) < 1e-9 && tproj > 0 && tproj < 1);
end

okd = true;
for i = 1:numel(me)
    if strcmp(me(i).position, 'middle')
        okd = okd && me(i).hole_d_mm == pe.support_d_mm;
    else
        okd = okd && me(i).hole_d_mm == pe.wire_d_mm;
    end
end
checktrue('hole diameters: wire at top/bottom, support at middle', okd);

%% --- summary ---
fprintf('====================================================\n');
if fails == 0
    fprintf('ALL %d tests PASSED.\n', ntests);
else
    error('qfh:selftest', '%d of %d tests FAILED.', fails, ntests);
end

% ----------------------------- helpers ----------------------------------
    function check(name, got, want, tol)
        ntests = ntests + 1;
        if abs(got - want) <= tol
            fprintf('  PASS  %s (%.4g)\n', name, got);
        else
            fails = fails + 1;
            fprintf('  FAIL  %s: got %.6g, expected %.6g (tol %g)\n', ...
                    name, got, want, tol);
        end
    end

    function checktrue(name, cond)
        ntests = ntests + 1;
        if cond
            fprintf('  PASS  %s\n', name);
        else
            fails = fails + 1;
            fprintf('  FAIL  %s\n', name);
        end
    end
end
