#!/bin/bash
# 2026-10-16 批次：DSH 0.2.0-rc.2 × glm-5.3-flash 两份完整测试
# 用法：run-dsh.sh <job-name> <case-dir>
export PATH="$PATH:/root/.local/bin"
BENCH="${BENCH:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
TOOLS="$BENCH/1-评测方案/工具链"
CASES="${CASES:-$BENCH/2-用例}"
JOBS="${JOBS:-$BENCH/3-表现现场}"
export PYTHONPATH="$TOOLS"
source /root/.codex/zai.env

echo "=== $1 (dsh x $2) ==="
harbor run -p "$CASES/$2" \
  -a dsh_agent:Dsh -m glm-5.3-flash \
  --ak version=0.2.0-rc.2 --ak config="$TOOLS/cordis.patch.yml" \
  --ae ZAI_API_KEY="$ZAI_API_KEY" \
  --extra-docker-compose "$TOOLS/compose-proxy-overlay-v2.yml" \
  --timeout-multiplier 3 --yes \
  --job-name "$1" --jobs-dir "$JOBS"
echo "--- reward: $(cat "$JOBS/$1"/*/verifier/reward.txt 2>/dev/null | tr '\n' ' ')"
