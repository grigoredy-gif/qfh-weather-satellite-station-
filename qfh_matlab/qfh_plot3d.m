function fig = qfh_plot3d(geom, design, params, pngfile)
%QFH_PLOT3D 3D visualization of the QFH antenna in MATLAB.
%
%   fig = QFH_PLOT3D(geom, design, params)             - display only
%   fig = QFH_PLOT3D(geom, design, params, 'fig.png')  - also save a PNG

if nargin < 4, pngfile = ''; end

fig = figure('Name', 'QFH antenna - 3D', 'Color', 'w', 'Position', [80 60 760 860]);
hold on;

cols  = {[0.85 0.33 0.10], [0.00 0.45 0.74], [0 0 0]};  % small, large, feed
names = {design.loops(1).name, design.loops(2).name, 'feed (excitation)'};
h = gobjects(1, 3);

for i = 1:numel(geom.wires)
    w  = geom.wires(i);
    g  = w.group;
    lw = 1.8;
    if g == 3, lw = 3.5; end
    hp = plot3([w.p1(1) w.p2(1)], [w.p1(2) w.p2(2)], [w.p1(3) w.p2(3)], ...
               '-', 'Color', cols{g}, 'LineWidth', lw);
    if ~isgraphics(h(g)), h(g) = hp; end
end

% feed points (the endpoints of the feed wire)
fw = geom.wires(geom.feed_idx);
plot3([fw.p1(1) fw.p2(1)], [fw.p1(2) fw.p2(2)], [fw.p1(3) fw.p2(3)], ...
      'k.', 'MarkerSize', 18);
text(0, 0, 30, '  feed', 'FontWeight', 'bold');

% the mast (visual only - it does NOT appear in the .nec file)
if params.show_mast
    Hmax = design.loops(2).H;                 % the large loop is the tallest
    [cx, cy, cz] = cylinder(params.mast_d_mm/2, 24);
    cz = cz * (-(Hmax + 60)) + 30;            % from +30 at the top to below the loop
    surf(cx, cy, cz, 'FaceColor', [0.75 0.75 0.75], ...
         'FaceAlpha', 0.25, 'EdgeColor', 'none');
end

axis equal; grid on; box on;
xlabel('X [mm]'); ylabel('Y [mm]'); zlabel('Z [mm]');
title(sprintf('QFH %.1f MHz  |  %s  |  wire %.2f mm', ...
      params.freq_mhz, upper(params.polarity), params.wire_d_mm));
legend(h, names, 'Location', 'northeast');
view(-37.5, 14);

if ~isempty(pngfile)
    exportgraphics(fig, pngfile, 'Resolution', 150);
    fprintf('3D figure saved: %s\n', pngfile);
end
end
