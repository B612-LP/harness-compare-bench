# _归档-v1：旧 5 题（2026-10-16 ~ 2026-10-22）

这 5 道自建用例已从现行题库退役，原因：在 **DeepSeek V4.1-Flash + thinking=low** 下被 Codex CLI 与 DSH CLI 打满（25 场协议里的 10 场 CLI 批次 **10/10**），结果面区分度为 0，只能证明「能力达标」不能比 Harness。证据见 [`3-表现现场/r1023-cli-dsf-low/`](../../3-表现现场/r1023-cli-dsf-low/)。

| 用例 | 定位 | 退役前状态 |
|---|---|---|
| `int-sum-sort/` | hello · 数据处理流水线 | 双款满分 |
| `word-freq-report/` | 进阶 · 词频与排序 | 双款满分 |
| `jielong-fullchain/` | hard · 接龙解析分单 | 双款满分 |
| `ledger-replay/` | hard · 乱序事件状态机 | 双款满分 |
| `corpus-squeeze/` | hard · 受限压缩达标 | 双款满分（`compressed.bin` 双款字节完全相同，已知独立性存疑） |

**保留原因**：2026-10-19 ~ 10-22 的表现现场、阶段报告与周报里引用了这些路径；归档保留可复核性。**不再新增运行**，新数据一律用现行 5 题（见上级 [`README.md`](../README.md)）。

已知遗留缺陷（未修，随归档冻结）：`corpus-squeeze/checker.py` 在 `run_dir` 传相对路径时，roundtrip 子进程拿到被截断路径导致误判 0 分；绝对路径正常。修复方法：`run_dir = Path(argv).resolve()`。