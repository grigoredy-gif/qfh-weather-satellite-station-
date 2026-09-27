function out = lrpt_sync(fname, tSeg)
%LRPT_SYNC  Stage 1 of the home-built LRPT decoder: baseband -> symbols.
%
%   Takes a cs16 baseband recording of a Meteor-M LRPT pass (72 kSym/s
%   OQPSK) and produces a synchronized QPSK symbol stream, using no
%   toolboxes and no decoder software:
%
%     1. Coarse + time-varying carrier correction (PSD template fit,
%        tracks Doppler chunk by chunk)
%     2. Root-raised-cosine matched filter (alpha = 0.6)
%     3. OPEN-LOOP symbol timing from the 72 kHz cyclostationary clock
%        line - the same line signal_id.m measured to 0.007 %. Its phase,
%        tracked over time, IS the symbol clock. No feedback loop needed.
%     4. OQPSK phase recovery: on half-symbol samples z, the sequence
%        z.^2 .* (-1).^m has phase 2*theta regardless of the I/Q stagger -
%        a vectorized, stagger-proof phase estimator.
%     5. Rail alignment: both hypotheses (which half-symbol lane is I)
%        are kept; stage 2 tries both.
%
%   OUTPUT: <recording>_sym.mat next to the recording, containing the two
%   candidate symbol streams + metadata, and four diagnostic figures.
%   THE FIGURE THAT MATTERS: the constellations. Four distinct clouds =
%   the demodulation works and stage 2's verdict can be trusted.
%
%   USAGE
%     lrpt_sync                    % file picker, auto-picks best 45 s
%     lrpt_sync(fname, [235 320])  % explicit segment [s]
%
%   Base MATLAB only.

% ------------------------------------------------------------------ input
if nargin < 1 || isempty(fname)
    startDir = 'C:\SDR';
    if ~isfolder(startDir), startDir = pwd; end
    [f, p] = uigetfile({'*.cs16', 'SatDump cs16 baseband'}, ...
                       'Pick the recording', startDir);
    if isequal(f, 0), fprintf('Cancelled.\n'); return; end
    fname = fullfile(p, f);
end
[~, nm0, ex0] = fileparts(fname);                 % filename ONLY - a digits+SPS
tok = regexpi([nm0 ex0], '(\d+)SPS', 'tokens', 'once');   % folder name must not win
if isempty(tok), error('Sample rate not found in filename.'); end
fs  = str2double(tok{1});

Rs    = 72000;          % symbol rate (measured on this very signal)
alpha = 0.6;            % LRPT RRC roll-off
D     = 4;              % decimation after matched filter
fsd   = fs / D;         % internal rate (250 kHz at 1 Msps)
SEGD  = 45;             % seconds to process when auto-picking

info = dir(fname);
if isempty(info), error('File not found.'); end
bytesPerSample = 4;                       % cs16
nTotal   = floor(info.bytes / bytesPerSample);
duration = nTotal / fs;

fprintf('\n=== lrpt_sync ===\nFile: %s  (%.1f s)\n', info.name, duration);

% ------------------------------------------- pass 0: find the best window
% Light SNR scan (1 row/s), same idea as baseband_check, to auto-pick the
% strongest contiguous SEGD seconds unless the caller chose a segment.
if nargin < 2 || isempty(tSeg)
    fprintf('Scanning for the strongest %d s window', SEGD);
    NF = 4096; NA = 8;
    fid = fopen(fname, 'r');
    nRows = floor(duration);
    snr = -inf(nRows, 1);
    fscan = (-NF/2:NF/2-1)' * (fs/NF);
    sigIdx   = abs(fscan) <= 60e3 & abs(fscan) >= 3e3;
    noiseIdx = abs(fscan) >= 200e3 & abs(fscan) <= 450e3;
    for r = 1:nRows
        raw = fread(fid, 2*NF*NA, 'int16=>double');
        if numel(raw) < 2*NF*NA, break; end
        x = complex(raw(1:2:end), raw(2:2:end));
        P = mean(abs(fft(reshape(x, NF, NA))).^2, 2);
        P = fftshift(P);
        ps = mean(P(sigIdx)); pn = mean(P(noiseIdx));
        snr(r) = 10*log10(max(ps - pn, eps) / pn);
        fseek(fid, (fs - NF*NA)*bytesPerSample, 'cof');
        if mod(r, 60) == 0, fprintf('.'); end
    end
    fclose(fid);
    win = min(SEGD, nRows);
    score = movmean(snr, win, 'Endpoints', 'discard');
    [bestSnr, i0] = max(score);
    tSeg = [i0-1, i0-1+win];
    fprintf(' -> t = %d..%d s (mean SNR %.1f dB)\n', tSeg, bestSnr);
