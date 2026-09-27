function out = baseband_check(fname, fs, fc)
%BASEBAND_CHECK  Independent sanity check of an SDR baseband (IQ) recording.
%
%   Reads a raw interleaved IQ recording - cs8, cs16 or cf32, taken from the
%   file extension - and answers, without involving any decoder:
%
%     1. Is the file healthy?      (all-zero? clipped? DC offset?)
%     2. Is there a signal in it?  (waterfall of the whole recording)
%     3. How strong is it?         (in-band SNR versus time)
%     4. Is it really a satellite? (Doppler drift of the peak frequency)
%
%   A decoder that reports "no sync" can mean a weak signal OR wrong
%   settings. This script separates the two: it looks at the raw samples.
%
%   USAGE
%     baseband_check('C:\path\2026-08-05_20-18-16_1000000SPS_137900000Hz.cs8')
%     baseband_check(fname, 1e6, 137.9e6)
%     out = baseband_check(fname);   % also returns the numbers
%
%   INPUTS
%     fname  path to the .cs8 file
%     fs     sample rate [Hz]     (default 1e6 - read it off the filename)
%     fc     centre frequency [Hz](default 137.9e6, display only)
%
%   Base MATLAB only - no toolboxes required.

% ------------------------------------------------------------------ setup
% Called with no arguments: pop up a file browser instead of failing.
if nargin < 1 || isempty(fname)
    startDir = 'C:\Users\grigo\OneDrive\Desktop\SatDumbInput';
    if ~isfolder(startDir), startDir = pwd; end
    [f, p] = uigetfile({'*.cs8;*.cs16;*.cf32;*.raw;*.iq;*.bin', ...
                        'Baseband recordings'; '*.*', 'All files'}, ...
                       'Pick the baseband recording', startDir);
    if isequal(f, 0), fprintf('Cancelled.\n'); return; end
    fname = fullfile(p, f);
end

if nargin < 2 || isempty(fs), fs = 1e6;     end
if nargin < 3 || isempty(fc), fc = 137.9e6; end

% SatDump names its recordings <date>_<rate>SPS_<freq>Hz.<fmt> - if the
% filename carries the parameters, believe it over the defaults.
tokRate = regexp(fname, '(\d+)SPS', 'tokens', 'once');
if ~isempty(tokRate), fs = str2double(tokRate{1}); end
tokFreq = regexp(fname, '(\d+)Hz',  'tokens', 'once');
if ~isempty(tokFreq), fc = str2double(tokFreq{1}); end

% The sample format lives in the extension. Reading cs16 as cs8 (or the
% other way round) turns a perfect recording into garbage, so never guess.
[~, ~, ext] = fileparts(fname);
switch lower(ext)
    case '.cs8'
        readType = 'int8=>double';   fullScale = 127;    bytesPerSample = 2;
    case {'.cs16','.s16'}
        readType = 'int16=>double';  fullScale = 32767;  bytesPerSample = 4;
    case {'.cf32','.f32'}
        readType = 'single=>double'; fullScale = 1;      bytesPerSample = 8;
    otherwise
        warning('Unknown extension "%s" - assuming cs8.', ext);
        readType = 'int8=>double';   fullScale = 127;    bytesPerSample = 2;
end

NFFT   = 4096;   % frequency resolution: fs/NFFT = 244 Hz at 1 Msps
NAVG   = 32;     % spectra averaged per output row (smooths the noise floor)
ROWSEC = 1;      % one waterfall row per second of recording

info = dir(fname);
if isempty(info), error('File not found: %s', fname); end

nSamples = floor(info.bytes / bytesPerSample);
duration = nSamples / fs;

fprintf('\n=== baseband_check ===\n');
fprintf('File      : %s\n', info.name);
fprintf('Size      : %.2f GB (%d complex samples)\n', info.bytes/2^30, nSamples);
fprintf('Rate      : %.3f Msps  ->  DURATION %.1f s (%.1f min)\n', ...
        fs/1e6, duration, duration/60);
fprintf('Centre    : %.4f MHz\n', fc/1e6);
fprintf('Format    : %s (full scale %g)\n\n', lower(ext(2:end)), fullScale);

nRows       = floor(duration / ROWSEC);
samplesRow  = round(fs * ROWSEC);
samplesRead = NFFT * NAVG;                            % actually read per row
if samplesRead > samplesRow
    samplesRead = floor(samplesRow/NFFT)*NFFT;
    NAVG = samplesRead / NFFT;
end
if nRows < 2, error('Recording too short to analyse.'); end

% ------------------------------------------------------- read + spectrogram
fid = fopen(fname, 'r');
if fid < 0, error('Cannot open file.'); end
cleanup = onCleanup(@() fclose(fid));

