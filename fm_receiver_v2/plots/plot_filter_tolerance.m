function plot_filter_tolerance(simdir, outfile)
% PLOT_FILTER_TOLERANCE  The three filter sections of receiver version 2: nominal parts and 300 tolerance runs.
%
% This plots simulation output (LTspice). It is not a measurement: nothing of version 2 is built yet.
%
% How the input is made:
%   1. Copy ../simulations to a scratch folder.
%   2. In the copy, add one line before ".end" of each of these six decks (the circuit and the analysis stay as they are):
%        rx2_a1_frontend_ac.cir, rx2_a2_frontend_tolerance.cir : .save V(m1in)
%        rx2_d1_if1_ac.cir,      rx2_d2_if1_tolerance.cir      : .save V(m2in)
%        rx2_f1_if2_ac.cir,      rx2_f3_if2_tolerance.cir      : .save V(t6)
%   3. Run each deck in LTspice (LTspice.exe -b <deck>.cir). This writes <deck>.raw next to it.
%   4. In MATLAB: plot_filter_tolerance('<scratch folder>', 'filter_tolerance.png')
%
% Every curve is shown relative to the nominal response at the signal frequency (0 dB there).
% The tolerance decks run 302 cases: 300 with random part values, then all parts at the bottom (301)
% and at the top (302) of their tolerance.

if nargin < 2, outfile = 'filter_tolerance.png'; end

P = struct( ...
  'title', {'Front end, 137.9 MHz', 'First IF, 12.9 MHz', 'Second IF, 1.418 MHz'}, ...
  'nom',   {'rx2_a1_frontend_ac', 'rx2_d1_if1_ac', 'rx2_f1_if2_ac'}, ...
  'tol',   {'rx2_a2_frontend_tolerance', 'rx2_d2_if1_tolerance', 'rx2_f3_if2_tolerance'}, ...
  'vec',   {'V(m1in)', 'V(m2in)', 'V(t6)'}, ...
  'fsig',  {137.9e6, 12.9e6, 1.41818e6}, ...
  'fimg',  {112.1e6, 15.736e6, NaN}, ...
  'xlim',  {[95 180], [9 17], [1.25 1.6]}, ...
  'note',  {'image 112.1 MHz', 'second image 15.736 MHz', ''});

fig = figure('Color', 'w', 'Units', 'inches', 'Position', [0.5 0.5 13 4.2], 'Visible', 'off');
tl = tiledlayout(fig, 1, 3, 'TileSpacing', 'compact', 'Padding', 'compact');
title(tl, 'Receiver version 2, LTspice simulation: filter response with nominal parts (black) and 300 runs with random part values (grey)', ...
  'FontSize', 11, 'FontWeight', 'normal');