end
tSeg(1) = max(0, tSeg(1)); tSeg(2) = min(duration, tSeg(2));
if diff(tSeg) < 5
    error('Segment too short (%.1f s after clamping to the file) - need >= 5 s.', diff(tSeg));
end

% ------------------------- pass 1: mix + matched filter + decimate stream
% Coarse frequency first, from an averaged PSD of the segment start.
fid = fopen(fname, 'r');
cleanup = onCleanup(@() fclose(fid));
fseek(fid, round(tSeg(1)*fs)*bytesPerSample, 'bof');
raw = fread(fid, 2*fs*2, 'int16=>double');          % 2 s for the coarse PSD
x0  = complex(raw(1:2:end), raw(2:2:end));
NF  = 8192;
P0  = fftshift(mean(abs(fft(reshape(x0(1:NF*floor(numel(x0)/NF)), NF, []))).^2, 2));
f0ax = (-NF/2:NF/2-1)' * (fs/NF);
mask = abs(f0ax) <= (1+alpha)*Rs/2;               % only the signal's occupancy
Pex  = max(P0 - median(P0), 0) .* mask;
fCoarse = sum(f0ax .* Pex) / max(sum(Pex), eps);
fprintf('Coarse carrier offset: %+.0f Hz\n', fCoarse);

% RRC taps at the input rate (fractional samples/symbol is fine for a FIR)
sps  = fs / Rs;
span = 6;
n    = (-ceil(span*sps) : ceil(span*sps))';
t_n  = n / sps;
h    = zeros(size(t_n));
for i = 1:numel(t_n)
    ti = t_n(i);
    if abs(ti) < 1e-9
        h(i) = 1 - alpha + 4*alpha/pi;
    elseif abs(abs(4*alpha*ti) - 1) < 1e-9
        h(i) = alpha/sqrt(2) * ((1+2/pi)*sin(pi/(4*alpha)) + (1-2/pi)*cos(pi/(4*alpha)));
    else
        h(i) = (sin(pi*ti*(1-alpha)) + 4*alpha*ti.*cos(pi*ti*(1+alpha))) ...
               ./ (pi*ti .* (1 - (4*alpha*ti).^2));
    end
end
h = h / sqrt(sum(h.^2));

