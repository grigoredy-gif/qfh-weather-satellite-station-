function out = lrpt_walk(symFile)
%LRPT_WALK  Walk the (now fully mapped) frame chain and census the M-PDUs.
%
%   Frame map, proven by lrpt_hdr_scan in the clean mid-pass region:
%     - every frame: [ASM][6-byte AOS hdr: ver1/scid0/vcid5/ctr/sig0][payload]
%     - two physical sizes: 424 bytes (counter +1) and 1148 bytes (+2)
%     - randomizer restarts at every frame, no hidden/markerless frames
%
%   This walker chains header-to-header with the size/step rule, tolerates
%   missed boundaries (multi-hop candidates with matching counter steps),
%   and reads each frame's M-PDU: first-header pointer + CCSDS space-packet
%   headers (APID / length). APIDs 64..69 = MSU-MR image channels = GO for
%   the CADU repack; anything else tells us what this transmission carries.
%
%   USAGE:  lrpt_walk                (picker for the *_sym.mat)
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
fprintf('\n=== lrpt_walk ===\nSymbols: %s\n', S.meta.fname);

NBYTES = 16000;              % bytes decoded per anchor
NANCH  = 2;                  % anchors (dense regions, far apart)
% candidate hops: (bytes to next header, expected counter step)
HOPS   = [ 424 1;  1148 2;  848 2;  1572 3;  2296 4;  1996 4;  2720 5];

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

pnB = ones(8*1300, 1);
for n = 1:numel(pnB)-8
    pnB(n+8) = mod(pnB(n+7) + pnB(n+5) + pnB(n+3) + pnB(n), 2);
end

% anchors from the DENSEST detection regions (mid-pass), spaced apart
pkOK = pk(pk + 2*8*(NBYTES+8) <= numel(u));
dens = zeros(size(pkOK));
for i = 1:numel(pkOK)
    dens(i) = sum(abs(pk - pkOK(i) - 8*NBYTES) <= 8*NBYTES);
end
anchors = [];
d2 = dens;
for a = 1:NANCH
    [dv, ib] = max(d2);
    if dv < 3, break; end
    anchors(end+1) = pkOK(ib); %#ok<AGROW>
    d2(abs(pkOK - pkOK(ib)) < 32*NBYTES) = -1;   % keep anchors apart
end

allF = [];
apidCount = containers.Map('KeyType','double','ValueType','double');
for a = 1:numel(anchors)
    fprintf('\n--- anchor %d/%d (chip %d, %.0f s in): decoding %d bytes ---\n', ...
            a, numel(anchors), anchors(a), anchors(a)/144000, NBYTES);
    rx = double(u(anchors(a)+1 : anchors(a)+2*8*(NBYTES+8)));
    db = vdecode(rx, s0, 8*(NBYTES+8), outc);
    db = db(1:8*NBYTES);

    hs  = 0;
    hdr = readHdr(db, hs, pnB);
    fprintf('%-7s %-6s %-9s %-4s %-6s %-6s %-7s %s\n', ...
            'offset','size','counter','sig','mpduP','apid','plen','note');
    nWalk = 0;
    while nWalk < 60
        mp = readMpdu(db, hs, pnB);
        apidStr = '-'; plenStr = '-';
        if mp.ok
            apidStr = sprintf('%d', mp.apid);
            plenStr = sprintf('%d', mp.plen);
            if isKey(apidCount, mp.apid)
                apidCount(mp.apid) = apidCount(mp.apid) + 1;
            else
                apidCount(mp.apid) = 1;
            end
        end

        bestScore = -1; best = [];
        for hI = 1:size(HOPS,1)
            L = HOPS(hI,1);  st = HOPS(hI,2);
            nh = hs + L;
            if nh + 8 > NBYTES, continue; end
            h2 = readHdr(db, nh, pnB);
            mBits = db(8*(nh-4)+1 : 8*nh);
            aham  = sum(mBits ~= asmBits);
            sc = 2*(aham <= 6) + (h2.ver == 1) + (h2.scid == 0) ...
               + 2*(h2.vcid == 5) + 3*(h2.ctr == hdr.ctr + st) ...
               - 0.01*st;                    % prefer the shortest valid hop
            if sc > bestScore
                bestScore = sc;
                best = struct('nh',nh,'L',L,'st',st,'h',h2);
            end
        end
        note = '';
        if isempty(best), break; end
        if bestScore < 6, note = 'WEAK'; end
        fprintf('%-7d %-6d %-9d %-4d %-6s %-6s %-7s %s\n', hs, best.L, ...
                hdr.ctr, hdr.sig, mpS(mp), apidStr, plenStr, note);
        allF = [allF; struct('anchor',a,'off',hs,'size',best.L, ...
                 'ctr',hdr.ctr,'mpdu',mp)]; %#ok<AGROW>
        if bestScore < 4, break; end         % lost the chain
        hs  = best.nh;
        hdr = best.h;
        nWalk = nWalk + 1;
    end
end

% ------------------------------------------------------------- the census
fprintf('\n=== APID census across all walked frames ===\n');
if isempty(keys(apidCount))
    fprintf('no parseable packet headers found.\n');
else
    ks = cell2mat(keys(apidCount));
    vs = cell2mat(values(apidCount));
    [vs, io] = sort(vs, 'descend');  ks = ks(io);
    for i = 1:numel(ks)
        note = '';
        if ks(i) >= 64 && ks(i) <= 69, note = '<-- MSU-MR IMAGE CHANNEL'; end
        if ks(i) == 70, note = '(telemetry)'; end
        if ks(i) == 2047, note = '(idle filler)'; end
        fprintf('  APID %4d : %3d packets  %s\n', ks(i), vs(i), note);
    end
    if any(ks >= 64 & ks <= 69)
        fprintf('\nVERDICT: image-channel packets ARE present -> GO for the\n');
        fprintf('CADU repack and a SatDump render.\n');
    else
        fprintf('\nVERDICT: no MSU-MR APIDs in this sample - the payload is\n');
        fprintf('something else; look at the pointers/lengths above.\n');
    end
end

if nargout, out = allF; end
end

% -------------------------------------------------------------------------
function h = readHdr(db, off, pnB)
bits = xor(db(8*off+1 : 8*off+48), pnB(1:48));
by = packBytes(bits);
h.ver  = floor(by(1)/64);
h.scid = mod(by(1),64)*4 + floor(by(2)/64);
h.vcid = mod(by(2), 64);
h.ctr  = by(3)*65536 + by(4)*256 + by(5);
h.sig  = by(6);
end

function mp = readMpdu(db, off, pnB)
mp.ok = false; mp.ptr = NaN; mp.apid = NaN; mp.plen = NaN;
nAvail = floor(numel(db)/8) - off - 20;
if nAvail < 16, return; end
n = min(nAvail, 1160);
bits = xor(db(8*off+1 : 8*(off+n)), pnB(1:8*n));
by = packBytes(bits);
mp.ptr = mod(by(7), 8)*256 + by(8);
if mp.ptr > 2000, return; end
ph = 8 + mp.ptr;
if ph + 6 > n, return; end
b = by(ph+1 : ph+6);
mp.apid = mod(b(1), 8)*256 + b(2);
mp.plen = b(5)*256 + b(6) + 1;
mp.ok = true;
end

function s = mpS(mp)
if isnan(mp.ptr), s = '-'; else, s = sprintf('%d', mp.ptr); end
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
