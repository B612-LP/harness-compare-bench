#!/bin/bash
# Deterministic offline verifier for word-freq-report — no network, no
# third-party installs (lesson from jobs/codex-glm-demo: a verifier that
# downloads tools at test time can fail before any test runs and score 0).
#
# Expected values are computed at test time from /app/corpus.txt with the
# SAME tokenization rules as solution/solve.sh (kept as two identical copies
# on purpose: the verifier must not depend on the solution at test time).
#
# Checks (see rubric for the scoring rubric):
#   1. output_exists    — /app/report.txt was created
#   2. total_line       — line 1 is the total word-token count
#   3. distinct_line    — line 2 is the distinct word count
#   4. top5_block       — lines 3-7 are the top-5 words (count desc, ASCII tie-break)
#   5. trailing_newline — file ends with exactly one newline after line 7
# Reward: binary, 1 only when all five checks pass.

mkdir -p /logs/verifier

reward=0

if [ ! -f /app/report.txt ]; then
  echo "check output_exists: FAIL (/app/report.txt not found)"
  echo "$reward" > /logs/verifier/reward.txt
  echo "reward=$reward"
  exit 0
fi
echo "check output_exists: PASS"

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

exp_total=$(sed -n '1p' "$tmp/summary")
exp_distinct=$(sed -n '2p' "$tmp/summary")
exp_top5=$(LC_ALL=C sort -k1,1nr -k2,2 "$tmp/counts" | head -5 | awk '{ print $2 " " $1 }')

ok=1

actual_total=$(sed -n '1p' /app/report.txt)
if [ "$actual_total" = "$exp_total" ]; then
  echo "check total_line: PASS"
else
  echo "check total_line: FAIL (got '$actual_total', want '$exp_total')"
  ok=0
fi

actual_distinct=$(sed -n '2p' /app/report.txt)
if [ "$actual_distinct" = "$exp_distinct" ]; then
  echo "check distinct_line: PASS"
else
  echo "check distinct_line: FAIL (got '$actual_distinct', want '$exp_distinct')"
  ok=0
fi

actual_top5=$(sed -n '3,7p' /app/report.txt)
if [ "$actual_top5" = "$exp_top5" ]; then
  echo "check top5_block: PASS"
else
  echo "check top5_block: FAIL"
  echo "--- got ---"
  echo "$actual_top5"
  echo "--- want (count desc, ASCII tie-break) ---"
  echo "$exp_top5"
  ok=0
fi

last_byte=$(tail -c 1 /app/report.txt | od -An -t x1 | tr -d ' \n')
n_lines=$(wc -l < /app/report.txt | tr -d ' ')
if [ "$last_byte" = "0a" ] && [ "$n_lines" = "7" ]; then
  echo "check trailing_newline: PASS"
else
  echo "check trailing_newline: FAIL (last_byte=$last_byte n_lines=$n_lines, want 0a and 7)"
  ok=0
fi

reward=$ok
echo "$reward" > /logs/verifier/reward.txt
echo "reward=$reward"
