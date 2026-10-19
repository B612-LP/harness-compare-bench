#!/bin/bash
# Gold solution for word-freq-report (spec: instruction.md).
# Same tokenization rules as tests/test.sh — kept as two identical copies on
# purpose (verifier must not depend on the solution at test time).
set -euo pipefail
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

awk -v counts_file="$tmp/counts" -v summary_file="$tmp/summary" '
function strip(t,   c) {
  while (length(t) > 0) {
    c = substr(t, 1, 1)
    if (index(PUNCT, c) > 0) t = substr(t, 2); else break
  }
  while (length(t) > 0) {
    c = substr(t, length(t), 1)
    if (index(PUNCT, c) > 0) t = substr(t, 1, length(t) - 1); else break
  }
  return t
}
BEGIN { PUNCT = ".,;:!?\047\"()-" }
{
  for (i = 1; i <= NF; i++) {
    t = strip(tolower($i))
    if (t == "") continue
    if (t ~ /[0-9]/) continue
    cnt[t]++
    total++
  }
}
END {
  for (w in cnt) { dist++; printf "%d %s\n", cnt[w], w > counts_file }
  printf "%d\n%d\n", total, dist > summary_file
}
' /app/corpus.txt

total=$(sed -n '1p' "$tmp/summary")
dist=$(sed -n '2p' "$tmp/summary")
top5=$(LC_ALL=C sort -k1,1nr -k2,2 "$tmp/counts" | head -5 | awk '{ print $2 " " $1 }')

{
  echo "$total"
  echo "$dist"
  echo "$top5"
} > /app/report.txt