fseek(fid, round(tSeg(1)*fs)*bytesPerSample, 'bof');
nSec  = floor(diff(tSeg));
y     = zeros(ceil(nSec*fs/D) + 8, 1);              % decimated output
ny    = 0;
zi    = zeros(numel(h)-1, 1);
phAcc = 0;                                          % mixer phase carry
dOff  = 0;                                          % decimator phase carry
fprintf('Filtering');
for b = 1:nSec
    raw = fread(fid, 2*fs, 'int16=>double');
    if numel(raw) < 2*fs, break; end
    x = complex(raw(1:2:end), raw(2:2:end));
    mixer = exp(-1j*(phAcc + 2*pi*fCoarse*(0:numel(x)-1)'/fs));
    phAcc = mod(phAcc + 2*pi*fCoarse*numel(x)/fs, 2*pi);
    [xf, zi] = filter(h, 1, x .* mixer, zi);
    idx = (1+dOff) : D : numel(xf);
    y(ny+1 : ny+numel(idx)) = xf(idx);
    ny   = ny + numel(idx);
    dOff = idx(end) + D - numel(xf) - 1;
    if mod(b, 10) == 0, fprintf('.'); end
end
y  = y(1:ny);
ty = (0:ny-1)' / fsd;
fprintf(' done (%.1f s at %.0f kHz)\n', ny/fsd, fsd/1e3);

% ------------------------------- Doppler track: PSD template fit per chunk
chunk = round(2*fsd);                                % 2 s chunks
nCh   = floor(ny/chunk);
NF2   = 8192;
fax   = (-NF2/2:NF2/2-1)' * (fsd/NF2);
% ideal RRC power template on this axis
T = zeros(size(fax));
T(abs(fax) <= (1-alpha)*Rs/2) = 1;
tr = abs(fax) > (1-alpha)*Rs/2 & abs(fax) < (1+alpha)*Rs/2;
T(tr) = cos(pi/(2*alpha*Rs) * (abs(fax(tr)) - (1-alpha)*Rs/2)).^2;
dfGrid = -3000:50:3000;
[dfCh, tCh, edged] = chunkDoppler(y, chunk, nCh, NF2, fax, T, dfGrid, fsd);
if edged
    warning('Doppler search pinned at +/-3 kHz - retrying with a +/-8 kHz grid.');
    [dfCh, tCh, edged] = chunkDoppler(y, chunk, nCh, NF2, fax, T, -8000:50:8000, fsd);
    if edged
        warning('Still pinned: the coarse frequency estimate is suspect (interference?).');
    end
end
pOrd = max(0, min(3, nCh-1));
pc   = polyfit(tCh, dfCh, pOrd);
dfT  = polyval(pc, ty);
y    = y .* exp(-1j*2*pi*cumsum(dfT)/fsd);
fprintf('Doppler track: %+.0f -> %+.0f Hz across the segment\n', ...
        polyval(pc, ty(1)), polyval(pc, ty(end)));

% ---------------------------------------- symbol clock from the 72k line
e  = abs(y).^2;  e = e - mean(e);
Ew = fft(e .* (0.5 - 0.5*cos(2*pi*(0:ny-1)'/ny)));
fE = (0:ny-1)' * (fsd/ny);
w  = find(abs(fE - Rs) <= 100);
[~, iw] = max(abs(Ew(w)));  ip = w(iw);
% parabolic sub-bin refinement
a1 = abs(Ew(ip-1)); a2 = abs(Ew(ip)); a3 = abs(Ew(ip+1));
d  = 0.5*(a1 - a3)/(a1 - 2*a2 + a3 + eps);
fclk = fE(ip) + d*(fsd/ny);
lineDb = 20*log10(a2 / median(abs(Ew(w))));
fprintf('Clock line: %.2f Hz (%.1f dB) - timing comes from HERE\n', fclk, lineDb);

% clock phase vs time (this is the timing information)
m  = e .* exp(-1j*2*pi*fclk*ty);
ms = movmean(m, round(0.05*fsd));                    % 50 ms smoothing
step  = round(0.001*fsd);                            % 1 ms grid
tgrid = ty(1:step:end);
phgrid = unwrap(angle(ms(1:step:end)));

% ------------------------- half-symbol sampling, 4 clock-phase hypotheses
% Each psi0 hypothesis is scored by the strength of a SPECTRAL LINE, not a
% block average (review finding: block averages collapse when a residual
% carrier offset is present; a line's strength does not, and its frequency
% measures that residual exactly, wrap-free):
%   OQPSK: v = z.^2 .* (-1).^m  -> line at 2*df_res, phase 2*theta
%   QPSK : w = z_sym.^4         -> line at 4*df_res
% BOTH branches are kept (review finding: for ideal OQPSK the z.^2 line is
% the right tool but for plain QPSK it is identically zero, and vice versa -
% betting on one modulation risks a silent false 'no frames' downstream).
M    = floor((ty(end) - 0.1) * 2 * fclk);
mIdx = (0:M-1)';
sgn  = 1 - 2*mod(mIdx, 2);
bestO = struct('metric',0,'psi0',NaN,'z',[],'fres',0);
bestQ = struct('metric',0,'psi0',NaN,'ze',[],'fres',0);
for psi0 = [0 pi/4 pi/2 3*pi/4]
    t0 = (pi*mIdx + psi0) / (2*pi*fclk);
    t1 = (pi*mIdx + psi0 - interp1(tgrid, phgrid, t0, 'linear', 'extrap')) ...
         / (2*pi*fclk);
    z  = interp1(ty, y, t1, 'linear', 0);
    z  = z / sqrt(mean(abs(z).^2));
    [mgO, frO] = phaseLine(z.^2 .* sgn, 2*fclk, 2000);
    ze = z(1:2:end);
    [mgQ, frQ] = phaseLine(ze.^4, fclk, 4000);
    fprintf('  psi0 = %4.2f -> OQPSK line %6.1fx | QPSK line %6.1fx\n', psi0, mgO, mgQ);
    if mgO > bestO.metric, bestO = struct('metric',mgO,'psi0',psi0,'z',z,'fres',frO/2); end
    if mgQ > bestQ.metric, bestQ = struct('metric',mgQ,'psi0',psi0,'ze',ze,'fres',frQ/4); end
end
fprintf('OQPSK branch: psi0 %.2f, line %.1fx floor, residual df %+.1f Hz\n', ...
        bestO.psi0, bestO.metric, bestO.fres);
fprintf('QPSK  branch: psi0 %.2f, line %.1fx floor, residual df %+.1f Hz\n', ...
        bestQ.psi0, bestQ.metric, bestQ.fres);
if max(bestO.metric, bestQ.metric) < 8
    fprintf(['note: phase lines are weak - a drifting Doppler residual smears them.\n' ...
             'The constellation quality q printed below is the decisive indicator.\n']);
end

% ------------------- OQPSK branch: kill residual df, track phase, rails
z   = bestO.z .* exp(-1j*2*pi*bestO.fres*(mIdx/(2*fclk)));
v   = z.^2 .* sgn;
B   = 2048;  nB = max(1, floor(M/B));
mu  = mean(reshape(v(1:nB*B), B, nB), 1).';
thB = 0.5 * unwrap(angle(mu));
tB  = ((0:nB-1)' + 0.5) * B / (2*fclk);
thS = interp1(tB, thB, mIdx/(2*fclk), 'linear', 'extrap');
z   = z .* exp(-1j*thS);

zI0 = real(z(1:2:end));  zQ0 = imag(z(2:2:end));
K0  = min(numel(zI0), numel(zQ0));
c0  = complex(zI0(1:K0), zQ0(1:K0));
zI1 = real(z(2:2:end));  zQ1 = imag(z(3:2:end));
K1  = min(numel(zI1), numel(zQ1));
c1  = complex(zI1(1:K1), zQ1(1:K1));
c0  = c0 / sqrt(mean(abs(c0).^2));
c1  = c1 / sqrt(mean(abs(c1).^2));
q0  = abs(mean(c0.^4));  q1 = abs(mean(c1.^4));

% ---------------- QPSK fallback branch: same treatment on symbol centres
ze  = bestQ.ze;
Mq  = numel(ze);
ze  = ze .* exp(-1j*2*pi*bestQ.fres*((0:Mq-1)'/fclk));
w4  = ze.^4;
Bq  = 1024;  nBq = max(1, floor(Mq/Bq));
muq = mean(reshape(w4(1:nBq*Bq), Bq, nBq), 1).';
thBq = 0.25 * unwrap(angle(muq));
thSq = interp1(((0:nBq-1)'+0.5)*Bq/fclk, thBq, (0:Mq-1)'/fclk, 'linear', 'extrap');
cq  = ze .* exp(-1j*thSq);
cq  = cq / sqrt(mean(abs(cq).^2));
qq  = abs(mean(cq.^4));

fprintf('Constellation quality |mean c^4|: rails d0 %.3f, d1 %.3f, qpsk %.3f\n', q0, q1, qq);
fprintf('(noise gives ~0.001 here; >= 0.1 = locked, even if the clouds overlap visually)\n');
if max([q0 q1 qq]) < 0.1
    warning('Demod did NOT lock (all q < 0.1) - stage 2 will refuse a NO FRAMES verdict.');
end

% ------------------------------------------------------------------ output
[fp, base] = fileparts(fname);
outFile = fullfile(fp, [base '_sym.mat']);
meta = struct('fname',info.name,'tSeg',tSeg,'fclk',fclk,'lineDb',lineDb, ...
              'q0',q0,'q1',q1,'qq',qq, ...
              'oMetric',bestO.metric,'qMetric',bestQ.metric, ...
              'psi0O',bestO.psi0,'psi0Q',bestQ.psi0, ...
              'fresO',bestO.fres,'fresQ',bestQ.fres, ...
              'Rs',Rs,'fCoarse',fCoarse,'dopplerPoly',pc);
save(outFile, 'c0', 'c1', 'cq', 'meta');
fprintf('Symbols saved: %s\n', outFile);

% --------------------------------------------------------------- figures
figure('Name','lrpt_sync - carrier','Color','w');
subplot(2,1,1);
plot(tCh, dfCh, 'o'); hold on; plot(ty(1:1000:end), dfT(1:1000:end), 'LineWidth',1.2);
grid on; xlabel('t [s]'); ylabel('\Deltaf [Hz]');
title('Doppler track (dots = measured per chunk, line = fit)');
subplot(2,1,2);
plot(tB, thB, 'LineWidth', 1.0); grid on;
xlabel('t [s]'); ylabel('\theta [rad]');
title('Recovered carrier phase, OQPSK branch (should be smooth)');

figure('Name','lrpt_sync - constellations','Color','w');
sets = {c0, c1, cq};  ttl = {'rails d0','rails d1','plain QPSK'};
qv = [q0 q1 qq];
for k = 1:3
    subplot(1,3,k);
    ns = min(20000, numel(sets{k}));
    plot(real(sets{k}(1:ns)), imag(sets{k}(1:ns)), '.', 'MarkerSize', 2);
    axis equal; axis([-2 2 -2 2]); grid on;
    title(sprintf('%s  (q = %.3f)', ttl{k}, qv(k)));
end

if nargout, out = meta; end
end

% -------------------------------------------------------------------------
function [mg, fpk] = phaseLine(v, fsv, fmax)
% Strength (x over the in-window median) and frequency of the strongest
% spectral line of v within +/-fmax Hz of DC. One shot gives a wrap-free
% residual-frequency estimate AND a lock metric: pure noise tops out around
% 4-6x the median, a locked line sits far above.
N = numel(v);
V = abs(fft((v - mean(v)) .* (0.5 - 0.5*cos(2*pi*(0:N-1)'/N))));
f = (0:N-1)' * (fsv/N);
f(f > fsv/2) = f(f > fsv/2) - fsv;
in = abs(f) <= fmax;
[pk, ii] = max(V .* in);
mg  = pk / max(median(V(in)), eps);
fpk = f(ii);
end

function [dfCh, tCh, edged] = chunkDoppler(y, chunk, nCh, NF2, fax, T, dfGrid, fsd)
% Per-chunk carrier offset by sliding the ideal RRC power template over the
% measured PSD, with parabolic sub-grid refinement (review finding: the raw
% 50 Hz grid quantization alone could push the downstream phase tracker past
% its ~17 Hz pull-in range).
dfCh = zeros(nCh,1); tCh = zeros(nCh,1); edged = false;
for cix = 1:nCh
    seg = y((cix-1)*chunk + (1:chunk));
    Pc  = fftshift(mean(abs(fft(reshape(seg(1:NF2*floor(chunk/NF2)), NF2, []))).^2, 2));
    Pc  = max(Pc - median(Pc), 0);
    sc  = zeros(numel(dfGrid), 1);
    for g = 1:numel(dfGrid)
        sc(g) = sum(Pc .* interp1(fax + dfGrid(g), T, fax, 'linear', 0));
    end
    [~, gi] = max(sc);
    if gi == 1 || gi == numel(dfGrid)
        edged = true;
        dfCh(cix) = dfGrid(gi);
    else
        st = dfGrid(2) - dfGrid(1);
        d  = 0.5*(sc(gi-1) - sc(gi+1)) / (sc(gi-1) - 2*sc(gi) + sc(gi+1) + eps);
        dfCh(cix) = dfGrid(gi) + max(-1, min(1, d))*st;
    end
    tCh(cix) = ((cix-0.5)*chunk)/fsd;
end
end
