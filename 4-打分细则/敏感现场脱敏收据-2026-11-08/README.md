# 敏感现场脱敏收据（2026-11-08）

对应老师 2026-11-03 新追问④「敏感现场脱敏收据/见证签名」的机制落地与 l6 试点。

## 机制

- `tools-redaction-receipt.py`：对每对「私档原件 → 公开脱敏派生件」生成机械可复核收据。原件侧只披露不可逆 sha256、字节数与文件名；派生件侧披露仓内相对路径、sha256、字节数；另记载脱敏范围结构描述（scope）与方法规则 id（method）。
- 输入分离：公开清单 `redaction-manifest-l6.json`（不含任何私档路径）；私档映射（basename→私档绝对路径）仅本机保存，工具含防泄漏断言（收据载荷不得出现私档路径）。
- 见证签名=机械双跑：`--witness` 模式用独立实现（`shasum -a 256` CLI，区别于主跑的 python hashlib）复算全部哈希，并对收据 pairs 块做逐字节确定性重放比对。**机器见证，非真人签名**（真人第三方核验要求已于 2026-11-04 由用户取消；本机制不虚称真人见证）。

## l6 试点（2026-10-30 l6-wb-gateway 敏感现场）

| 私档原件（basename） | 原件 sha256 | 脱敏范围 | 方法 |
|---|---|---|---|
| e1-to-e2-authorized-diff.json | `d0a3afcfe3eedfe840629204aa35275fa63bb685407a33fd9b493f183adc6b0b` | 全文不公开；公开摘要仅记载差异段数=7 | R1-移出私档+摘要替代 |
| l6-runtime-defaults-audit.json | `41319954dc29e2bf087636fc7b8940c3ebc81b20bab93318c5e657cf3b9d9a90` | 审计条目内容不公开；仅记载条目数=85 | R1-移出私档+摘要替代 |
| release-refused.json | `84cd9c19ce86d80d6932bc4ab6cbc0d71410b97511d11f1c6b7719a8b70789b2` | 完全不公开（内部控制记录） | R2-移出私档+不公开 |

三对均绑定同一公开派生件 [public-redacted-summary.md](<../3-表现现场/l6-20261030-wb-gateway/receipts/public-redacted-summary.md>)（收据时点 sha256 `567f4d15…`，全值见收据文件）。

- 主跑收据：[redaction-receipt-l6-pilot.json](<redaction-receipt-l6-pilot.json>)
- 见证收据：[redaction-receipt-l6-pilot.witness.json](<redaction-receipt-l6-pilot.witness.json>)

## 诚实边界

1. 公开脱敏摘要是**事后编制的派生件，不是历史原件**，不替代证据、不证明产品表现；本收据证明的是「哪份私档原件、以何种范围与方法、对应收据时点哪份公开派生件（字节层面）」。
2. 机器见证不认证私档原件真实性；原件在私档保存，公开侧无法独立验证其内容真实性。
3. 原件哈希为不可逆披露，用于未来比对「同一原件」；不含内容、不含路径前缀。
4. 收据绑定收据时点字节；派生件此后若修订，须出新收据，不改旧收据。

## 用法

```
python3 tools-redaction-receipt.py <公开仓根> --manifest <清单> --private-map <私档映射> \
  --out <收据> [--receipt <运行收据>]
python3 tools-redaction-receipt.py <公开仓根> --manifest <清单> --private-map <私档映射> \
  --witness <已有收据> --witness-out <见证收据>
```

运行收据与私档映射存仓外私档；收据 write-once。与 [竞品评测报告 v1.9 §4.5](<../5-评测报告/竞品评测报告-v1.9.md>)「脱敏收据不是原件签名，机器审查不是真人见证」口径一致，本目录即该口径的机制实现，不改报告正文。
