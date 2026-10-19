#!/bin/bash
# 2026-10-16 批次：DSH 0.2.0-rc.2 × glm-5.3-flash 两份完整测试
# 用法：run-dsh.sh <job-name> <case-dir>
export PATH="$PATH:/root/.local/bin"
BENCH=/mnt/c/Users/Administrator/Desktop/harness-compare-bench
export PYTHONPATH="$BENCH/infra"
source /root/.codex/zai.env

echo "=== $1 (dsh x $2) ==="
harbor run -p "$BENCH/cases/$2" \
  -a dsh_agent:Dsh -m glm-5.3-flash \
  --ak version=0.2.0-rc.2 --ak config="$BENCH/infra/dsh-proto/cordis.patch.yml" \
  --ae ZAI_API_KEY="$ZAI_API_KEY" \
  --extra-docker-compose "$BENCH/infra/compose-proxy-overlay-v2.yml" \
  --timeout-multiplier 3 --yes \
  --job-name "$1" --jobs-dir "$BENCH/jobs"
echo "--- reward: $(cat "$BENCH/jobs/$1"/*/verifier/reward.txt 2>/dev/null | tr '\n' ' ')"
