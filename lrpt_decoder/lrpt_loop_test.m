function lrpt_loop_test(symFile)
%LRPT_LOOP_TEST  Is the transmission a repeating test loop, or real data?
%
%   The frame hunt found ASM sync markers with a super-period of
%   25152 chips (1572 bytes, two ASMs per period at a 424/1148 split) -
%   NOT the standard 16384-chip CADU. Two possibilities remain:
%
%     LOOP : the satellite replays the same test pattern forever.
%            Then the chip stream must agree with itself at a lag of
%            exactly one super-period (~86-92 % given the chip BER,
%            vs 50 % at any random lag).
%     DATA : the frames carry changing payload (real, oddly framed).
%            Then self-agreement at the super-period stays at ~50 %,
%            like every other lag.
%
%   Uses the winning stream (rails d0), raw bits WITHOUT differential
%   decoding (content repetition is invariant to that), block-wise with
%   +/-3 chips of local alignment search to ride out clock jitter.
%
%   USAGE:  lrpt_loop_test            (picker for the *_sym.mat)
%
%   Base MATLAB only.

if nargin < 1 || isempty(symFile)
    startDir = 'C:\SDR';
    if ~isfolder(startDir), startDir = pwd; end
    [f, p] = uigetfile({'*.mat', 'lrpt_sync output'}, ...
                       'Pick the symbol file', startDir);
    if isequal(f, 0), fprintf('Cancelled.\n'); return; end
    symFile = fullfile(p, f);
end
S = load(symFile);
fprintf('\n=== lrpt_loop_test ===\nSymbols: %s\n', S.meta.fname);

c  = S.c0;                              % the winning rail alignment
bI = real(c) < 0;   bQ = imag(c) < 0;
u  = false(2*numel(bI), 1);
u(1:2:end) = bI;  u(2:2:end) = bQ;
Nu = numel(u);

L0   = 25152;                           % the measured super-period [chips]
lags = [L0, 2*L0, 16384, 6784, 18368, 11111, 20000, 30011];
lagName = {'SUPER-PERIOD 25152', '2x super-period', 'standard CADU 16384', ...
           'atom A 6784', 'atom B 18368', 'control 11111', ...
           'control 20000', 'control 30011'};

BLK = L0;                               % compare in one-period blocks
fprintf('%-22s | %s\n', 'lag', 'self-agreement (50% = random, >75% = repeated)');
agg0 = NaN;
for k = 1:numel(lags)
    L = lags(k);
    nBlk = floor((Nu - L - 3) / BLK) - 1;
    if nBlk < 3, fprintf('%-22s | (not enough data)\n', lagName{k}); continue; end
    nBlk = min(nBlk, 200);
    a = zeros(nBlk, 1);
    for b = 1:nBlk
        i0 = (b-1)*BLK + 4;             % +4 leaves room for the -3 offset
        s1 = u(i0 : i0+BLK-1);
        bestA = 0;
        for off = -3:3
            s2 = u(i0+L+off : i0+L+off+BLK-1);
            bestA = max(bestA, mean(s1 == s2));
        end
        a(b) = bestA;
    end
    fprintf('%-22s | mean %.1f %%   (blocks 25-75%%: %.1f - %.1f %%)\n', ...
            lagName{k}, 100*mean(a), 100*prctile2(a,25), 100*prctile2(a,75));
    if k == 1, agg0 = mean(a); end
end

% NRZ-M differential encoding can turn a repeated pattern into a perfectly
% ANTI-correlated one (bits inverted every period, when the period's parity
% is odd) - so the statistic is the DISTANCE from 50 %, in either direction.
rep = max(agg0, 1 - agg0);
fprintf('\n--- VERDICT ---\n');
if rep > 0.75
    if agg0 < 0.5
        fprintf('(anti-correlated at %.0f %% - the NRZ-M parity flips each period;\n', 100*agg0);
        fprintf(' that is still an exact repetition of the content)\n');
    end
    fprintf('REPEATING LOOP. The stream repeats itself at the super-period:\n');
    fprintf('the satellite is replaying a fixed test pattern - there are no\n');
    fprintf('images in this signal, and there is nothing any decoder could do.\n');
elseif rep < 0.6
    fprintf('CHANGING CONTENT. The frames carry real, varying payload in a\n');
    fprintf('nonstandard 1572-byte framing. Decoding is possible in principle:\n');
    fprintf('next step is Viterbi-decoding the bytes after each ASM to read\n');
    fprintf('the frame headers and identify the format.\n');
else
    fprintf('PARTIAL repetition (%.0f %% agreement) - mixed/idle frames with\n', 100*agg0);
    fprintf('some fixed fields. Decode the post-ASM headers to see what is fixed.\n');
end
end

% ------------------------------------------------------------------------
function q = prctile2(x, p)
% base-MATLAB percentile (no toolbox): linear interpolation on sorted data
x = sort(x(:));
n = numel(x);
r = 1 + (p/100)*(n-1);
lo = floor(r);  hi = ceil(r);
q = x(lo) + (r-lo)*(x(hi)-x(lo));
end
