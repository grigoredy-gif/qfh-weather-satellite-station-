function out = signal_id(fname, tSeg, fs, fc)
%SIGNAL_ID  Identify what a recorded signal actually IS, without any decoder.
%
%   Cuts the strong segment out of a baseband recording and measures, from
%   the raw samples alone:
%
%     1. Occupied bandwidth  - how wide is the signal really?
%     2. SYMBOL RATE         - a digital signal repeats its symbol clock;
%                              the spectrum of |x|^2 shows a sharp line at
%                              exactly the symbol rate. No decoder needed.
%     3. Carrier signature   - the spectrum of x^4 shows a line for plain
%                              QPSK; OQPSK suppresses it. Bonus evidence.
%
%   WHY: a decoder that refuses to lock cannot tell you whether the signal
%   is the wrong format or the software is broken. Measuring the symbol
%   rate directly settles it: 72k -> the LRPT 72k pipeline SHOULD work and
%   the failure is software-side; anything else -> we were decoding the
%   wrong thing all along.
%
%   USAGE
%     signal_id                          % file picker, default segment
%     signal_id(fname, [230 360])        % explicit good-segment in seconds
%     out = signal_id(...)               % also returns the numbers
%
%   Base MATLAB only - no toolboxes required.

% ------------------------------------------------------------------ setup
if nargin < 1 || isempty(fname)
    startDir = 'C:\Users\grigo\OneDrive\Desktop\SatDumbInput';
    if ~isfolder(startDir), startDir = pwd; end
    [f, p] = uigetfile({'*.cs8;*.cs16;*.cf32;*.raw;*.iq;*.bin', ...
                        'Baseband recordings'; '*.*', 'All files'}, ...
                       'Pick the baseband recording', startDir);
    if isequal(f, 0), fprintf('Cancelled.\n'); return; end
    fname = fullfile(p, f);
end
if nargin < 2 || isempty(tSeg), tSeg = [230 360]; end   % the good segment
if nargin < 3 || isempty(fs),   fs = 1e6;   end
if nargin < 4 || isempty(fc),   fc = 137.9e6; end

tokRate = regexp(fname, '(\d+)SPS', 'tokens', 'once');
if ~isempty(tokRate), fs = str2double(tokRate{1}); end
tokFreq = regexp(fname, '(\d+)Hz',  'tokens', 'once');
if ~isempty(tokFreq), fc = str2double(tokFreq{1}); end

[~, ~, ext] = fileparts(fname);
switch lower(ext)
    case '.cs8'
        readType = 'int8=>double';   bytesPerSample = 2;
    case {'.cs16','.s16'}
        readType = 'int16=>double';  bytesPerSample = 4;
    case {'.cf32','.f32'}
        readType = 'single=>double'; bytesPerSample = 8;
    otherwise
        warning('Unknown extension "%s" - assuming cs8.', ext);
        readType = 'int8=>double';   bytesPerSample = 2;
end

info = dir(fname);
if isempty(info), error('File not found: %s', fname); end
nSamples = floor(info.bytes / bytesPerSample);
duration = nSamples / fs;

tSeg(1) = max(0, tSeg(1));
tSeg(2) = min(duration, tSeg(2));
if diff(tSeg) < 5, error('Segment too short (%.1f s) - give tSeg=[t1 t2].', diff(tSeg)); end

fprintf('\n=== signal_id ===\n');
fprintf('File     : %s\n', info.name);
fprintf('Duration : %.1f s   -   analysing t = %.0f..%.0f s (%.0f s)\n', ...
        duration, tSeg(1), tSeg(2), diff(tSeg));
fprintf('Rate     : %.3f Msps   Centre: %.4f MHz\n\n', fs/1e6, fc/1e6);

% ---------------------------------------------------------------- analysis
NPSD  = 8192;                 % PSD resolution: fs/NPSD = 122 Hz at 1 Msps
NENV  = 2^19;                 % clock-line resolution: fs/NENV = 1.9 Hz
blkLen = round(fs);           % process one second at a time (memory!)

