FROM ubuntu:24.04
WORKDIR /app

# Task input (fixed, deterministic): sum=245, count=6, sorted=8 17 23 42 56 99
# 2026-10-21 v0.3：输入改由 environment/input.txt 提供（字节与旧 printf 完全一致），
# 使轻量判卷器（checker.py）能对输入做 SHA-256 完整性守卫。
COPY input.txt /app/input.txt
