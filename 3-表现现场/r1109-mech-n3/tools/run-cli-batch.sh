#!/bin/bash
# r1109-mech-n3 CLI 批：dsh 臂→codex 臂串行（同 API 键，避免并发 429）
L=<launch 工作目录，本仓公开档为 archive://launch-r1109/；脚本原文随私档收据保留，此处为去路径披露版>
cd "$L"
CASES="bird-ca-schools-15 dabstep-payments-10 exercism-py-6 lcb-recent-hard-4 tb-cargo-plan"
echo "=== CLI batch start $(date '+%F %T %z') ==="
for arm in dsh codex; do
  for case in $CASES; do
    for rep in 1 2 3; do
      echo "--- [$arm] $case r$rep start $(date '+%T')"
      python3 "$L/tools-$arm/lab.py" run "$case" "$rep" || echo "RUN-FAIL rc=$? [$arm] $case r$rep"
      echo "--- [$arm] $case r$rep done $(date '+%T')"
    done
  done
done
echo "=== CLI batch end $(date '+%F %T %z') ==="
