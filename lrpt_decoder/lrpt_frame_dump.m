function out = lrpt_frame_dump(symFile)
%LRPT_FRAME_DUMP  Aligned hex dumps of clean frames - read the format by eye.
%
%   The frame layer is proven (424/+1 and 1148/+2, ASM + 6-byte header,
%   per-frame randomizer restart) but the payload is NOT standard M-PDU.
%   So: collect clean frames from the dense region, split by size class,
%   and show
%     1. aligned hex of the first 48 bytes (de-randomized) - constant
%        fields, counters and structure become visible immediately
%     2. a per-offset constancy map over the first 96 bytes
%     3. the LAST 12 bytes of each frame (trailer / checksum / padding?)
%     4. crude randomness stats for the payload body
%
%   USAGE:  lrpt_frame_dump          (picker for the *_sym.mat)
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
fprintf('\n=== lrpt_frame_dump ===\nSymbols: %s\n', S.meta.fname);

NBYTES = 16000;
HOPS   = [ 424 1;  1148 2;  848 2;  1572 3;  2296 4;  1996 4;  2720 5];

% ---------------- chain identical to lrpt_walk --------------------------
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

pnB = ones(8*1300, 1);
for n = 1:numel(pnB)-8
    pnB(n+8) = mod(pnB(n+7) + pnB(n+5) + pnB(n+3) + pnB(n), 2);
end

pkOK = pk(pk + 2*8*(NBYTES+8) <= numel(u));
dens = zeros(size(pkOK));
for i = 1:numel(pkOK)
    dens(i) = sum(abs(pk - pkOK(i) - 8*NBYTES) <= 8*NBYTES);
end
[~, ib] = max(dens);
anchor = pkOK(ib);
fprintf('Anchor at chip %d (%.0f s in), %d detections in window\n', ...
        anchor, anchor/144000, dens(ib));
rx = double(u(anchor+1 : anchor+2*8*(NBYTES+8)));
db = vdecode(rx, s0, 8*(NBYTES+8), outc);
db = db(1:8*NBYTES);

% walk & collect frames (derandomized payload bytes, per frame)
frames = struct('off',{},'size',{},'ctr',{},'der',{});
hs  = 0;
hdr = readHdr(db, hs, pnB);
while true
    bestScore = -1; best = [];
    for hI = 1:size(HOPS,1)
        L = HOPS(hI,1);  st = HOPS(hI,2);
        nh = hs + L;
        if nh + 8 > NBYTES, continue; end
        h2 = readHdr(db, nh, pnB);
        mBits = db(8*(nh-4)+1 : 8*nh);
        aham  = sum(mBits ~= asmBits);
        sc = 2*(aham <= 6) + (h2.ver == 1) + (h2.scid == 0) ...
           + 2*(h2.vcid == 5) + 3*(h2.ctr == hdr.ctr + st) - 0.01*st;
        if sc > bestScore
            bestScore = sc; best = struct('nh',nh,'L',L,'h',h2);
        end
    end
    if isempty(best), break; end
    if ismember(best.L, [424 1148]) && bestScore >= 6
        n = best.L - 4;                       % header+payload bytes
        bits = xor(db(8*hs+1 : 8*(hs+n)), pnB(1:8*n));
        frames(end+1) = struct('off',hs,'size',best.L,'ctr',hdr.ctr, ...
                               'der',packBytes(bits)); %#ok<AGROW>
    end
    if bestScore < 4, break; end
    hs = best.nh;  hdr = best.h;
end
fprintf('Collected %d clean frames\n', numel(frames));

% ------------------------------------------------------------- the dumps
for SZ = [424 1148]
    sel = frames([frames.size] == SZ);
    if isempty(sel), continue; end
    fprintf('\n===== %d-byte frames (%d clean) =====\n', SZ, numel(sel));

    fprintf('-- first 48 bytes (derandomized), aligned --\n');
    for i = 1:min(8, numel(sel))
        fprintf('ctr %-9d: %s\n', sel(i).ctr, sprintf('%02X ', sel(i).der(1:48)));
    end

    % constancy map over the first 96 bytes
    nB = min(96, SZ-4);
    M = zeros(numel(sel), nB);
    for i = 1:numel(sel), M(i,:) = sel(i).der(1:nB)'; end
    agree = zeros(1,nB); modev = zeros(1,nB);
    for j = 1:nB
        [uv,~,ic] = unique(M(:,j));
        cc = accumarray(ic,1);
        [mx,im] = max(cc);
        agree(j) = mx/numel(sel);  modev(j) = uv(im);
    end
    fprintf('-- constant offsets (>=75%% agreement) in bytes 0..%d --\n', nB-1);
    fi = find(agree >= 0.75);
    if isempty(fi)
        fprintf('(none beyond the header)\n');
    else
        runS = fi([true, diff(fi) > 1]);  runE = fi([diff(fi) > 1, true]);
        for r = 1:numel(runS)
            sp = runS(r):runE(r);
            fprintf('  offs %2d..%2d : %s\n', sp(1)-1, sp(end)-1, ...
                    sprintf('%02X ', modev(sp)));
        end
    end

    fprintf('-- last 12 bytes of each frame --\n');
    for i = 1:min(6, numel(sel))
        fprintf('ctr %-9d: %s\n', sel(i).ctr, ...
                sprintf('%02X ', sel(i).der(end-11:end)));
    end

    % payload randomness: distinct byte values in the middle of the body
    mid = round((SZ-4)/2);
    vals = [];
    for i = 1:numel(sel), vals = [vals; sel(i).der(mid:mid+15)]; end %#ok<AGROW>
    fprintf('-- body middle: %d distinct byte values in %d samples ',...
            numel(unique(vals)), numel(vals));
    fprintf('(random ~%d; constant/structured = fewer) --\n', ...
            round(256*(1-exp(-numel(vals)/256))));
end

if nargout, out = frames; end
end

% ------------------------------------------------------------------------
function h = readHdr(db, off, pnB)
bits = xor(db(8*off+1 : 8*off+48), pnB(1:48));
by = packBytes(bits);
h.ver  = floor(by(1)/64);
h.scid = mod(by(1),64)*4 + floor(by(2)/64);
h.vcid = mod(by(2), 64);
h.ctr  = by(3)*65536 + by(4)*256 + by(5);
h.sig  = by(6);
end

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
