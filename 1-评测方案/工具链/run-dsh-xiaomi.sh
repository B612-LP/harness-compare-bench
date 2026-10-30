#!/bin/bash
# 2026-10-16 小米批次（r1016x-*）：DSH 0.2.0-rc.2 × mimo-v2.6-flash × 两用例
export PATH="$PATH:/root/.local/bin"
BENCH="${BENCH:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
TOOLS="$BENCH/1-评测方案/工具链"
CASES="${CASES:-$BENCH/2-用例}"
JOBS="${JOBS:-$BENCH/3-表现现场}"
export PYTHONPATH="$TOOLS"
source /root/.codex/xiaomi.env

run() {
  echo "=== $1 (dsh x $2) ==="
  harbor run -p "$CASES/$2" \
    -a dsh_agent:Dsh -m mimo-v2.6-flash \
    --ak version=0.2.0-rc.2 --ak config="$TOOLS/cordis-xiaomi.patch.yml" \
    --ae XIAOMI_API_KEY="$XIAOMI_API_KEY" \
    --ae npm_config_registry=https://registry.npmmirror.com \
    --extra-docker-compose "$TOOLS/compose-proxy-overlay-v2.yml" \
    --timeout-multiplier 3 --yes \
    --job-name "$1" --jobs-dir "$JOBS"
  echo "--- reward: $(cat "$JOBS/$1"/*/verifier/reward.txt 2>/dev/null | tr '\n' ' ')"
}

run r1016x-intsum-dsh  int-sum-sort
run r1016x-wordfreq-dsh word-freq-report
echo DSH-XIAOMI-DONE
