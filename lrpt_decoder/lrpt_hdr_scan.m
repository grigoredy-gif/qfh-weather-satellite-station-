function out = lrpt_hdr_scan(symFile)
%LRPT_HDR_SCAN  Brute-force header scan: where exactly do valid AOS headers
%               live, and under which randomizer convention?
%
%   lrpt_walk failed at markerless boundaries, so instead of hypothesising
%   the geometry we scan EVERY byte offset of a long decoded stretch and
%   test, at each position, whether the 6 bytes read as a sane AOS header
%   (ver 1 / scid 0 / vcid 5) under either convention:
%
%     RESTART : PN phase 0 at this offset (randomizer restarts here)
%     CONT    : PN phase = offset mod 255 (continuous since the anchor ASM)
%
%   16 fixed bits per test -> ~0.25 chance hits per convention over 16k
%   offsets: every real header stands out individually. The list of hit
%   offsets + their counters IS the frame map.
%
%   USAGE:  lrpt_hdr_scan            (picker for the *_sym.mat)
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
fprintf('\n=== lrpt_hdr_scan ===\nSymbols: %s\n', S.meta.fname);

NBYTES = 16000;

% ---------------- winning chip stream + template + Viterbi (as elsewhere)
c  = S.c0;
bI = real(c) < 0;   bQ = imag(c) < 0;
bi = xor(bI(2:end), bI(1:end-1));
bq = xor(bQ(2:end), bQ(1:end-1));
u  = false(2*numel(bi), 1);
u(1:2:end) = bi;  u(2:2:end) = bq;

G1 = [1 1 1 1 0 0 1];  G2 = [1 0 1 1 0 1 1];
asm = '1ACFFC1D';
asmBits = zeros(32,1);
for i = 1:8
    nib = hex2dec(asm(i));
    asmBits(4*i-3:4*i) = bitget(nib, 4:-1:1)';
end
reg = zeros(6,1);  chips = zeros(64,1);
for k = 1:32
    r7 = [asmBits(k); reg];
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

outc = zeros(64, 2, 2);
for s = 0:63
    sv = bitget(s, 6:-1:1)';
    for b = 0:1
        r7 = [b; sv];
        outc(s+1, b+1, 1) = mod(sum(r7 .* G1'), 2);
        outc(s+1, b+1, 2) = mod(sum(r7 .* G2'), 2);
    end
end

% Pick the anchor from the DENSEST detection region, not the "strongest"
% peak: correlation saturates at 52 wherever the signal is good, so the
% strongest-first tie-break lands on the earliest peak = the noisy edge of
% the pass. Detection density is the honest SNR proxy.
pkOK  = pk(pk + 2*8*(NBYTES+8) <= numel(u));
dens  = zeros(size(pkOK));
for i = 1:numel(pkOK)
    dens(i) = sum(abs(pk - pkOK(i) - 8*NBYTES) <= 8*NBYTES);   % peaks in window
end
[~, ib] = max(dens);
anchor = pkOK(ib);
fprintf('Anchor at chip %d (%.0f s into the segment), %d detections in window\n', ...
        anchor, anchor/144000, dens(ib));
fprintf('Deep Viterbi decode of %d bytes after the strongest ASM...\n', NBYTES);
rx = double(u(anchor+1 : anchor+2*8*(NBYTES+8)));
db = vdecode(rx, s0, 8*(NBYTES+8), outc);
db = db(1:8*NBYTES);
BY = packBytes(db);                          % raw (randomized) bytes

% chip-domain ASM detections inside this window (looser threshold), bytes
pk40  = findPeaks(abs(xc), 40);
inWin = pk40(pk40 > anchor & pk40 <= anchor + 16*NBYTES) - anchor;
asmAt = round(inWin/16);                     % ASM END offsets [bytes]

% CCSDS PN core: the sequence period is 255 BITS (8-stage m-sequence)
pnBit = ones(300, 1);
for n = 1:numel(pnBit)-8
    pnBit(n+8) = mod(pnBit(n+7) + pnBit(n+5) + pnBit(n+3) + pnBit(n), 2);
end
pnCore = pnBit(1:255);

% ------------------------------------------------------------- the scan
fprintf('Scanning %d offsets x 2 randomizer conventions...\n\n', NBYTES-6);
hits = [];
idx0 = mod((0:47)', 255) + 1;                % PN phase 0 (restart here)
for o = 0:NBYTES-7
    segBits = db(8*o+1 : 8*o+48);
    % RESTART: PN restarts at this offset
    d1 = packBytes(xor(segBits, pnCore(idx0)));
    % CONTINUOUS: PN running since the anchor (bit phase = 8*o mod 255)
    d2 = packBytes(xor(segBits, pnCore(mod(8*o + (0:47)', 255) + 1)));
    for conv = 1:2
        if conv == 1, d = d1; else, d = d2; end
        ver  = floor(d(1)/64);
        scid = mod(d(1),64)*4 + floor(d(2)/64);
        vcid = mod(d(2), 64);
        if ver == 1 && scid == 0            % ANY vcid - report it
            ctr = d(3)*65536 + d(4)*256 + d(5);
            % does an ASM sit right before this header? (marker evidence)
            aham = 32;
            if o >= 4
                aham = sum(db(8*(o-4)+1 : 8*o) ~= asmBits);
            end
            hits = [hits; o, conv, vcid, ctr, d(6), aham]; %#ok<AGROW>
        end
    end
end

if isempty(hits)
    fprintf('No ver-1/scid-0 headers at ANY offset under either convention.\n');
else
    fprintf('%-8s %-8s %-5s %-10s %-8s %-5s %-8s %-8s %s\n', ...
            'offset', 'PNconv', 'vcid', 'counter', 'ctrHex', 'sig', ...
            'asmHam', 'gapPrev', 'nearASM?');
    for i = 1:size(hits,1)
        gp = '-';
        if i > 1, gp = sprintf('%d', hits(i,1) - hits(i-1,1)); end
        nearA = '';
        if any(abs(asmAt - hits(i,1)) <= 1), nearA = 'ASM'; end
        cv = 'RST';
        if hits(i,2) == 2, cv = 'CONT'; end
        fprintf('%-8d %-8s %-5d %-10d %-8s %-5d %-8d %-8s %s\n', ...
                hits(i,1), cv, hits(i,3), hits(i,4), ...
                dec2hex(hits(i,4), 6), hits(i,5), hits(i,6), gp, nearA);
    end
    fprintf('\n%d hits (10-bit ver/scid gate -> ~%d chance hits expected;\n', ...
            size(hits,1), round(2*(NBYTES-6)/1024));
    fprintf('real frames give themselves away by asmHam <= 8, coherent\n');
    fprintf('counters, and gap structure).\n');
end

if nargout, out = struct('hits',hits,'asmAt',asmAt,'BY',BY); end
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
