# 支持域与漂移判定（试行 v1）

日期：2026-11-23。各口径页声明了结构与数字的门，但「输入是否落在已校准范围之内」此前没有一处显式登记。本页把冻结原件的支持域列成清单，并给出一条出域判定规则；试行不冻结。对应[冻结门清单](<../观测规范冻结门清单-2026-11-23/README.md>)的 G5 门，[未知处置表](<../未知处置表-2026-11-23/README.md>)的出域行为在此获得清单依据。

## 支持域清单（来自 130 份冻结原件，65 请求+65 响应流）

| 线 | 族 | 请求/响应流 | 请求顶层键集合 | SSE 事件名 |
|---|---|---|---|---|
| DSH messages | R38 | 23/23 | 基础 8 键、带工具 10 键（见下） | 7 种（见下） |
| DSH messages | R52 | 26/26 | 同上两种 | 同上 7 种 |
| DSH messages | R77 | 4/4 | 同上两种 | 同上 7 种 |
| Codex responses | R53 | 12/12 | 单一 11 键集合 | 13 种 `response.*` |

- DSH 基础 8 键：`dsh_plugin_packages`、`dsh_session_log`、`max_tokens`、`messages`、`model`、`stream`、`system`、`thinking`；带工具 10 键另加 `output_config`、`tools`。
- DSH 7 种事件名：`content_block_start`、`content_block_delta`、`content_block_stop`、`message_start`、`message_delta`、`message_stop`、`ping`。
- Codex 11 键：`client_metadata`、`include`、`input`、`model`、`parallel_tool_calls`、`prompt_cache_key`、`reasoning`、`store`、`stream`、`tool_choice`、`tools`。
- Codex 13 种事件名：`response.created`、`response.in_progress`、`response.completed`、`response.output_item.added`、`response.output_item.done`、`response.content_part.added`、`response.content_part.done`、`response.output_text.delta`、`response.output_text.done`、`response.reasoning_text.delta`、`response.reasoning_text.done`、`response.function_call_arguments.delta`、`response.function_call_arguments.done`。

## 漂移判定规则 v1

- 请求：顶层键集合不在清单内 → `unknown_out_of_support`，不静默收下；在清单内 → `in_support`，域内仍走[DSH 口径](<../DSH观测口径校准-2026-11-19/README.md>)、[Codex 口径](<../CodexResponses观测口径-2026-11-23/README.md>)、[数字口径](<../数字口径定版候选-2026-11-23/README.md>)各自的结构门与数字门。
- 响应流：出现清单外事件名 → 该流 `unknown_out_of_support`（已核实层保留，不填 0）；事件名全在清单内 → `in_support`。
- 升级条件：供应商 schema 演化的证据（官方变更记录，或新捕获整批一致的新键集/新事件名）→ 另环扩清单并重校准；本页不预设漂移阈值。
- 校准与负控：130 份原件全部 `in_support`；合成负控（清单外顶层键、清单外事件名）按规则出域；已知 DSH 基础键集与 7 事件名流按规则入域。判定只回答「入域/出域」，不替代结构、近错与数字门。

## 它不能说明什么

- 清单来自 2026-11-23 前的冻结批；新产品的合法演化会出域——出域不是缺陷判定，而是「当前校准面之外」的登记。
- 入域不等于通过任何结构门；出域层不抬高或拉低任何历史成绩。
- 不冻结；扩清单走另环；不覆盖受控第三方核验（外部阻塞维持）。

## 证据与边界

清单与判定由环内脚本从 R112 封印的 130 份原档抽取（逐锚 SHA 链可复算）；与四份口径页和[验收条款](<../../反馈/2026-11-18-第五轮/验收条款-公开版.md>)第 1 条的对照见环执行记录；非作者复审收据随环登记。
