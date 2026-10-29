# L4 预注册：请求级缓存语义、归档测量效应与 WB gateway 正式批次

## 1. 封印与范围

本轮是一个完整闭环，完成后停止等待放行。分支 `loop4-2026-10-29`。

采用两阶段封印：D=本设计及 plan.json/contract.json 的 git 提交，先于实现；E=实现完成、合成负例通过后的 execution-manifest.json 与全部执行代码/配置提交，先于任何真实模型请求。E 的完整提交 ID、提交时刻由只读 git 自动提取进入 runtime-binding.json；registered_at 严格等于 E 提交时刻，不手填。计划/合同必须同时存在于 D 和 E 且字节一致。实现和预检不得暗中发模型请求。真实运行仅在 lead 明确释放 E 后开始。

运行身份、顺序与完整槽位以 plan.json 为准；评分与准入以独立 contract.json 为准。旧 v1/v2/v3 合同及产物不改，不向旧表加槽位，v3 恒空语义保留。本轮不写周报，不改 CHANGELOG。

## 2. 研究问题与可识别边界

A. provider-cache：直接保存官方 API 原始请求体/响应 usage，区分字段缺失、null、0 和正值。检验历史“creation=0”是否来自原始协议缺字段或归一化投影，不把 absence 解释为无写入，也不把 miss 当作 cache creation。与官方缓存文档 https://api-docs.deepseek.com/zh-cn/guides/kv_cache/ 对照（文档称 best-effort，hit/miss 不承诺必命中）。不从 usage 推货币成本。

B. runner：历史 r1030/r1031 混合 rep 不能估计代际因果贡献。先固定模型执行，采用同一份新执行证据的两个独立副本重放旧/新归档测量语义，识别记录留存、可判定性、usage 投影和分数差异。丢证或无法复现须报告 unknown，不补零。新 CLI sentinel 重复运行仅描述当前条件下极差，不是“旧/新生成质量随机对照”，不作零效应/统计等效、贡献百分比或产品排名结论。

C. WorkBuddy：五题 first slots、单独 WB gateway 产品交付态（wb_gateway_delivery）。历史证据指向 www.workbuddy.cn 网关，不能推定官方直连或同权重。模型 alias、effort、权限、工具、skills、版本及可观察路由分别登记；不可观测项管理为限制，不借改名放入 A_same_model 或旧 B_native。不改既有 WB 不准入历史裁定。

## 3. 固定实验与顺序

### A：裸模型缓存探针

18 个固定槽位：responses、anthropic-messages、chat-completions × 2 block × fresh/repeat/nonce-control 三次。每协议/block 使用独立 nonce（置于最前可控文本），synthetic prefix 固定生成；repeat 请求体与 fresh 逐字节一致，至少等待 5 秒；control 仅替换首 nonce。block 1 协议正序，block 2 反序。协议实际端点须有本机历史取证或官方规范支持，不猜路径。

使用同一既有官方 DEEPSEEK_API_KEY 引用（只在进程内读取，不展示或入库）、deepseek-flash、low；输出上限 256 tokens（具体 wire 形状在 E 封印）。不支持的协议或 4xx/格式错不改请求适配重跑：保存首次失败，该协议剩余槽位记 not_executed+原因，不挪额度给其他协议。任何结果都不追加样本。两次连续网络/服务失败停止该协议并完整列示未执行槽位。原始 body/SSE、HTTP status、request/response ID、时间、时延、usage 原字段与映射逐调用保存，认证头与密钥绝不保存。

fresh 只是新 nonce，不宣称真实冷缓存；repeat 不保证热命中；全部零命中结论为“本条件未观测命中”，不等于服务端无缓存。usage 分母/是否包含 cached 必须从该协议原字段说明，禁止跨 wire 盲目求和。

### B：CLI 当前执行与双归档反事实重放

Codex/DSH 各 6 场：dabstep-payments-10、tb-cargo-plan 各 3 rep，共 12 场。rep1 顺序 dab→cargo，rep2 cargo→dab，rep3 dab→cargo；产品各自串行，可跨产品并行。选择两题因历史已见翻转/极差，是诊断性选题而非 holdout，不泛化至完整五题总分或未知题集。

固定当前 CLI build/profile/route、deepseek-flash、low、离线题解约束、skills/web off（实际配置入 E）。每槽一个全新会话和仓外 workspace，只复制题面允许的 inputs/TASK。规范化 prompt（仅独立绝对路径不同，路径混杂显式保留），每场保存实际 prompt 哈希；不把两代不同路径冒充逐字节相同请求。

整场 CLI/session 重启上限为 0：whole-CLI 失败不等于同 HTTP 重传，不以“transport retry”名义重启工作区。产品内部不可控制的 HTTP 重试如可观察须留痕；不可观察则披露。单场 timeout 沿用冻结 case.json（dab 1800 秒，cargo 2400 秒），超时停进程留部分产物按合同判卷，基础设施错误与能力失败分开。不额外设无法执行的内部请求或金额上限，明确总逻辑槽位和时限，实际 usage/calls 全量报告，缺失不填 0。

