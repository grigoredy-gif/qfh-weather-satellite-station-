function out = lrpt_viterbi_peek(symFile)
%LRPT_VITERBI_PEEK  Decode the bytes after each ASM and read the headers.
%
%   The frame hunt proved the stream contains convolutionally-encoded ASMs
%   with a nonstandard 1572-byte super-period (two ASMs per period, split
%   424/1148 bytes). This tool answers "what IS this format?" by letting
%   the satellite label itself:
%
%     1. rebuild the winning chip stream (rails d0, NRZ-M diff, C1-first)
%     2. find every ASM (same 52-chip template as lrpt_frame_hunt)
%     3. Viterbi-decode (K=7, G1=171o, G2=133o) 64 bytes after each ASM.
%        The encoder state at the first data bit is KNOWN - it is fixed by
%        the last 6 ASM bits - so the decode starts fully synchronized.
%     4. show the bytes raw AND de-randomized with the standard CCSDS PN
%        (x^8+x^7+x^5+x^3+1, all-ones seed), parse the AOS frame header
%        (version / spacecraft ID / virtual channel / frame counter) and
%        check whether the counters increment sanely.
%
%   Incrementing counters + a stable spacecraft ID = real telemetry frames,
%   format identified from the inside. Garbage in both raw and derand =
%   the payload uses a nonstandard randomizer too.
%
%   USAGE:  lrpt_viterbi_peek        (picker for the *_sym.mat)
%
%   Base MATLAB only.

% ------------------------------------------------------------------ input
if nargin < 1 || isempty(symFile)
    startDir = 'C:\SDR';
    if ~isfolder(startDir), startDir = pwd; end
    [f, p] = uigetfile({'*.mat', 'lrpt_sync output'}, ...
                       'Pick the symbol file', startDir);
    if isequal(f, 0), fprintf('Cancelled.\n'); return; end
    symFile = fullfile(p, f);
end
S = load(symFile);
fprintf('\n=== lrpt_viterbi_peek ===\nSymbols: %s\n', S.meta.fname);

NDEC   = 64;                 % bytes to decode after each ASM
NTAIL  = 4;                  % extra bytes decoded and thrown away (traceback)
MAXASM = 120;                % how many ASMs to process

% ------------------------------------- winning chip stream (from the hunt)
c  = S.c0;
bI = real(c) < 0;   bQ = imag(c) < 0;
bi = xor(bI(2:end), bI(1:end-1));           % NRZ-M diff decode per rail
bq = xor(bQ(2:end), bQ(1:end-1));
u  = false(2*numel(bi), 1);
u(1:2:end) = bi;  u(2:2:end) = bq;

% ------------------------------------------------ encoder + ASM template
G1 = [1 1 1 1 0 0 1];        % 171 octal
G2 = [1 0 1 1 0 1 1];        % 133 octal
asm = '1ACFFC1D';
bits = zeros(32,1);
for i = 1:8
    nib = hex2dec(asm(i));
    bits(4*i-3:4*i) = bitget(nib, 4:-1:1)';
