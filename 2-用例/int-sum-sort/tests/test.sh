#!/bin/bash
# Deterministic offline verifier — no network, no third-party installs
# (lesson from jobs/codex-glm-demo: a verifier that downloads tools at
# test time can fail before any test runs and silently score 0).
#
# Checks (see rubric/README.md for the scoring rubric):
#   1. output_exists  — /app/output.txt was created
#   2. sum_line       — line 1 is the sum of input integers
#   3. count_line     — line 2 is the count of input integers
#   4. sorted_block   — remaining non-empty lines are the integers sorted asc
# Reward: binary, 1 only when all four checks pass.

mkdir -p /logs/verifier

reward=0

if [ -f /app/output.txt ]; then
  echo "check output_exists: PASS"

  expected_sum=$(awk '{ s += $1 } END { print s }' /app/input.txt)
  expected_count=$(awk 'END { print NR }' /app/input.txt)
  expected_sorted=$(sort -n /app/input.txt | tr '\n' ' ')

  actual_sum=$(sed -n '1p' /app/output.txt)
  actual_count=$(sed -n '2p' /app/output.txt)
  actual_sorted=$(sed -n '3,$p' /app/output.txt | sed '/^$/d' | tr '\n' ' ')

  ok=1
  if [ "$actual_sum" = "$expected_sum" ]; then
    echo "check sum_line: PASS"
  else
    echo "check sum_line: FAIL (got '$actual_sum', want '$expected_sum')"
    ok=0
  fi
  if [ "$actual_count" = "$expected_count" ]; then
    echo "check count_line: PASS"
  else
    echo "check count_line: FAIL (got '$actual_count', want '$expected_count')"
    ok=0
  fi
  if [ "$actual_sorted" = "$expected_sorted" ]; then
    echo "check sorted_block: PASS"
  else
    echo "check sorted_block: FAIL (got '$actual_sorted', want '$expected_sorted')"
    ok=0
  fi

  reward=$ok
else
  echo "check output_exists: FAIL (/app/output.txt not found)"
fi

echo "$reward" > /logs/verifier/reward.txt
echo "reward=$reward"