评分/归档与执行上下文隔离：被测 agent 不得接触仓库或 checker/truth/solution；runner 可机械执行冻结 checker，不语义阅读标准答案。每场 original stdout/stderr/session 先持久保存到不可覆盖新路径，再在两个独立 sandbox 副本执行 legacy/current 后处理；旧丢日志等缺陷只在副本复现，不删除母本。若只能实现等价模拟而非原 pipeline 原样调用，须披露适配 diff 与推断边界。

### C：WB 独立正式批次

固定五题顺序 bird、dab、exercism、lcb、cargo，各 1 场；新命名空间 l4-20261029-wb-gateway，不复用 r1030/r1031。不做能力冒烟；封印后可做零模型版本/驱动/路径预检，不建探针题会话。不得为预检终止用户现有会话、改网络配置、注入产品代码或回滚版本；无法非干扰接入则记 infrastructure_not_executed。

每场全新仓外 workspace/session；沿用冻结题目 timeout。产品原生 trace + 产物 + 提示词 + checker 评分为证据，不录屏、不要求截图。启动/结束记录 app 版本与 app.asar 哈希，若中途升级则暂停剩余槽位、保留已跑证据并分层；不换版本补跑。模型/route/effort等未知不得假填已知值。

## 4. 执行前闸门与真实准入

E 释放前：封印旧合同 verify 双通过；L4工具合成正反例通过；检查固定槽位唯一性、既有身份碰撞、输入/checker快照、仓外隔离、证据写入非破坏、默认零模型 dry-run。任何运行 E 代码/配置 drift 必须停该槽位并保存首次失败，不在已看结果后修改后补准入。

L3 --spec 是 fixtures 自检、--retro 是披露矩阵，二者 exit 0 不代表真实准入。本轮生产消费者须逐场 validate_meta+classify，同时做语义检查：完整计划全集（包括未执行/失败）、唯一 run/event ID、注册源与 E 全提交绑定、registered_at==E时刻<started_at、文件 SHA/bytes 实算、actual route/模型证据、isolation.ok、attempts/selection、判卷完整分母与原始收据、独立污染裁定。合法 enum（如 status=error 或 integrity=violation）不等于准入通过。

准入输出必须区分 field-compliance、execution-status、evidence/integrity、score 与 formal-admission；缺一槽、重复、错 hash、无 seal、非法 alias/route、污染、未知失管、未授权重启均有负例。基础设施失败/未执行为诊断记录，不记能力零分，不按已评分部分折满。WB可在预先声明的独立gateway层有效，但禁止借此跨路由归因。

U1：首个真实产品运行执行后，审计侧用完整 E 提交 ID 核 git 内 plan/contract/manifest 的 blob、runtime-binding 的精确时刻来源与真实 meta.registered_at；L3 reconcile（>=）只作一个组件，外层另核等值和先后。git时钟不是第三方可信时间戳，仍保留这一限制。

## 5. 分账、证据与职责

product_run：12 CLI + 5 WB 共17固定槽位。bare_model_probe：18固定槽位。interface_preflight：零模型环境预检；self_test：合成fixture/工具测试；offline_recompute：双归档重放与独立复算；grading_regression：0（不修判卷器）。预算指槽位上限，未执行/部分执行单列，不凑完成数。

lead 只做 git/封印/调度；builder事实报告必须落各自批次目录的 REPORT.md+机器收据，报告与修正链保留。各自写界见任务板；共享活台账由lead收口串行登记，不并发改。新收据统一内嵌 live_doc_drift（list）且用 evidence-kit；时间/哈希由脚本生成。旧收据不改。必要的 receipt 原子拒写/新鲜度/严格准入只在 L4 新工具中实现，不大改历史工具。

judge 独立验收（不得依赖builder已给出的分数/结论）；auditor敌意审查，至少核真实U1、全槽位对账、缓存原字段、双归档推断边界、WB路由分层。结论按观察—证据—解释—未排除因素—可复现实验五段。

## 6. 停止与剩余问题

任何凭据/标准答案泄漏、越界污染、模型/产品意外漂移、E代码漂移、准入误收，立即停相关执行/主张并归档；不静默重跑。未知包含影响/下一步/停止条件。缓存未命中不判模型失败；历史runner生成差异的因果贡献本轮不识别，不伪称消融已全部完成。

L3池项③汇报仓内归档、④非破坏写、⑤源hash新鲜度、⑧drift键、⑨消费者语义本轮按执行需要落L4新工具；⑥seal标签清理和⑦其他低风险文档/计数尾项保留池，不承诺全部做完。O6只在新L4消歧侧栏集中说明旧批次完整路径，避免修改已封印历史README；不静默宣称旧注记已完成。
