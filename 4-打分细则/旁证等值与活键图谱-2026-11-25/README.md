# 旁证等值与活键图谱（2026-11-25）

R4 环：补齐 R3《轨迹面格式合同候选》留下的两个缺口——豆包输入侧在轨迹面结构性缺席（无 user 行），本环用**落盘旁证件**给出输入侧恒量的等值证据；WB `rawUsage` 同名键 `cached_tokens` 语义分裂（R3 审计 N3），本环给出**逐键活性图谱**。零发射离线复算，数据面为 r1109 bw-retest 冻结原档的豆包 tb-cargo-plan 三槽。

## 预测对照（PREREG 预注册后判定）

| 预测 | 判定 | 要点 |
|---|---|---|
| PA 输入侧旁证等值 | **PASS** | `system/assignment.md` 三槽各 3087B，经旁证掩蔽集后**逐字节等值**（含 Agent ID、ISO 时间戳、槽位路径、本机绝对路径，全部被掩蔽集吸收） |
| PB 旁证件死活分类 | **PASS**（含预测分支修订） | `briefing.md`/`findings.jsonl`/`MEMORY.md` 三槽全 0 字节=死文件（**空洞等值不作声明**：`masked_equal=null`）；预测「findings 为活文件不等值」被数据证伪——改由活文件 `board.md`(221B)、`session_meta.json`(89B) 承载三-run 不等值的如实登记 |
| PC rawUsage 死键非空 | **PASS** | 14 键中**死键 4**（160 载体全 0/空）：`cache_creation_input_tokens`、`cache_read_input_tokens`、`cached_tokens`、`prompt_cache_write_tokens`；**死键=本数据集恒 0，不是协议恒 0** |
| PD 归一层键集一致 | **PASS** | 六键 `{inputTokens, inputTokensDetails, outputTokens, outputTokensDetails, requests, totalTokens}` 逐槽一致；`inputTokensDetails` **160/160 list 形**（R2/R3 已核） |

## 活键图谱（160 载体：WB 6 槽 = 2 任务 × 3 run，逐槽 23–35 载体）

活键 10：`prompt_tokens`、`prompt_cache_hit_tokens`、`prompt_cache_miss_tokens`、`completion_tokens`、`completion_thinking_tokens`、`total_tokens`、`completion_tokens_details`、`prompt_tokens_details`、`credit`、`quota`（WB 计费字段）。

**`cached_tokens` 语义分裂（R3 审计 N3 的图谱化结论）**：顶层 `rawUsage.cached_tokens` ≡ `prompt_cache_write_tokens`（本数据全 0，写维度）；`prompt_tokens_details.cached_tokens` ≡ `prompt_cache_hit_tokens`（160/160，读维度）。同名不同义，任何跨键同名合并都会翻转缓存账。

## 绑定口径

18 个旁证件 = `trace/` 全树（R3 登记的 15 个是 `session/` 子树口径，本环扩展并新增 `session_meta.json`×3；`trajectory.jsonl` 本身不在旁证内，由 R3 单独绑定）。旁证**内容不公开**：本页只登记 SHA256、字节数、掩蔽后等值判定（内容无关统计件 `sidecar-key-contract.json`）。

## 旁证掩蔽集（5 元，逐元素承重）

`m_<id>→m_MASKED`、ISO8601 时间戳→`<ts>`、`__r<digit>→__rN`、`/Users/<user>→<home>`、槽位文件名内 `__r<digit>→__rN`（第 5 元先被第 3 元吸收，本数据集 0 独立命中=冗余声明，实际承重 4 元）。省略时间戳掩蔽即翻转为不等值（近错 NM1 实测）。

## 近错（4 条；其中 NM2/NM4 为不变式自检，非独立扰动实验——如实降级登记）

1. **NM1（真实可达）** 省略时间戳掩蔽 → assignment 三-run 等值翻转（三-run 时间戳互异，掩蔽集承重）。
2. **NM2（不变式自检）** 「单载体非零即破坏死键判定」以字面量注入验证恒等式 `live ⇔ nonzero>0`，非对真实检测路径的扰动实验；独审以独立实现补验该不变式在 160 载体上成立。
3. **NM3（真实可达）** 路径绑定错树解析必失败（依赖三 run mid 互异，实测互异）。语义相对预注册原文「错绑→SHA 不符拒绝」有替换（改为错树路径解析），已按独审要求登记。
4. **NM4（不变式自检）** 「0B 死文件不作 `masked_equal=true` 声明」与主管道同一判据驱动，属同义反复自检；独审补验反事实（0B 文件套等值判定必得空串哈希等值）设计动机成立。

公开复算器附 10 个测试夹具（正常 + 死文件等值声明 / PA 翻转 / SHA 非 hex / 死键误标活 / 全键死 / 载体计数破坏 / 归一层键漂移 / 不等值却三 SHA 全同 / 等值却 SHA 互异，均须拒绝；后两个为三态等值不变式检查）。

## 与既有登记的关系

- 不回填、不修订 R1–R3 与更早已冻结分数；`board.md` 三-run 掩蔽后不等值属于**输出侧状态分歧**的如实登记，不进入任何分数。
- usage 归一层结论与 R2《自报 usage 分离账》一致：WB 归一口径 = Codex 形（`totalTokens=input+output`，cache 走 details），非 DSH 形。
- 第三方受控核验（老师第 3 条）尚未完成，本页属作者侧可复算派生材料，不替代该核验。

## 复算

```bash
python3 recompute.py            # 校验 sidecar-key-contract.json 内部一致性
python3 test_recompute.py       # 8 夹具
```

只吃钉定统计件；旁证原档不在公开仓库（私有管道保持 r1109 原件绑定）。
