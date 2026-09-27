function geom = qfh_geometry(design, params)
%QFH_GEOMETRY Builds the 3D geometry of the QFH antenna (list of wires).
%
%   geom = QFH_GEOMETRY(design, params)
%
%   Faithful port of the make_helix() function from QFH2nec.c
%   (https://github.com/oceantrotter/QFH2nec). Each bifilar loop is
%   made of:
%     - 2 radial arms at the top (connected to the ends of the feed wire)
%     - the top 90-degree corners (arc of radius bend_r_mm, discretized)
%     - the helical section (the actual twist)
%     - the bottom corners + one continuous radial arm passing through
%       the center
%   plus the short feed wire in the center, at the top.
%
%   geom.wires    - struct array, one element per wire (GW card in NEC):
%                     .p1, .p2  - wire endpoints [mm]
%                     .r        - conductor radius [mm]
%                     .nseg     - number of NEC segments
%                     .group    - 1 = small loop, 2 = large loop, 3 = feed
%   geom.feed_idx - index of the feed wire (= NEC tag for the EX card)

wires = struct('p1', {}, 'p2', {}, 'r', {}, 'nseg', {}, 'group', {});

for k = 1:2
    wires = [wires, loop_wires(design.loops(k), params, k == 1, k)]; %#ok<AGROW>
end

% The feed wire: a short segment passing through the center, at the top.
% The 4 radial arms of both loops join at its endpoints, so a voltage
% source placed on it feeds both loops in parallel.
lp = design.loops(1);
f2 = params.feed_len_mm / 2;
pf = [f2*cos(lp.theta0 + pi/4), f2*sin(lp.theta0 + pi/4), lp.offset];
wires = addw(wires, pf, [-pf(1), -pf(2), lp.offset], lp.wire_r, 1, 3);

geom.wires    = wires;
geom.feed_idx = numel(wires);
end

% =========================================================================
function w = loop_wires(lp, params, feedhack, group)
% 1:1 port of make_helix() from QFH2nec.c (all values in mm).
H   = lp.H;   D   = lp.D;   R  = lp.R;
T   = lp.turns;             % the sign of T sets the winding sense
th0 = lp.theta0;
off = lp.offset;
wr  = lp.wire_r;
f2  = params.feed_len_mm / 2;
sc  = params.seg_corner;
sh  = params.seg_helix;

w = struct('p1', {}, 'p2', {}, 'r', {}, 'nseg', {}, 'group', {});

% --- top radial arms ---
% the inner end sits at +/-45 degrees from the loop, on the feed endpoints
if feedhack
    a = th0 + pi/4;    % loop 1
else
    a = th0 - pi/4;    % loop 2 (theta0 differs by 90 => same physical point)
end
x1 = f2*cos(a);  y1 = f2*sin(a);  z1 = 0;
x  = (D/2 - R)*cos(th0);  y = (D/2 - R)*sin(th0);  z = 0;
w = addw(w, [ x1,  y1, z1+off], [ x,  y, z+off], wr, params.seg_radial, group);
w = addw(w, [-x1, -y1, z1+off], [-x, -y, z+off], wr, params.seg_radial, group);

% --- top corners (quarter circle of radius R, twisted with the helix) ---
for i = 1:sc
    x1 = x;  y1 = y;  z1 = z;
    alpha = pi/2 * i/sc;
    z  = -R + R*cos(alpha);
    th = z/H * T * 2*pi + th0;
    r  = D/2 - R + R*sin(alpha);
    x  = r*cos(th);  y = r*sin(th);
    w = addw(w, [ x1,  y1, z1+off], [ x,  y, z+off], wr, 1, group);
    w = addw(w, [-x1, -y1, z1+off], [-x, -y, z+off], wr, 1, group);
end

% --- helical section (constant radius D/2) ---
r = D/2;
for i = 1:sh
    x1 = x;  y1 = y;  z1 = z;
    z  = -R - i/sh * (H - 2*R);
    th = z/H * T * 2*pi + th0;
    x  = r*cos(th);  y = r*sin(th);
    w = addw(w, [ x1,  y1, z1+off], [ x,  y, z+off], wr, 1, group);
    w = addw(w, [-x1, -y1, z1+off], [-x, -y, z+off], wr, 1, group);
end

% --- bottom corners ---
for i = 1:sc
    x1 = x;  y1 = y;  z1 = z;
    alpha = pi/2 * i/sc;
    z  = -H + R - R*sin(alpha);
    th = z/H * T * 2*pi + th0;
    r2 = D/2 - R + R*cos(alpha);
    x  = r2*cos(th);  y = r2*sin(th);
    w = addw(w, [ x1,  y1, z1+off], [ x,  y, z+off], wr, 1, group);
    w = addw(w, [-x1, -y1, z1+off], [-x, -y, z+off], wr, 1, group);
end

% --- bottom radial arm (continuous, passes through the antenna center) ---
w = addw(w, [x, y, z+off], [-x, -y, z+off], wr, 2*params.seg_radial - 1, group);
end

function w = addw(w, p1, p2, r, nseg, group)
e = struct('p1', p1, 'p2', p2, 'r', r, 'nseg', nseg, 'group', group);
if isempty(w)
    w = e;
else
    w(end+1) = e;
end
end