for k = 1:3
  [fn, Mn] = read_ac_raw(fullfile(simdir, [P(k).nom '.raw']), P(k).vec);
  [ft, Mt] = read_ac_raw(fullfile(simdir, [P(k).tol '.raw']), P(k).vec);
  ref = interp1(fn, Mn, P(k).fsig);              % nominal response at the signal frequency
  ax = nexttile(tl); hold(ax, 'on'); grid(ax, 'on'); box(ax, 'on');
  if k == 3                                       % the band the FM signal occupies: +-21 kHz
    patch(ax, ([P(k).fsig-21e3 P(k).fsig+21e3 P(k).fsig+21e3 P(k).fsig-21e3])/1e6, [-60 -60 5 5], ...
      [0.85 0.92 1], 'EdgeColor', 'none');
  end
  plot(ax, ft/1e6, Mt(:, 1:300) - ref, 'Color', [0.72 0.72 0.72], 'LineWidth', 0.4);
  plot(ax, ft/1e6, Mt(:, 301:302) - ref, '--', 'Color', [0.35 0.35 0.35], 'LineWidth', 0.8);
  plot(ax, fn/1e6, Mn - ref, 'k', 'LineWidth', 1.6);
  xline(ax, P(k).fsig/1e6, ':', 'signal', 'Color', [0 0.35 0.8], 'LineWidth', 1.2, ...
    'LabelVerticalAlignment', 'bottom', 'FontSize', 9);
  if ~isnan(P(k).fimg)
    xline(ax, P(k).fimg/1e6, ':', P(k).note, 'Color', [0.8 0.1 0.1], 'LineWidth', 1.2, ...
      'LabelVerticalAlignment', 'bottom', 'FontSize', 9);
  end
  xlim(ax, P(k).xlim); ylim(ax, [-60 5]);
  xlabel(ax, 'frequency (MHz)');
  if k == 1, ylabel(ax, 'response re nominal at the signal (dB)'); end
  title(ax, P(k).title, 'FontWeight', 'normal');

  % Numbers to compare with DESIGN_LOG.md
  sig = interp1(ft, Mt, P(k).fsig) - ref;         % 1 x 302, dB at the signal
  fprintf('%s: nominal 0 dB at the signal; tolerance runs %.2f to %.2f dB (worst-case pair %.2f / %.2f)\n', ...
    P(k).title, min(sig(1:300)), max(sig(1:300)), sig(301), sig(302));
  if ~isnan(P(k).fimg)
    rn = interp1(fn, Mn, P(k).fsig) - interp1(fn, Mn, P(k).fimg);
    rt = interp1(ft, Mt, P(k).fsig) - interp1(ft, Mt, P(k).fimg);
    fprintf('   image rejection: nominal %.1f dB, 300 runs %.1f to %.1f dB\n', rn, min(rt(1:300)), max(rt(1:300)));
  end
  bw = minus3db(fn, Mn);
  fprintf('   nominal -3 dB width: %.1f kHz (%.4f to %.4f MHz)\n', (bw(2)-bw(1))/1e3, bw(1)/1e6, bw(2)/1e6);
end

exportgraphics(fig, outfile, 'Resolution', 140);
fprintf('wrote %s\n', outfile);
end

function bw = minus3db(f, m)
[pk, i] = max(m);
lo = find(m(1:i) < pk - 3, 1, 'last');
hi = i - 1 + find(m(i:end) < pk - 3, 1, 'first');
bw = [interp1(m(lo:lo+1), f(lo:lo+1), pk - 3), interp1(m(hi-1:hi), f(hi-1:hi), pk - 3)];
end

function [f, M] = read_ac_raw(file, vec)
% Reads an LTspice binary AC .raw file (one run or stepped runs); returns f (Hz) and |vec| in dB, one column per run.
fid = fopen(file, 'r'); assert(fid > 0, 'cannot open %s', file);
b = fread(fid, Inf, 'uint8=>uint8')'; fclose(fid);
utf16 = b(2) == 0;
if utf16, enc = 'UTF-16LE'; else, enc = 'US-ASCII'; end
marker = unicode2native(sprintf('Binary:\n'), enc);
pos = strfind(char(b), char(marker)); assert(~isempty(pos), 'no binary section in %s', file);
hdr = splitlines(string(native2unicode(b(1:pos(1)-1), enc)));
nvar = str2double(extractAfter(hdr(startsWith(hdr, 'No. Variables:')), ':'));
npts = str2double(extractAfter(hdr(startsWith(hdr, 'No. Points:')), ':'));
iv = find(startsWith(hdr, 'Variables:'));
names = strings(nvar, 1);
for k = 1:nvar
  parts = split(strtrim(hdr(iv + k)), char(9));
  names(k) = parts(2);
end
j = find(strcmpi(names, vec)); assert(~isempty(j), '%s not in %s', vec, file);
first = pos(1) + numel(marker);
d = typecast(b(first : first + 16*nvar*npts - 1), 'double');
d = reshape(d, 2*nvar, npts).';
fr = d(:, 1);
v = complex(d(:, 2*j - 1), d(:, 2*j));
starts = [1; find(diff(fr) < 0) + 1];
n = numel(fr) / numel(starts); assert(n == round(n), 'runs of unequal length in %s', file);
f = fr(1:n);
M = reshape(20*log10(abs(v)), n, numel(starts));
end
