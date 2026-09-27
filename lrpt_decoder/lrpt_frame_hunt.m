function out = lrpt_frame_hunt(symFile)
%LRPT_FRAME_HUNT  Stage 2: do CCSDS frames exist in the symbol stream?
%
%   The decisive question of this whole investigation. Instead of decoding
%   everything, it hunts for the FINGERPRINT of the frame sync marker in
%   the still-encoded chip stream:
%
%     - every CADU starts with the 32-bit ASM 0x1ACFFC1D
%     - the transmitter convolutionally encodes the whole stream (CCSDS
%       K=7, r=1/2, G1=171o, G2=133o), so the ASM becomes a fixed pattern
%       of chips. The first 12 encoded chips depend on the unknown encoder
%       state (6 memory bits); the remaining 52 chips are DETERMINISTIC.
%     - if frames exist, that 52-chip template appears every 16384 chips
%       (CADU = 1024 bytes = 8192 bits = 16384 chips). Periodicity at
%       exactly 16384 cannot be faked by noise or by interference.
%
%   All demod ambiguities are searched: 2 rail pairings (from lrpt_sync)
%   x 2 rotations x conjugation x NRZ-M differential x G2 inversion x
%   chip order = 64 variants. Verdict: FRAMES EXIST (+ the exact variant,
%   which tells us what the decoder software should have used) or NO
%   FRAMES in any variant (the satellite is not sending CADUs).
%
%   USAGE
%     lrpt_frame_hunt              % picker for the *_sym.mat from stage 1
%     lrpt_frame_hunt(symFile)
%
%   Base MATLAB only.

% ------------------------------------------------------------------ input
if nargin < 1 || isempty(symFile)
    startDir = 'C:\SDR';
    if ~isfolder(startDir), startDir = pwd; end
    [f, p] = uigetfile({'*_sym.mat', 'lrpt_sync output'}, ...
                       'Pick the symbol file', startDir);
    if isequal(f, 0), fprintf('Cancelled.\n'); return; end
    symFile = fullfile(p, f);
end
S = load(symFile);
fprintf('\n=== lrpt_frame_hunt ===\nSymbols: %s (%.0fk + %.0fk)\n', ...
        S.meta.fname, numel(S.c0)/1e3, numel(S.c1)/1e3);

FRAME = 16384;               % chips per CADU (1024 bytes * 8 * 2)
THR   = 40;                  % |correlation| threshold out of 52
TOL   = 2;                   % chips of tolerance on the frame period

% ------------------------------------------------- encoded ASM templates
% CCSDS K=7 r=1/2 encoder, shift register [b_k b_{k-1} ... b_{k-6}]:
G1 = [1 1 1 1 0 0 1];        % 171 octal
G2 = [1 0 1 1 0 1 1];        % 133 octal
asm = '1ACFFC1D';
bits = zeros(32,1);
for i = 1:8
    nib = hex2dec(asm(i));
    bits(4*i-3:4*i) = bitget(nib, 4:-1:1)';
