function cut_segment(fname, tSeg)
%CUT_SEGMENT  Cut a time segment out of a baseband recording, for sharing.
%
%   cut_segment                    % file picker, default t = [230 360] s
%   cut_segment(fname, [240 330])  % explicit segment
%
%   Writes <name>_cut<t1>-<t2>s.<ext> next to the original, same format.
%   Chunked copy - never loads the whole file into memory.

if nargin < 1 || isempty(fname)
    startDir = 'C:\Users\grigo\OneDrive\Desktop\SatDumbInput';
    if ~isfolder(startDir), startDir = pwd; end
    [f, p] = uigetfile({'*.cs8;*.cs16;*.cf32', 'Baseband recordings'}, ...
                       'Pick the recording to cut', startDir);
    if isequal(f, 0), fprintf('Cancelled.\n'); return; end
    fname = fullfile(p, f);
end
if nargin < 2 || isempty(tSeg), tSeg = [230 360]; end

tokRate = regexp(fname, '(\d+)SPS', 'tokens', 'once');
if isempty(tokRate), error('Sample rate not in filename - pass a SatDump-named file.'); end
fs = str2double(tokRate{1});

[fp, base, ext] = fileparts(fname);
switch lower(ext)
    case '.cs8',           bytesPerSample = 2;
    case {'.cs16','.s16'}, bytesPerSample = 4;
    case {'.cf32','.f32'}, bytesPerSample = 8;
    otherwise, error('Unknown format %s', ext);
end

info = dir(fname);
tSeg(2) = min(tSeg(2), info.bytes/bytesPerSample/fs);
outName = fullfile(fp, sprintf('%s_cut%d-%ds%s', base, round(tSeg), ext));

fin  = fopen(fname, 'r');
fout = fopen(outName, 'w');
cleanup = onCleanup(@() cellfun(@fclose, {fin, fout}));

fseek(fin, round(tSeg(1)*fs)*bytesPerSample, 'bof');
bytesLeft = round(diff(tSeg)*fs)*bytesPerSample;
chunk = 64*2^20;                                  % 64 MB at a time
fprintf('Cutting %.0f..%.0f s -> %s\n', tSeg, outName);
while bytesLeft > 0
    buf = fread(fin, min(chunk, bytesLeft), 'uint8=>uint8');
    if isempty(buf), break; end
    fwrite(fout, buf);
    bytesLeft = bytesLeft - numel(buf);
    fprintf('.');
end
d = dir(outName);
fprintf(' done: %.0f MB\n', d.bytes/2^20);
end
