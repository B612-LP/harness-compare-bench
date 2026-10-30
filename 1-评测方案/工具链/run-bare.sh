#!/bin/bash
# 2026-10-16 小米批次（r1016x-*）：C 组裸模型基线 × 两用例
# 零脚手架：指令原样进 API、回答原文落盘、同一评分器判卷
export PATH="$PATH:/root/.local/bin"
BENCH="${BENCH:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
TOOLS="$BENCH/1-评测方案/工具链"
CASES="${CASES:-$BENCH/2-用例}"
JOBS="${JOBS:-$BENCH/3-表现现场}"
export PYTHONPATH="$TOOLS"
source /root/.codex/xiaomi.env

run() {
  echo "=== $1 (bare-model x $2 -> $3) ==="
  harbor run -p "$CASES/$2" \
    -a bare_model:BareModel -m mimo-v2.6-flash \
    --ak output_path="$3" \
    --ae XIAOMI_API_KEY="$XIAOMI_API_KEY" \
    --extra-docker-compose "$TOOLS/compose-proxy-overlay-v2.yml" \
    --timeout-multiplier 3 --yes \
    --job-name "$1" --jobs-dir "$JOBS"
  echo "--- reward: $(cat "$JOBS/$1"/*/verifier/reward.txt 2>/dev/null | tr '\n' ' ')"
}

run r1016x-intsum-bare  int-sum-sort    /app/output.txt
run r1016x-wordfreq-bare word-freq-report /app/report.txt
echo BARE-RUNS-DONE
