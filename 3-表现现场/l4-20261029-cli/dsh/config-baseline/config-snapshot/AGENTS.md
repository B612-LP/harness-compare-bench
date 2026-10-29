---
name: global-agents-defaults
description: 汽水的用户级默认规则：代理、SSH、DSH 插件热加载、HTML 交付、作业封面身份信息。
---

# 用户级默认规则

## 代理

Clash Verge 混合端口 `127.0.0.1:7897`。终端 `git`/`curl`/`gh` 不读系统代理，访外网按条加 `HTTPS_PROXY=http://127.0.0.1:7897`；`ssh`/`scp`/`rsync`/Tailscale 不走代理。改网络设置前先说明。

## SSH（Tailscale，账号 `b612-lp.github`）

- 宿舍机器 = `ssh work-01`；工作室机器 = `ssh studio-01`（`WIN-PCUL207TV6I` / `100.67.127.9`）。用户均 `Administrator`，共用密钥 `~/.ssh/dsh_work01`。
- 传文件 `scp`/`sftp` 可用；或 `tailscale file cp <file> studio-01:` → `D:\Downloads`。
- 工作室机器的 PowerShell 已配 UTF-8 profile，中文不乱码。
- 新增机器：Tailscale 同账号入网 + OpenSSH Server + 公钥进 `C:\ProgramData\ssh\administrators_authorized_keys`。

## DSH 插件热加载

本机 Desktop App 的当前 profile 开着 dsh-hmr：改 `cordis.patch.yml`、`dsh plugin add`、改插件源码都实时重组生效，但客户端 UI 要刷新页面（Cmd+R），别急着说「重启 DSH」。

## HTML 交付

生成的 HTML 页面颜色统一用 CSS 变量，并默认跟随系统明暗（`prefers-color-scheme`）；需要切换按钮时我再单独说。

## 微信小号「冰块」

我的微信小号[REDACTED-PII:name-line]

## 作业封面/填表信息

[REDACTED-PII:name-line]
