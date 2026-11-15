#!/usr/bin/env python3
"""Synthetic illustration, not the historical fixture or a product execution."""
import json

def require(ok, msg):
    if not ok:
        raise ValueError(msg)

# Newly invented content, not the historical checksums or product inputs.
# 420 × 85-byte lines plus a 33-byte head and 34-byte tail = 35,767 bytes.
lines = [b'H' + b'a'*31 + b'\n']
for n in range(420):
    line = f'noise-{n:04d}:{n:064x}'.encode('ascii') + b'x'*9 + b'\n'
    require(len(line) == 85, 'noise line length')
    lines.append(line)
lines.append(b'T' + b'b'*32 + b'\n')
require(len(lines)==422, 'line count')
source = b''.join(lines)
require(len(source)==35767, 'source bytes')
target = lines[211]
require(target.startswith(b'noise-0210:'), 'target line')
changed = lines.copy()
changed[211], changed[301] = changed[301], changed[211]
permuted = b''.join(changed)
require(len(source) == len(permuted) and source[:864] == permuted[:864] and source[-864:] == permuted[-864:], 'projected bytes differ')
require(changed[301] == target and changed[211] != target, 'target permutation')
# Values are a minimal transcription of the six historical first read calls.
# The bytes above are synthetic and cannot validate that transcription.
windows = [(208,8), (208,12), (208,8), (212,1), (205,20), (190,40)]
result = []
for i,(offset,limit) in enumerate(windows,1):
    old = lines[offset-1:offset-1+limit]
    new = changed[offset-1:offset-1+limit]
    result.append({'slot':i,'offset_1based':offset,'limit':limit,
                   'old_target_in_slice':target in old,'permuted_target_in_slice':target in new})
require(all(x['old_target_in_slice'] and not x['permuted_target_in_slice'] for x in result), 'unexpected window coverage')
print(json.dumps({'synthetic_demo':True,'byte_count':len(source),'line_count':len(lines),
                  'compared_prefix_and_suffix_bytes':864,'old_target_line':212,'permuted_target_line':302,
                  'windows':result},indent=2))
