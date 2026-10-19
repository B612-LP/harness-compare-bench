#!/bin/bash
# 2026-10-16 批次：两个自建用例的 oracle-gating 四连跑（nop=0 / oracle=1）
export PATH="$PATH:/root/.local/bin"
BENCH=/mnt/c/Users/Administrator/Desktop/harness-compare-bench-old

run() {
  echo "=== $1 ($2 x $3) ==="
  harbor run -p "$BENCH/cases/$3" -a "$2" --job-name "$1" \
    --jobs-dir "$BENCH/jobs" --yes
  echo "--- reward: $(cat "$BENCH/jobs/$1"/*/verifier/reward.txt 2>/dev/null | tr '\n' ' ')"
}

run r1016-intsum-nop    nop    int-sum-sort
run r1016-intsum-oracle oracle int-sum-sort
run r1016-wordfreq-nop    nop    word-freq-report
run r1016-wordfreq-oracle oracle word-freq-report
echo "ALL GATES DONE"