S       = zeros(nRows, NFFT);        % waterfall, dB
w       = 0.5 - 0.5*cos(2*pi*(0:NFFT-1)'/NFFT);   % Hann, built by hand
nClip   = 0; nZero = 0; nSeen = 0;
sumI    = 0; sumQ  = 0;
zeroRow  = zeros(nRows, 1);          % dead-sample fraction per row
histAmp  = zeros(128, 1);            % level histogram, 128 bins over full scale
binWidth = fullScale / 128;

fprintf('Analysing');
for r = 1:nRows
    raw = fread(fid, 2*samplesRead, readType);
    if numel(raw) < 2*samplesRead, S = S(1:r-1,:); nRows = r-1; break; end

    I = raw(1:2:end);  Q = raw(2:2:end);

    % health statistics (on the samples we actually looked at)
    nClip = nClip + sum(abs(I) >= fullScale | abs(Q) >= fullScale);
    nDead = sum(I == 0 & Q == 0);
    nZero = nZero + nDead;
    nSeen = nSeen + numel(I);
    sumI  = sumI + sum(I);   sumQ = sumQ + sum(Q);

    % (1) where the dead samples sit in time, (2) how the levels are spread
    % 128 bins spanning 0..full scale, so the picture means the same thing
    % ("how much of the available range is used") in cs8, cs16 or cf32.
    zeroRow(r) = nDead / numel(I);
    bin        = min(floor(abs(I) / binWidth), 127) + 1;
    histAmp    = histAmp + accumarray(bin, 1, [128 1]);

    x = complex(I, Q);
    X = reshape(x(1:NFFT*NAVG), NFFT, NAVG) .* w;
    P = mean(abs(fft(X)).^2, 2);
    S(r,:) = 10*log10(fftshift(P) + eps);

    % skip the rest of this second
    skip = (samplesRow - samplesRead) * bytesPerSample;
    if skip > 0, fseek(fid, skip, 'cof'); end
    if mod(r, 60) == 0, fprintf('.'); end
end
fprintf(' done (%d rows)\n\n', nRows);

% ------------------------------------------------------------- file health
dcI = sumI/nSeen;  dcQ = sumQ/nSeen;
fprintf('--- file health ---\n');
fprintf('Clipped samples : %.3f %%  %s\n', 100*nClip/nSeen, ...
        tick(100*nClip/nSeen < 1, 'gain OK', 'GAIN TOO HIGH - clipping'));
fprintf('Zero samples    : %.3f %%  %s\n', 100*nZero/nSeen, ...
        tick(100*nZero/nSeen < 5, 'OK', 'DEAD SAMPLES - dropped data?'));
fprintf('DC offset       : I %+.2f  Q %+.2f  %s\n', dcI, dcQ, ...
        tick(abs(dcI) < 3 && abs(dcQ) < 3, 'OK', 'large - enable DC blocking'));

% --- Why are samples dead? Two very different faults look alike in the
% --- overall percentage, so separate them here.
%
%   QUANTISATION : the noise floor sits below 1 LSB, so most samples round
%                  to zero. Uniform in time, everything crammed into
%                  |I| = 0,1,2.  Fix = more gain, or record cs16.
%   DROPOUTS     : the capture chain (USB / CPU / disk) could not keep up
%                  and zeros were written instead. Bursty in time, and the
%                  surviving bursts have healthy levels.
%                  Fix = no cloud-synced folder, laptop on mains, faster disk.
levels   = (0:127)' * binWidth;                    % bin centres, native units
nonZero  = histAmp(2:end);
if sum(nonZero) > 0
    rmsLive = sqrt(sum(nonZero .* levels(2:end).^2) / sum(nonZero));
else
    rmsLive = 0;
end
smallFrac = sum(histAmp(1:3)) / sum(histAmp);      % bottom ~2% of the range
burstiness = std(zeroRow) / max(mean(zeroRow), eps);
bitsUsed   = log2(max(rmsLive,eps) / max(fullScale,eps)) + log2(fullScale+1);

fprintf('\n--- level usage ---\n');
fprintf('RMS of live ones: %.1f of %g full scale (~%.1f bits in use)\n', ...
        rmsLive, fullScale, max(bitsUsed, 0));

% Only argue about WHY samples are dead if a meaningful number of them are.
% Below that, "burstiness" is std/mean of a near-zero quantity - pure noise,
% and it will happily invent a dropout problem that does not exist.
if 100*nZero/nSeen < 2
    fprintf('Dead samples    : negligible - recording format is healthy.\n');
    if bitsUsed < 6
        fprintf('NOTE: only %.1f bits in use. Nothing is lost, but more gain\n', bitsUsed);
        fprintf('      would give the decoder a little more to work with.\n');
    end
else
    fprintf('Dead %% per sec  : mean %.1f %%, spread %.1f %% (burstiness %.2f)\n', ...
            100*mean(zeroRow), 100*std(zeroRow), burstiness);
    if burstiness > 0.35
        fprintf('DIAGNOSIS: BURSTY -> dropped samples. The capture chain could not\n');
        fprintf('           keep up (cloud-synced folder / CPU throttling / disk).\n');
    elseif rmsLive < fullScale/16
        fprintf('DIAGNOSIS: UNIFORM and tiny -> quantisation. The level uses only\n');
        fprintf('           the bottom of the range. Raise the gain, or record in\n');
        fprintf('           a wider format (cs8 -> cs16).\n');
    else
        fprintf('DIAGNOSIS: mixed / unclear - look at the two extra plots.\n');
    end
end

% ------------------------------------------------------------- SNR vs time
f   = (-NFFT/2 : NFFT/2-1)' * (fs/NFFT);     % baseband frequency axis [Hz]
Slin = 10.^(S/10);

% LRPT at 72 kSym OQPSK occupies roughly +/-70 kHz around the carrier.
% The DC bin is excluded: the Pluto puts a narrow spurious spike there.
sigIdx   = abs(f) <= 70e3 & abs(f) >= 3e3;
noiseIdx = abs(f) >= 200e3 & abs(f) <= 450e3;

Psig   = mean(Slin(:, sigIdx),   2);
Pnoise = mean(Slin(:, noiseIdx), 2);
snr    = 10*log10( max(Psig - Pnoise, eps) ./ Pnoise );

t = (0:nRows-1)' * ROWSEC;
[snrMax, iMax] = max(snr);

% peak frequency inside the signal band, per row -> Doppler signature
fSig = f(sigIdx);
[~, iPk] = max(Slin(:, sigIdx), [], 2);
fPeak = fSig(iPk);

fprintf('\n--- signal ---\n');
fprintf('Best in-band SNR: %.1f dB at t = %.0f s (%.1f min into the pass)\n', ...
        snrMax, t(iMax), t(iMax)/60);
if snrMax > 6
    fprintf('VERDICT: a signal IS present. A decoder failing on this file\n');
    fprintf('         is a settings problem, not a reception problem.\n');
elseif snrMax > 2
    fprintf('VERDICT: something weak is there - marginal, near the limit.\n');
else
    fprintf('VERDICT: no usable signal in this recording.\n');
end

% ------------------------------------------------------------------- plots
figure('Name', 'baseband_check', 'Color', 'w');

subplot(3,1,[1 2]);
imagesc(f/1e3, t, S); axis xy;
xlabel('offset from centre [kHz]'); ylabel('time [s]');
title(sprintf('%s  -  %.4f MHz', strrep(info.name,'_','\_'), fc/1e6));
cb = colorbar; cb.Label.String = 'dB';
% clip the colour scale to the useful range so the signal stands out
med = median(S(:));
clim([med-5, med+25]);

subplot(3,1,3);
yyaxis left
plot(t, snr, 'LineWidth', 1.2); ylabel('in-band SNR [dB]'); grid on
yyaxis right
plot(t, fPeak/1e3, '.', 'MarkerSize', 4); ylabel('peak offset [kHz]');
xlabel('time [s]');
title('SNR and peak frequency (a satellite drifts smoothly - that is Doppler)');

% --- second figure: the two health diagnostics -------------------------
figure('Name', 'baseband_check - health', 'Color', 'w');

subplot(2,1,1);
plot(t, 100*zeroRow, 'LineWidth', 1.0); grid on; ylim([-2 102]);
xlabel('time [s]'); ylabel('dead samples [%]');
title('Dead samples versus time (flat = quantisation, bursty = dropouts)');

subplot(2,1,2);
bar(levels(1:32)/fullScale*100, histAmp(1:32)/sum(histAmp)*100, 'histc');
grid on; xlabel('|I| [% of full scale]'); ylabel('share of samples [%]');
title('Level distribution (all in the first bins = the range is wasted)');

% ------------------------------------------------------------------ output
if nargout
    out = struct('duration',duration,'t',t,'snr',snr,'fpeak',fPeak, ...
                 'S',S,'f',f,'snrMax',snrMax,'tMax',t(iMax), ...
                 'clipPct',100*nClip/nSeen,'zeroPct',100*nZero/nSeen, ...
                 'dcI',dcI,'dcQ',dcQ,'zeroRow',zeroRow,'histAmp',histAmp, ...
                 'rmsLive',rmsLive,'burstiness',burstiness);
end
end

% -------------------------------------------------------------------------
function s = tick(cond, okMsg, badMsg)
if cond, s = ['[OK] '  okMsg]; else, s = ['[!!] ' badMsg]; end
end