end
reg = zeros(6,1);                                 % state irrelevant: we cut it
chips = zeros(64,1);
for k = 1:32
    r7 = [bits(k); reg];
    chips(2*k-1) = mod(sum(r7 .* G1'), 2);
    chips(2*k)   = mod(sum(r7 .* G2'), 2);
    reg = r7(1:6);
end
tplBase = 1 - 2*chips(13:64);                     % 52 chips, state-independent

% Self-test against SatDump's ground-truth correlator constant: the
% bit-inverted 64-chip encoding of the ASM must equal 0xFCA2B63DB00D9794
% (verified independently during review). Catches any silent edit of the
% encoder loop, polynomials or ASM bit order before a verdict is trusted.
chk = 1 - chips;
hx  = '';
for i = 1:16
    hx = [hx dec2hex(chk(4*i-3)*8 + chk(4*i-2)*4 + chk(4*i-1)*2 + chk(4*i))]; %#ok<AGROW>
end
assert(strcmpi(hx, 'FCA2B63DB00D9794'), ...
       'Encoder self-test FAILED - the template is broken, no verdict is trustworthy.');
fprintf('Encoder self-test vs SatDump constant: OK\n');

% ------------------------------------------------------- the variant hunt
% noise-floor calibration: P(|corr| >= THR) for a random +/-1 stream
aMin = ceil((THR + 52)/2);
pFalse = 0;
for a = aMin:52, pFalse = pFalse + nchoosek(52, a); end
pFalse = 2 * pFalse / 2^52;

streams = {S.c0, S.c1};
snames  = {'d0','d1'};
if isfield(S, 'cq'), streams{end+1} = S.cq; snames{end+1} = 'qpsk'; end
res = [];
fprintf('Hunting (%d variants)', numel(streams)*32);
for st = 1:numel(streams)
    c = streams{st};
    for rot = 0:1
        cr = c * exp(1j*pi/2*rot);
        for cj = 0:1
            if cj, cc = conj(cr); else, cc = cr; end
            bI = real(cc) < 0;   bQ = imag(cc) < 0;
            for df = 0:1
                if df                              % NRZ-M per rail
                    bi = xor(bI(2:end), bI(1:end-1));
                    bq = xor(bQ(2:end), bQ(1:end-1));
                else
                    bi = bI; bq = bQ;
                end
                u = zeros(2*numel(bi), 1);
                u(1:2:end) = 1 - 2*bi;
                u(2:2:end) = 1 - 2*bq;
                for g2i = 0:1
                    for ord = 0:1
                        tpl = tplBase;
                        if g2i, tpl(2:2:end) = -tpl(2:2:end); end
                        if ord
                            tpl = reshape(flipud(reshape(tpl, 2, [])), [], 1);
                        end
                        xc = filter(flipud(tpl), 1, u);
                        pk = findPeaks(abs(xc), THR);
                        sc = periodScore(pk, FRAME, TOL);
                        res = [res; struct('st',st,'rot',rot,'cj',cj, ...
                              'df',df,'g2i',g2i,'ord',ord,'nPk',numel(pk), ...
                              'nPer',sc.nPer,'bestRun',sc.bestRun, ...
                              'maxC',max(abs(xc)),'pk',{pk})]; %#ok<AGROW>
                    end
                end
            end
        end
    end
    fprintf('.');
end
fprintf(' done\n');
expFalse = pFalse * 2 * max(cellfun(@numel, streams));
famExp   = expFalse * numel(res);
fprintf('Noise calibration: ~%.2f false peaks per variant, ~%.1f across all %d variants (thr %d/52)\n\n', ...
        expFalse, famExp, numel(res), THR);

% ------------------------------------------------------------ the verdict
[~, order] = sort([res.nPer] + [res.nPk]/1e6, 'descend');
res = res(order);
fprintf('%-4s %-4s %-4s %-4s %-4s %-4s | %6s %8s %8s %6s\n', ...
        'str','rot','conj','diff','g2i','ord','peaks','periodic','bestRun','maxC');
for i = 1:min(10, numel(res))
    r = res(i);
    fprintf('%-4d %-4d %-4d %-4d %-4d %-4d | %6d %8d %8d %6.0f\n', ...
            r.st, r.rot, r.cj, r.df, r.g2i, r.ord, r.nPk, r.nPer, r.bestRun, r.maxC);
end

best = res(1);
mxPk = max([res.nPk]);

% Demod-health gate (review finding: NEVER claim 'no frames' from a demod
% that never locked - that converts 'my sync failed' into the false claim
% 'the satellite sends nothing', the worst possible outcome of this tool).
hOK = false; hWhy = 'no health metadata (old _sym.mat - rerun lrpt_sync)';
if isfield(S.meta, 'oMetric')
    % The decisive lock indicator is the constellation coherence q = |mean c^4|
    % (noise gives ~1/sqrt(N) ~ 0.001 over millions of symbols; an unlocked
    % rotating constellation averages to zero). The pre-tracking phase-line
    % strength underestimates lock when the Doppler residual drifts, so it is
    % reported but NOT gated on.
    railQ = max(S.meta.q0, S.meta.q1);
    hOK = S.meta.lineDb >= 10 && max(railQ, S.meta.qq) >= 0.1;
    hWhy = sprintf(['OQPSK line %.1fx / rail q %.2f; QPSK line %.1fx / q %.2f; ' ...
                    'clock line %.1f dB'], S.meta.oMetric, railQ, ...
                    S.meta.qMetric, S.meta.qq, S.meta.lineDb);
end

fprintf('\n--- VERDICT ---\n');
if best.nPer >= 5
    fprintf('FRAMES EXIST. %d frame-periodic sync markers found (longest run %d\n', ...
            best.nPer, best.bestRun);
    fprintf('consecutive frames), variant: stream %s, rot %d, conj %d, diff %d,\n', ...
            snames{best.st}, best.rot, best.cj, best.df);
    fprintf('G2 inverted %d, chip order %d.\n', best.g2i, best.ord);
    fprintf('=> The satellite IS sending CADUs and the failure is in the\n');
    fprintf('   decoding software/settings. Next step: full Viterbi + deframe.\n');
elseif ~hOK
    fprintf('NO VERDICT - stage-1 demodulation never locked (%s).\n', hWhy);
    fprintf('A no-frames claim would be meaningless on unlocked symbols.\n');
    fprintf('Inspect the lrpt_sync constellations (need 4 clouds) and rerun.\n');
elseif best.nPer >= 1 || mxPk > 3*famExp
    fprintf('AMBIGUOUS: best variant has %d peaks, %d of them frame-periodic;\n', ...
            best.nPk, best.nPer);
    fprintf('family-wide noise expectation is %.1f peaks (max seen %d).\n', famExp, mxPk);
    fprintf('Look at the plots before concluding anything.\n');
else
    fprintf('NO FRAMES. The demodulation is HEALTHY (%s),\n', hWhy);
    fprintf('yet every variant sits at the noise floor: max %d peaks anywhere\n', mxPk);
    fprintf('vs ~%.1f expected across the whole family by chance alone, and\n', famExp);
    fprintf('none frame-periodic. The stream carries no CCSDS sync markers -\n');
    fprintf('a valid convolutional stream with no CADU structure (test/idle\n');
    fprintf('transmission). Your station and SatDump are both innocent.\n');
end

% ---------------- gap forensics on the best variant: what IS the period?
% (added after the first real run found perfect 52/52 ASM hits at spacings
% that are NOT multiples of 16384 - so the transmitter frames its stream
% with some other period, and that number is the whole mystery)
pk = best.pk;
if numel(pk) >= 3
    d = diff(pk);
    [ud, ~, ic] = unique(d);
    cnt = accumarray(ic, 1);
    [cnt, si] = sort(cnt, 'descend');  ud = ud(si);
    fprintf('\n--- gap forensics (best variant) ---\n');
    fprintf('Most common exact gaps:\n');
    for i = 1:min(8, numel(ud))
        fprintf('  %7d chips = %7.1f bytes  x%d\n', ud(i), ud(i)/16, cnt(i));
    end
    Ps = 4000:40000;  scP = zeros(size(Ps));
    for ip = 1:numel(Ps)
        P = Ps(ip);
        m = mod(d + 3, P);
        scP(ip) = sum(m <= 6 & d >= P - 3);
    end
    [~, ord2] = sort(scP, 'descend');
    fprintf('Best-fitting frame periods (gaps explained as exact multiples):\n');
    for i = 1:3
        P = Ps(ord2(i));
        fprintf('  P = %6d chips = %6.1f bytes = %5.1f ms  ->  %d/%d gaps\n', ...
                P, P/16, P/144, scP(ord2(i)), numel(d));
    end
    fprintf('  (the standard 16384-chip CADU explains %d/%d)\n', ...
            sum(mod(d+3,16384) <= 6 & d >= 16381), numel(d));
end

% --------------------------------------------------------------- figures
figure('Name','lrpt_frame_hunt','Color','w');
subplot(2,1,1);
if ~isempty(best.pk)
    d = diff(best.pk);
    histogram(mod(d + FRAME/2, FRAME) - FRAME/2, 101);
    xlabel(sprintf('peak spacing modulo %d chips', FRAME));
    title('Frame periodicity (a sharp spike at 0 = real frames)');
else
    title('No peaks above threshold in the best variant');
end
grid on;
subplot(2,1,2);
plot([res.nPer], 'o-'); grid on;
xlabel('variant rank'); ylabel('frame-periodic peaks');
title('Periodic-peak count across all 64 variants');

if nargout, out = res; end
end

% -------------------------------------------------------------------------
function pk = findPeaks(a, thr)
% indices of local maxima above thr, clustered (gap <= 8 keeps the max)
idx = find(a >= thr);
pk = [];
while ~isempty(idx)
    grp = idx(idx <= idx(1) + 8);
    [~, gi] = max(a(grp));
    pk(end+1,1) = grp(gi); %#ok<AGROW>
    idx(idx <= grp(end) + 8) = [];
end
end

function sc = periodScore(pk, FRAME, TOL)
% how many peak gaps are a multiple of the frame period, and the longest
% run of CONSECUTIVE frames (gap == exactly one frame)
sc.nPer = 0; sc.bestRun = 0;
if numel(pk) < 2, return; end
d   = diff(pk);
mod_ = mod(d + TOL, FRAME);
isPer = mod_ <= 2*TOL & d >= FRAME - TOL;
sc.nPer = sum(isPer);
run = 0;
for i = 1:numel(d)
    if abs(d(i) - FRAME) <= TOL, run = run + 1; else, run = 0; end
    sc.bestRun = max(sc.bestRun, run);
end
end
