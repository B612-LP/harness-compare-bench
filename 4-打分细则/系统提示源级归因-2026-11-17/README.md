# 系统提示源级归因（2026-11-17）

## 问题与授权

请求侧捕获包（§4.50 系列）证明了同一构建下请求组装字节稳定，但 capture req1 的 system（2593 B，SHA256 `8e17c07c2a212f104dea010c0200c45a6b7a27682c91ed4bbc14827da059eb93`）此前只有结构层归因（对齐包 §4.49：信封字节 vs wire 原文），未归因到源。本包把该 system 的**每一节**归属到当前安装构建（DeepSeek Harness 0.2.2-rc.3，macOS arm64）内的被 pin 源文件或配置，并冻结重建规则。

- 0 新增产品运行；只读分析已归档捕获私档与已安装构建的只读快照。
- 源文件快照（9 个文件，SHA256 在证据 `sources` 表）私存于评测私有档，公开证据只含路径、SHA、字节数与节文本；不发布源码大段。

## 方法

1. 从捕获私档 req1 提取 system 原文（2593 B）。
2. 在安装构建的资源包（asar）中逐节定位唯一来源：先用行内片段定位包，再确认该节文本可由被 pin 源文件中的字面量/模板按冻结规则拼出。
3. 冻结 12 个抽取槽（9 源文件 + 4 类槽值），重建器从源快照拼装 12 段、按 `\n\n` 连接，与 system 逐字节比较。

## 逐节归因表（冻结）

| # | 节（公开文本） | 源 | 拼装类 |
|---|---|---|---|
| 1 | You are an AI agent powered by DeepSeek Harness. | dsh-system-prompt/lib/index.js | static |
| 2 | You are a coding agent powered by the glm-5.3-flash model. | dsh-headless/cordis.patch.yml | template（{{model}} 槽 = glm-5.3-flash，来自 profile patch agent-default-model） |
| 3 | Check the [exit code: N] marker on every bash result; … | dsh-tool-bash/lib/index.js | static |
| 4 | Use the read tool — not shell commands like cat, sed, head, or tail — … | dsh-tool-fs/lib/index.js | static（read 已注册条件，成立） |
| 5 | Read an existing file before overwriting it with write and prefer edit for targeted changes. | dsh-tool-fs/lib/index.js | concat（write 段 + edit 段 + 句号；两工具均已注册） |
| 6 | Read a file before editing it unless you just created or edited it in this session. | dsh-tool-fs/lib/index.js | static（edit 已注册条件，成立） |
| 7 | Use the glob tool — not shell find — to discover files by path pattern. | dsh-tool-fs-search/lib/index.js | static（glob 已注册条件，成立） |
| 8 | Use the grep tool — not shell grep or rg — to search file contents. Use read on a matched file when you need surrounding context. | dsh-tool-fs-search/lib/index.js | concat（grep 段 + read 条件段，成立） |
| 9 | Track every background job id you start. … | dsh-tool-jobs/lib/index.js | static |
| 10 | create_goal may infer goal intent … at least 3 consecutive goal rounds … | dsh-tool-goal/lib/index.js | template（blockedAfter 槽 = 3，构建默认值） |
| 11 | Use the workflow tool ONLY when the user explicitly asks … | dsh-tool-workflow/lib/index.js | template（${toolName} 槽 = workflow） |
| 12 | Start independent delegations with `subagent` or `subagent_fork` together … | dsh-tool-subagent/lib/index.js | template（delegates 槽 = subagent, subagent_fork；含内嵌换行产生第 13 节） |
| 13 | Bash, formatters, code generators, and scripts can overwrite concurrent edits … | dsh-tool-subagent/lib/index.js | 同节 12 模板的内嵌段落 |

源文件 SHA256 与路径见 `evidence.json` 的 `sources`；节顺序与重建规则见 `verify.py`。

## 终点

- P1 重建逐字节相等：从 9 个被 pin 源文件按冻结规则重建，与捕获 system 2593 B 逐字节相等（构建模式；证据 `rebuild.byte_equal=true`）。
- P2 13/13 节全部归因：0 未归因节。
- P3 动态槽仅 4 类（model、toolName、delegates、blockedAfter），值全部可从请求体/profile 构建配置观察。
- P4 system 内任务/用户内容字节 = 0：13 节全部为 Harness 指令或构建槽，不含任务文件、用户数据或对话内容。

## 已知限制

- 只代表**当前安装构建**（0.2.2-rc.3）与 headless 捕获 profile 的装配；不外推到其他版本/profile。
- 公开重放核封印一致性（节文本哈希、连接序、源 pin、槽声明）；不能重验私档源文件内部内容——逐字节重建由构建模式在私档完成，独审以独立实现复核。
- 源码为产品私有材料，本包只引用短行/节文本作评测性引用。
- system 节为构建装配，不构成对模型行为或任务结果的因果断言；正式成绩与本节无关。

## 复算

```
# 公开重放（只核封印）
python3 verify.py --evidence evidence.json --output /tmp/replay.json
# 构建（需捕获私档 system.txt 与源快照目录，见私有工具说明）
python3 verify.py --system system.txt --sources sources/ --build-evidence ev.json --output result.json
```

公开 `result.json` 由构建模式在私档生成后安装；公开重放应与其逐字节一致。
