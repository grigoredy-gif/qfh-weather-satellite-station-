function marks = qfh_drill_marks(design, params)
%QFH_DRILL_MARKS Drilling positions (depth + angles) on the mast.
%
%   marks = QFH_DRILL_MARKS(design, params)
%
%   Follows the classic construction used by John Coppens' QFH design
%   tool (https://www.jcoppens.com/ant/qfh):
%     - TOP:    the four top radial wires pass straight through the mast
%               wall (small holes at the wire diameter, all at depth 0)
%               and meet at the feed point inside the tube;
%     - MIDDLE: one horizontal support tube per loop (e.g. a 5/8" pipe,
%               params.support_d_mm) passes through the mast and holds
%               the helix arms open (holes at the support diameter);
%     - BOTTOM: the continuous bottom radial wire of each loop passes
%               straight through the mast (holes at the wire diameter).
%
%   The angles are computed from the same geometry as qfh_geometry.m:
%     theta(z) = z/H * turns * 2*pi + theta0
%   evaluated where each element crosses the mast wall (radius mast_d/2).
%   For the TOP holes two conventions exist (params.top_marks):
%     'cardinal' (default) - on the loop axis theta0, like the Coppens
%                template (easier to build; see README);
%     'exact'    - the exact wall-crossing azimuth of the slanted top
%                radial (feed end -> outer corner) of the simulated model.
%
%   Angle convention: degrees from the 0-deg seam line, increasing
%   counter-clockwise when seen from the TOP of the mast. Depths are to
%   HOLE CENTERS, measured from the antenna top plane (z = 0).
%
%   Fields per row (one row = one through-hole pair, or the two ends of
%   one support tube):
%     loop        - 'small' / 'large'
%     position    - 'top' / 'middle' / 'bottom'
%     depth_mm    - depth below the antenna top plane [mm]
%     angles_deg  - [a1 a2] wall-crossing azimuths (always 180 deg apart)
%     hole_d_mm   - hole diameter (wire or support tube)
%     arms        - {arm1 arm2} labels: A/B = small loop, C/D = large

rm = params.mast_d_mm / 2;
wd = params.wire_d_mm;
sd = params.support_d_mm;
f2 = params.feed_len_mm / 2;

if sd >= params.mast_d_mm
    error('qfh:template', ...
        'Support tube (%.1f mm) does not fit through the mast (%.1f mm).', ...
        sd, params.mast_d_mm);
end
if rm <= f2
    error('qfh:template', ...
        'Mast radius (%.1f mm) must be larger than the feed half-length (%.1f mm).', rm, f2);
end

names  = {'small', 'large'};
armlab = {{'A','B'}, {'C','D'}};

marks = struct('loop', {}, 'position', {}, 'depth_mm', {}, ...
                'angles_deg', {}, 'hole_d_mm', {}, 'arms', {});

for k = 1:2
    lp = design.loops(k);
    H = lp.H;  D = lp.D;  R = lp.R;  T = lp.turns;  th0 = lp.theta0;

    if rm >= D/2 - R
        error('qfh:template', ...
            'Mast radius (%.1f mm) reaches beyond the loop radials (%.1f mm).', rm, D/2 - R);
    end

    % --- TOP: hole azimuth, two conventions (params.top_marks) ---
    switch lower(params.top_marks)
        case 'cardinal'
            % Construction convention (same as the Coppens template): the
            % top holes sit on the loop's cardinal axis (theta0). The
            % simulated model actually has the top radials slanting toward
            % the offset feed point, but at the mast wall the difference
            % is only ~3 mm of arc and the wires get bent slightly toward
            % the feed during assembly anyway. See README.
            aTop = mod(th0 * 180/pi, 360);
        case 'exact'
            % Exact azimuth where the slanted radial of the simulated
            % model crosses the wall: the radial runs from the feed end P
            % (at +/-45 deg, radius f2) to the outer corner start Q (at
            % theta0, radius D/2-R); solve |P+t*d| = rm.
            if k == 1
                af = th0 + pi/4;   % loop 1 feed end (as in qfh_geometry)
            else
                af = th0 - pi/4;   % loop 2
            end
            P  = f2 * [cos(af), sin(af)];
            Q  = (D/2 - R) * [cos(th0), sin(th0)];
            d  = Q - P;
            qa = dot(d, d);
            qb = 2 * dot(P, d);
            qc = dot(P, P) - rm^2;
            t  = (-qb + sqrt(qb^2 - 4*qa*qc)) / (2*qa);   % crossing in [0,1]
            pw = P + t*d;
            aTop = mod(atan2(pw(2), pw(1)) * 180/pi, 360);
        otherwise
            error('qfh:params', 'top_marks must be ''cardinal'' or ''exact''');
    end

    % --- MIDDLE: helix azimuth at z = -H/2 (support tube direction) ---
    aMid = mod((-T*pi + th0) * 180/pi, 360);

    % --- BOTTOM: azimuth of the bottom radial at z = -H ---
    aBot = mod((-T*2*pi + th0) * 180/pi, 360);

    rows = { 'top',    0,   aTop, wd; ...
             'middle', H/2, aMid, sd; ...
             'bottom', H,   aBot, wd };

    for r = 1:3
        a1 = rows{r, 3};
        marks(end+1) = struct( ...                            %#ok<AGROW>
            'loop', names{k}, 'position', rows{r,1}, ...
            'depth_mm', rows{r,2}, ...
            'angles_deg', [a1, mod(a1 + 180, 360)], ...
            'hole_d_mm', rows{r,4}, 'arms', {armlab{k}});
    end
end

[~, idx] = sort([marks.depth_mm]);
marks = marks(idx);
end
