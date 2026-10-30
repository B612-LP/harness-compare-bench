#!/bin/bash
# 跑一场桌面实测：./tools/run.sh <workbuddy|yuanbao|doubao> <case> [额外参数]
set -u
cd "$(dirname "$0")/.." || exit 1
exec python3 tools/desk.py run "$@"
