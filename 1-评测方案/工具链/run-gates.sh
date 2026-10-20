#!/bin/bash
# 2026-10-16 批次：两个自建用例的 oracle-gating 四连跑（nop=0 / oracle=1）
export PATH="$PATH:/root/.local/bin"
BENCH="${BENCH:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
TOOLS="$BENCH/1-评测方案/工具链"
CASES="${CASES:-$BENCH/2-用例}"
JOBS="${JOBS:-$BENCH/3-表现现场}"

run() {
  echo "=== $1 ($2 x $3) ==="
  harbor run -p "$CASES/$3" -a "$2" --job-name "$1" \
    --jobs-dir "$JOBS" --yes
  echo "--- reward: $(cat "$JOBS/$1"/*/verifier/reward.txt 2>/dev/null | tr '\n' ' ')"
}

run r1016-intsum-nop    nop    int-sum-sort
run r1016-intsum-oracle oracle int-sum-sort
run r1016-wordfreq-nop    nop    word-freq-report
run r1016-wordfreq-oracle oracle word-freq-report
echo "ALL GATES DONE"
