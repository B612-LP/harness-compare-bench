#!/bin/bash
# 2026-10-16 批次：Codex 0.162.1 × glm-5.3-flash 两份完整测试
# 修正后模板：v2 overlay（智谱走代理）+ disable_web_search + 版本锁定
export PATH="$PATH:/root/.local/bin"
BENCH=/mnt/c/Users/Administrator/Desktop/harness-compare-bench-old
source /root/.codex/zai.env

run() {
  echo "=== $1 (codex x $2) ==="
  harbor run -p "$BENCH/cases/$2" \
    -a codex -m glm-5.3-flash \
    --ak version=0.162.1 --ak config=/root/.codex/config.toml \
    --ak disable_web_search=true \
    --ae ZAI_API_KEY="$ZAI_API_KEY" --ae OPENAI_API_KEY="$ZAI_API_KEY" \
    --extra-docker-compose "$BENCH/infra/compose-proxy-overlay-v2.yml" \
    --allow-agent-host open.bigmodel.cn --allow-agent-host 172.21.240.1 \
    --timeout-multiplier 3 --yes \
    --job-name "$1" --jobs-dir "$BENCH/jobs"
  echo "--- reward: $(cat "$BENCH/jobs/$1"/*/verifier/reward.txt 2>/dev/null | tr '\n' ' ')"
}

run r1016-intsum-codex  int-sum-sort
run r1016-wordfreq-codex word-freq-report
echo "CODEX RUNS DONE"
