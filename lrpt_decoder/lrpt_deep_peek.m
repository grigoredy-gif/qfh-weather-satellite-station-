function out = lrpt_deep_peek(symFile)
%LRPT_DEEP_PEEK  Decode straight through the super-period and expose the
%                hidden frame markers.
%
%   lrpt_viterbi_peek proved the detected ASMs start genuine AOS frames
%   (ver 1, scid 0, vcid 5 = Meteor MSU-MR, live counters) but the counter
%   arithmetic shows frames BETWEEN our detections that carry a sync marker
%   which is NOT 1ACFFC1D. Sync markers are not randomized, so decoding a
%   full super-period in one go makes any hidden marker appear VERBATIM in
%   the decoded bytes at its true offset.
%
%   Does three things:
%     1. decodes 1600 bytes after the strongest ASMs (through the whole
%        1572-byte super-period), prints the raw bytes around the expected
%        boundaries (offset ~424 and ~1148) and at the next period start
%     2. scans all decoded blocks for byte columns that are CONSTANT across
%        frames - fixed markers/headers expose themselves this way
%     3. tabulates (byte-gap, counter-step) for adjacent detected ASMs -
%        the frame-accounting evidence in one table
%
%   USAGE:  lrpt_deep_peek           (picker for the *_sym.mat)
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
fprintf('\n=== lrpt_deep_peek ===\nSymbols: %s\n', S.meta.fname);

NLONG = 1600;                 % bytes per deep decode (covers a full period)
NBLK  = 12;                   % how many deep decodes

% ---------------- winning chip stream + template (as in the other tools)
c  = S.c0;
bI = real(c) < 0;   bQ = imag(c) < 0;
bi = xor(bI(2:end), bI(1:end-1));
bq = xor(bQ(2:end), bQ(1:end-1));
u  = false(2*numel(bi), 1);
u(1:2:end) = bi;  u(2:2:end) = bq;

G1 = [1 1 1 1 0 0 1];  G2 = [1 0 1 1 0 1 1];
asm = '1ACFFC1D';
bits = zeros(32,1);
for i = 1:8
    nib = hex2dec(asm(i));
    bits(4*i-3:4*i) = bitget(nib, 4:-1:1)';