end
reg = zeros(6,1);
chips = zeros(64,1);
for k = 1:32
    r7 = [bits(k); reg];
    chips(2*k-1) = mod(sum(r7 .* G1'), 2);
    chips(2*k)   = mod(sum(r7 .* G2'), 2);
    reg = r7(1:6);
end
tpl = 1 - 2*chips(13:64);
% encoder state entering the first data bit = the last 6 ASM bits:
s0 = reg(1)*32 + reg(2)*16 + reg(3)*8 + reg(4)*4 + reg(5)*2 + reg(6);

% ------------------------------------------------------------- find ASMs
upm = 1 - 2*double(u);
xc  = filter(flipud(tpl), 1, upm);
pk  = findPeaks(abs(xc), 46);               % strict: clean ASMs only
% stream polarity: peaks should correlate POSITIVE after NRZ-M decode
pol = sign(median(xc(pk)));
if pol < 0
    u = ~u;  fprintf('(stream polarity inverted - flipped)\n');
end
need = 2*8*(NDEC + NTAIL);
pk = pk(pk + need <= numel(u));
if numel(pk) > MAXASM, pk = pk(1:MAXASM); end
fprintf('Decoding %d bytes after each of %d clean ASMs (state-seeded Viterbi)\n', ...
        NDEC, numel(pk));

% classify each ASM by the gap to the previous one
gapPrev = [NaN; diff(pk)];
typ = repmat('?', numel(pk), 1);
typ(abs(gapPrev - 6784)  <= 3) = 'A';       % 424-byte slot follows an A gap
typ(abs(gapPrev - 18368) <= 3) = 'B';       % 1148-byte slot

% -------------------------------------------------- Viterbi tables (K=7)
nextS = zeros(64, 2);  outc = zeros(64, 2, 2);
for s = 0:63
    sv = bitget(s, 6:-1:1)';                % [b_{k-1} ... b_{k-6}]
    for b = 0:1
        r7 = [b; sv];
        outc(s+1, b+1, 1) = mod(sum(r7 .* G1'), 2);
        outc(s+1, b+1, 2) = mod(sum(r7 .* G2'), 2);
        nextS(s+1, b+1)   = b*32 + floor(s/2);
    end
end

% CCSDS randomizer sequence (a_{n+8} = a_{n+7}+a_{n+5}+a_{n+3}+a_n, seed 1s)
pnBits = ones(8*(NDEC+8), 1);
for n = 1:numel(pnBits)-8
    pnBits(n+8) = mod(pnBits(n+7) + pnBits(n+5) + pnBits(n+3) + pnBits(n), 2);
end

% --------------------------------------------------------- decode them all
nBitsDec = 8*(NDEC + NTAIL);
frames = struct('pos',{},'typ',{},'corr',{},'ber',{},'raw',{},'der',{});
for k = 1:numel(pk)
    rx = double(u(pk(k)+1 : pk(k)+2*nBitsDec));
    db = vdecode(rx, s0, nBitsDec, outc);
    db = db(1:8*NDEC);
    % re-encode to measure the local channel quality
    re = zeros(2*numel(db),1); rg = bitget(s0,6:-1:1)';
    for t = 1:numel(db)
        r7 = [db(t); rg];
        re(2*t-1) = mod(sum(r7 .* G1'),2);  re(2*t) = mod(sum(r7 .* G2'),2);
        rg = r7(1:6);
    end
    ber = mean(re ~= rx(1:numel(re)));
    der = xor(db, pnBits(1:numel(db)));
    frames(end+1) = struct('pos',pk(k),'typ',typ(k),'corr',abs(xc(pk(k))), ...
        'ber',ber,'raw',packBytes(db),'der',packBytes(der)); %#ok<AGROW>
end
fprintf('Mean re-encode chip BER at the decodes: %.3f\n\n', mean([frames.ber]));

% ------------------------------------------------------------- inspection
for T = 'AB'
    sel = find([frames.typ] == T);
    if isempty(sel), continue; end
    fprintf('=== frames in ''%c'' slots (%d found) ===\n', T, numel(sel));
    fprintf('First bytes (RAW    ): %s\n', hexRow(frames(sel(1)).raw(1:16)));
    fprintf('First bytes (DERAND ): %s\n', hexRow(frames(sel(1)).der(1:16)));
    fprintf('%-6s %-6s | %-28s | %s\n', 'idx', 'ber', ...
            'AOS hdr derand: ver scid vcid', 'counter');
    cnt = NaN(numel(sel),1);
    for ii = 1:min(numel(sel), 10)
        d = frames(sel(ii)).der;
        [ver, scid, vcid, ctr] = aosHdr(d);
        cnt(ii) = ctr;
        fprintf('%-6d %-6.3f | ver %d  scid %3d  vcid %2d      | %d\n', ...
                sel(ii), frames(sel(ii)).ber, ver, scid, vcid, ctr);
    end
    for ii = 11:numel(sel)
        d = frames(sel(ii)).der;  [~,~,~,cnt(ii)] = aosHdr(d);
    end
    dc = diff(cnt); dc = dc(~isnan(dc));
    if ~isempty(dc)
        fprintf('counter steps between consecutive decoded ''%c'' frames: ', T);
        fprintf('%d ', dc(1:min(12,numel(dc)))); fprintf('...\n');
    end
    % same header fields but WITHOUT derandomization, for comparison
    d = frames(sel(1)).raw;
    [ver, scid, vcid, ctr] = aosHdr(d);
    fprintf('(same header parsed RAW, no derand: ver %d scid %d vcid %d ctr %d)\n\n', ...
            ver, scid, vcid, ctr);
end

if nargout, out = frames; end
end

% -------------------------------------------------------------------------
function bitsOut = vdecode(rx, s0, nBits, outc)
% hard-decision Viterbi, K=7, known start state; rx = 2*nBits chips (0/1)
PM = inf(64,1);  PM(s0+1) = 0;
prev = zeros(64, nBits, 'uint8');
ns   = (0:63)';
bvec = floor(ns/32);                        % input bit that leads INTO ns
sA   = 2*mod(ns,32) + 1;                    % the two predecessor states
sB   = sA + 1;
liA  = sA + 64*bvec;                        % linear index into 64x2 arrays
liB  = sB + 64*bvec;
o1 = squeeze(outc(:,:,1));  o2 = squeeze(outc(:,:,2));
for t = 1:nBits
    cost = double(o1 ~= rx(2*t-1)) + double(o2 ~= rx(2*t));
    cand = PM + cost;                       % 64x2
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

function s = hexRow(by)
s = sprintf('%02X ', by);
end

function [ver, scid, vcid, ctr] = aosHdr(by)
% CCSDS AOS transfer-frame primary header: 2 bits version, 8 bits SCID,
% 6 bits VCID, then a 24-bit virtual-channel frame counter.
ver  = floor(by(1)/64);
scid = mod(by(1),64)*4 + floor(by(2)/64);
vcid = mod(by(2), 64);
ctr  = by(3)*65536 + by(4)*256 + by(5);
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
