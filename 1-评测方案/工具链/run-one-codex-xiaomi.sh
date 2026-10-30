#!/bin/bash
# 单跑 Codex × mimo-v2.6-flash（重跑用）。用法：run-one-codex-xiaomi.sh <job-name> <case-dir>
export PATH="$PATH:/root/.local/bin"
BENCH="${BENCH:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
TOOLS="$BENCH/1-评测方案/工具链"
CASES="${CASES:-$BENCH/2-用例}"
JOBS="${JOBS:-$BENCH/3-表现现场}"
source /root/.codex/xiaomi.env

echo "=== $1 (codex x $2) ==="
harbor run -p "$CASES/$2" \
  -a codex -m mimo-v2.6-flash \
  --ak version=0.162.1 --ak config="$TOOLS/config-xiaomi.toml" \
  --ak disable_web_search=true \
  --ae XIAOMI_API_KEY="$XIAOMI_API_KEY" --ae OPENAI_API_KEY="$XIAOMI_API_KEY" \
  --ae npm_config_registry=https://registry.npmmirror.com \
  --extra-docker-compose "$TOOLS/compose-proxy-overlay-v2.yml" \
  --timeout-multiplier 3 --yes \
  --job-name "$1" --jobs-dir "$JOBS"
echo "--- reward: $(cat "$JOBS/$1"/*/verifier/reward.txt 2>/dev/null | tr '\n' ' ')"