end
reg = zeros(6,1);  chips = zeros(64,1);
for k = 1:32
    r7 = [bits(k); reg];
    chips(2*k-1) = mod(sum(r7 .* G1'), 2);
    chips(2*k)   = mod(sum(r7 .* G2'), 2);
    reg = r7(1:6);
end
tpl = 1 - 2*chips(13:64);
s0  = reg(1)*32 + reg(2)*16 + reg(3)*8 + reg(4)*4 + reg(5)*2 + reg(6);

upm = 1 - 2*double(u);
xc  = filter(flipud(tpl), 1, upm);
pk  = findPeaks(abs(xc), 46);
if sign(median(xc(pk))) < 0, u = ~u; end

% Viterbi tables
outc = zeros(64, 2, 2);
for s = 0:63
    sv = bitget(s, 6:-1:1)';
    for b = 0:1
        r7 = [b; sv];
        outc(s+1, b+1, 1) = mod(sum(r7 .* G1'), 2);
        outc(s+1, b+1, 2) = mod(sum(r7 .* G2'), 2);
    end
end

% ------------------- 3: frame accounting: (byte gap, counter step) pairs
% short decode (8 bytes) after EVERY detection to read its counter
nShort = 8*10;
ctr = NaN(numel(pk),1);
okDecode = pk + 2*(nShort+48) <= numel(u);
pnBits = ones(8*NLONG + 64, 1);
for n = 1:numel(pnBits)-8
    pnBits(n+8) = mod(pnBits(n+7) + pnBits(n+5) + pnBits(n+3) + pnBits(n), 2);
end
for k = 1:numel(pk)
    if ~okDecode(k), continue; end
    rx = double(u(pk(k)+1 : pk(k)+2*(nShort+24)));
    db = vdecode(rx, s0, nShort+24, outc);
    d  = xor(db(1:nShort), pnBits(1:nShort));
    by = packBytes(d);
    ctr(k) = by(3)*65536 + by(4)*256 + by(5);
end
fprintf('\n--- frame accounting: adjacent detections ---\n');
fprintf('%-10s %-10s %-12s %s\n', 'byteGap', 'ctrStep', 'bytes/step', '(count)');
gaps  = round(diff(pk)/16);
steps = diff(ctr);
valid = ~isnan(steps) & steps > 0 & steps < 50;
pairKey = gaps(valid)*1000 + steps(valid);
[up, ~, ic] = unique(pairKey);
cnt = accumarray(ic, 1);
[cnt, si] = sort(cnt, 'descend');  up = up(si);
for i = 1:min(8, numel(up))
    g = floor(up(i)/1000);  st = mod(up(i), 1000);
    fprintf('%-10d %-10d %-12.1f x%d\n', g, st, g/st, cnt(i));
end

% ------------------------------- 1+2: deep decodes through the period
[~, strongest] = sort(abs(xc(pk)), 'descend');
sel = pk(strongest);
sel = sel(sel + 2*8*(NLONG+8) <= numel(u));
sel = sel(1:min(NBLK, numel(sel)));
fprintf('\nDeep-decoding %d bytes after %d strong ASMs...\n', NLONG, numel(sel));
BY = zeros(numel(sel), NLONG);
for k = 1:numel(sel)
    rx = double(u(sel(k)+1 : sel(k)+2*8*(NLONG+8)));
    db = vdecode(rx, s0, 8*(NLONG+8), outc);
    BY(k,:) = packBytes(db(1:8*NLONG))';
end

% constant byte columns across blocks = fixed structure (markers, headers)
agree = zeros(1, NLONG);
mode_ = zeros(1, NLONG);
for j = 1:NLONG
    col = BY(:,j);
    [uv, ~, ici] = unique(col);
    cc = accumarray(ici, 1);
    [mx, im] = max(cc);
    agree(j) = mx / numel(col);
    mode_(j) = uv(im);
end
fixedIdx = find(agree >= 0.75);
fprintf('\n--- byte offsets constant across >=75%% of the %d blocks ---\n', numel(sel));
if isempty(fixedIdx)
    fprintf('(none - every offset varies)\n');
else
    % group consecutive offsets into runs and print them as hex strings
    runStart = fixedIdx([true, diff(fixedIdx) > 1]);
    runEnd   = fixedIdx([diff(fixedIdx) > 1, true]);
    for r = 1:numel(runStart)
        span = runStart(r):runEnd(r);
        if numel(span) < 2, continue; end
        fprintf('offset %5d..%5d : %s\n', span(1)-1, span(end)-1, ...
                sprintf('%02X ', mode_(span)));
    end
end

% raw hex around the expected hidden boundaries, first 3 blocks
fprintf('\n--- raw decoded bytes around candidate boundaries (block 1) ---\n');
for off = [416 560 990 1140 1560]
    if off+24 <= NLONG
        fprintf('@%5d: %s\n', off, sprintf('%02X ', BY(1, off+1:off+24)));
    end
end

if nargout, out = struct('BY',BY,'agree',agree,'mode',mode_, ...
                          'gaps',gaps,'steps',steps,'pk',pk,'ctr',ctr); end
end

% -------------------------------------------------------------------------
function bitsOut = vdecode(rx, s0, nBits, outc)
PM = inf(64,1);  PM(s0+1) = 0;
prev = zeros(64, nBits, 'uint8');
ns   = (0:63)';
bvec = floor(ns/32);
sA   = 2*mod(ns,32) + 1;
sB   = sA + 1;
liA  = sA + 64*bvec;
liB  = sB + 64*bvec;
o1 = squeeze(outc(:,:,1));  o2 = squeeze(outc(:,:,2));
for t = 1:nBits
    cost = double(o1 ~= rx(2*t-1)) + double(o2 ~= rx(2*t));
    cand = PM + cost;
    mA = cand(liA);  mB = cand(liB);
    takeB = mB < mA;
    PMn = mA;  PMn(takeB) = mB(takeB);
    pS  = sA;  pS(takeB) = sB(takeB);
    prev(:, t) = uint8(pS - 1);
    PM = PMn;
end
[~, sEnd] = min(PM);
s = sEnd - 1;
bitsOut = zeros(nBits, 1);
for t = nBits:-1:1
    bitsOut(t) = floor(s/32);
    s = double(prev(s+1, t));
end
end

function by = packBytes(bits)
n  = floor(numel(bits)/8);
by = bits(1:8:8*n)*128 + bits(2:8:8*n)*64 + bits(3:8:8*n)*32 + ...
     bits(4:8:8*n)*16  + bits(5:8:8*n)*8  + bits(6:8:8*n)*4 + ...
     bits(7:8:8*n)*2   + bits(8:8:8*n);
end

function pk = findPeaks(a, thr)
idx = find(a >= thr);
pk = [];
while ~isempty(idx)
    grp = idx(idx <= idx(1) + 8);
    [~, gi] = max(a(grp));
    pk(end+1,1) = grp(gi); %#ok<AGROW>
    idx(idx <= grp(end) + 8) = [];
end
end