wPSD = 0.5 - 0.5*cos(2*pi*(0:NPSD-1)'/NPSD);
wENV = 0.5 - 0.5*cos(2*pi*(0:NENV-1)'/NENV);

P = zeros(NPSD, 1);  E = zeros(NENV, 1);  Q4 = zeros(NENV, 1);
nBlk = 0;

fid = fopen(fname, 'r');
if fid < 0, error('Cannot open file.'); end
cleanup = onCleanup(@() fclose(fid));
fseek(fid, round(tSeg(1)*fs) * bytesPerSample, 'bof');

fprintf('Analysing');
for b = 1:floor(diff(tSeg))
    raw = fread(fid, 2*blkLen, readType);
    if numel(raw) < 2*blkLen, break; end
    x = complex(raw(1:2:end), raw(2:2:end));
    x = x - mean(x);                          % kill DC / LO leak
    x = x / max(sqrt(mean(abs(x).^2)), eps);  % normalise per block

    % (1) averaged spectrum
    K  = floor(blkLen/NPSD);
    Xw = reshape(x(1:K*NPSD), NPSD, K) .* wPSD;
    P  = P + mean(abs(fft(Xw)).^2, 2);

    % (2) symbol-clock line: spectrum of the instantaneous power |x|^2.
    % Any linearly modulated signal is cyclostationary - its power "breathes"
    % once per symbol, so a sharp line appears at exactly the symbol rate.
    env = abs(x(1:NENV)).^2;
    env = env - mean(env);
    E   = E + abs(fft(env .* wENV)).^2;

    % (3) x^4: plain QPSK collapses to a tone at 4x the carrier offset;
    % OQPSK's half-symbol stagger suppresses it. Weak evidence, but free.
    q  = x(1:NENV).^4;
    q  = q - mean(q);
    Q4 = Q4 + abs(fft(q .* wENV)).^2;

    nBlk = nBlk + 1;
    if mod(b, 20) == 0, fprintf('.'); end
end
fprintf(' done (%d s used)\n\n', nBlk);
if nBlk < 5, error('Could not read enough data from the segment.'); end

% -------------------------------------------------- 1: occupied bandwidth
fP   = (-NPSD/2 : NPSD/2-1)' * (fs/NPSD);
Plin = fftshift(P);
nfl  = median(Plin);                          % noise floor estimate
Pex  = max(Plin - nfl, 0);                    % signal power above the floor
c    = cumsum(Pex) / max(sum(Pex), eps);
fLo  = fP(find(c >= 0.005, 1));
fHi  = fP(find(c >= 0.995, 1));
fMid = fP(find(c >= 0.5,   1));
obw  = fHi - fLo;

fprintf('--- occupied bandwidth (99%% of above-floor power) ---\n');
fprintf('Width  : %.1f kHz   (LRPT 72k is ~%.0f kHz, 80k is ~%.0f kHz)\n', ...
        obw/1e3, 72e3*1.4/1e3, 80e3*1.4/1e3);
fprintf('Centre : %+.1f kHz off the recording centre\n\n', fMid/1e3);

% -------------------------------------------------- 2: symbol-rate line
fE   = (0:NENV-1)' * (fs/NENV);
half = fE <= fs/2;
fE   = fE(half);  Elin = E(half);

% search everywhere a plausible clock could be
[fClk, promClk] = strongestLine(fE, Elin, [20e3 200e3]);
[p72, f72] = lineNear(fE, Elin, 72e3, 500);
[p80, f80] = lineNear(fE, Elin, 80e3, 500);

fprintf('--- symbol-rate lines (spectrum of |x|^2) ---\n');
fprintf('Strongest line 20-200 kHz : %.1f Hz  (%.1f dB above local floor)\n', fClk, promClk);
fprintf('Line near 72 000 Hz       : %.1f Hz  (%.1f dB)\n', f72, p72);
fprintf('Line near 80 000 Hz       : %.1f Hz  (%.1f dB)\n', f80, p80);

% -------------------------------------------------- 3: x^4 carrier check
fQ  = (-NENV/2 : NENV/2-1)' * (fs/NENV);
Q4s = fftshift(Q4);
[pQ4, iQ4] = max(Q4s .* (abs(fQ) < 100e3));   % only look near the carrier
promQ4 = 10*log10(pQ4 / median(Q4s));
fprintf('\n--- x^4 carrier signature ---\n');
fprintf('Strongest x^4 line: %+.1f Hz offset/4 = %+.1f Hz  (%.1f dB)\n', ...
        fQ(iQ4), fQ(iQ4)/4, promQ4);
fprintf('(strong line -> plain QPSK; absent -> OQPSK or not PSK at all)\n');

% ----------------------------------------------------------------- verdict
fprintf('\n--- VERDICT ---\n');
if p72 >= 8 && p72 >= p80
    fprintf('Symbol clock at %.1f Hz -> this IS a 72k signal.\n', f72);
    fprintf('The LRPT 72k pipeline is the right one; a deframer that still\n');
    fprintf('fails on this file is a software/format problem, not a signal one.\n');
elseif p80 >= 8
    fprintf('Symbol clock at %.1f Hz -> this is an 80k signal.\n', f80);
    fprintf('Decode with the 80k pipeline.\n');
elseif promClk >= 8
    fprintf('Clear symbol clock at %.1f Hz - neither 72k nor 80k!\n', fClk);
    fprintf('We were decoding the wrong thing. Look this rate up.\n');
else
    fprintf('NO clear symbol clock found (best: %.1f dB at %.1f Hz).\n', promClk, fClk);
    fprintf('Either the SNR in this segment is too low for the clock line,\n');
    fprintf('or the signal is not a linearly modulated digital downlink.\n');
end

% ------------------------------------------------------------------- plots
figure('Name', 'signal_id', 'Color', 'w');

subplot(3,1,1);
plot(fP/1e3, 10*log10(Plin + eps), 'LineWidth', 0.8); grid on;
hold on; xline(fLo/1e3, 'r--'); xline(fHi/1e3, 'r--');
xlabel('offset [kHz]'); ylabel('PSD [dB]');
title(sprintf('Averaged spectrum - 99%% power between the red lines (%.1f kHz)', obw/1e3));
xlim([-250 250]);

subplot(3,1,2);
plot(fE/1e3, 10*log10(Elin + eps), 'LineWidth', 0.8); grid on;
hold on; xline(72, 'g--', '72k'); xline(80, 'm--', '80k');
xlabel('frequency [kHz]'); ylabel('|x|^2 spectrum [dB]');
title('Symbol-clock search - a sharp spike ON a dashed line names the rate');
xlim([40 120]);

subplot(3,1,3);
plot(fQ/1e3, 10*log10(Q4s + eps), 'LineWidth', 0.8); grid on;
xlabel('offset [kHz]'); ylabel('x^4 spectrum [dB]');
title('x^4 carrier signature (sharp central spike = plain QPSK)');
xlim([-100 100]);

% ------------------------------------------------------------------ output
if nargout
    out = struct('obw',obw,'fMid',fMid,'fClk',fClk,'promClk',promClk, ...
                 'f72',f72,'p72',p72,'f80',f80,'p80',p80, ...
                 'fQ4',fQ(iQ4),'promQ4',promQ4,'nBlk',nBlk);
end
end

% -------------------------------------------------------------------------
function [prom, fpk] = lineNear(f, S, f0, tol)
% height of the strongest bin within f0 +/- tol, in dB above the local floor
win = abs(f - f0) <= tol;
[pk, i] = max(S .* win);
fpk = f(find(win, 1) - 1 + find(S(win) == max(S(win)), 1));
loc = abs(f - f0) <= 5e3 & abs(f - fpk) > 300;
prom = 10*log10(pk / max(median(S(loc)), eps));
if isempty(fpk), fpk = f0; prom = 0; end
% keep MATLAB happy about unused variable
i = i; %#ok<NASGU,ASGSL>
end

function [fpk, prom] = strongestLine(f, S, band)
% strongest narrow line in the band, in dB above a sliding median floor
in  = f >= band(1) & f <= band(2);
fi  = f(in);  Si = S(in);
flo = movmedian(Si, 2001);
[~, i] = max(Si ./ max(flo, eps));
fpk  = fi(i);
prom = 10*log10(Si(i) / max(flo(i), eps));
end
