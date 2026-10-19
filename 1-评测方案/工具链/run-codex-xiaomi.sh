#!/bin/bash
# 2026-10-16 小米批次（r1016x-*）：Codex 0.162.1 × mimo-v2.6-flash × 两用例
export PATH="$PATH:/root/.local/bin"
BENCH=/mnt/c/Users/Administrator/Desktop/harness-compare-bench-old
source /root/.codex/xiaomi.env

run() {
  echo "=== $1 (codex x $2) ==="
  harbor run -p "$BENCH/cases/$2" \
    -a codex -m mimo-v2.6-flash \
    --ak version=0.162.1 --ak config="$BENCH/infra/config-xiaomi.toml" \
    --ak disable_web_search=true \
    --ae XIAOMI_API_KEY="$XIAOMI_API_KEY" --ae OPENAI_API_KEY="$XIAOMI_API_KEY" \
    --ae npm_config_registry=https://registry.npmmirror.com \
    --extra-docker-compose "$BENCH/infra/compose-proxy-overlay-v2.yml" \
    --timeout-multiplier 3 --yes \
    --job-name "$1" --jobs-dir "$BENCH/jobs"
  echo "--- reward: $(cat "$BENCH/jobs/$1"/*/verifier/reward.txt 2>/dev/null | tr '\n' ' ')"
}

run r1016x-intsum-codex  int-sum-sort
run r1016x-wordfreq-codex word-freq-report
echo CODEX-XIAOMI-DONE
