# 请求侧跨日稳定性（2026-11-17，第三次运行点；先冻结后运行）

状态：协议冻结（作者生成证据前），预算 = 1 次计划内真实运行 + ≤1 次同日 0 请求失败重试；运行后补 EXECUTION-RECORD / verify.py / test_verify.py / evidence.json / result.json。旧包与历史结论不改。

## 背景与先验披露（作者已读，不冒充盲测）

- 作者已完整读过 2026-11-16 18:33 首次捕获（[DSH请求侧最小捕获-2026-11-16](../DSH请求侧最小捕获-2026-11-16/README.md)）：req1=33091B（system 2593B+22 工具，req SHA `92220699…`）、req3=34107B（delta +1016B）、辅助请求 1042B（thinking enabled, max_tokens 4096）、stdout step1 input 7620 / step2 cacheRead 7616。
- 同夜 t2/t3 各 run（环7/环15）与今天运行前的全部请求侧包均已公开；作者未读今天即将产生的请求。
- 应用构建元数据（运行前登记）：DSH app.asar mtime=2026-11-13 15:31:48、版本 0.2.2-rc.3，与昨日捕获时相同——故本环是**运行时点（runtime point）对照，不是构建（build）对照**；若字节全同，结论命名 `cross_day_runtime_stable`，只证「同一构建在隔日运行产生同构请求面」，不证未来版本不变。

## 运行方法

- 同一 profile（capture-r1，baseURL→本机新代理实例，上游 open.bigmodel.cn GLM）；同一工作区（capture-r1，两文件字节 pin：TASK.md `68599aec…`、dominoes.py `89f1fede…`）；同一 prompt 字节（从昨日捕获 req1 messages[1].content 逐字提取落盘为新 prompt 文件并 pin SHA，运行前不再改动）。
- 请求/响应原文只入私档；公开仅派生哈希/字节量/形态；Authorization 只存 SHA 前缀。

## 终点（描述性；n=1/点）

- **E1（主）**：新 req1 与昨日 req1 内容级分类——逐字节相同则 `IDENTICAL`；否则逐叶列出差异（system 字节/工具 digest/消息字节/参数字段），每差异给双侧 SHA，不 guess 归因。
- **E2**：新 run 内前缀性——第 2 主请求 = 第 1 主请求内容级前缀 + 仅追加消息；delta 逐条归因或 UNKNOWN。
- **E3**：辅助请求（标题生成形态）出现性与形态（0 工具/thinking enabled/max_tokens 4096 是否复现）。
- **E4**：stdout 步进 usage 与 cacheRead 登记（product-reported，不认证服务端）。
- **E5**：两次运行点间辅助/主请求时间间隔与请求序（register only）。

## 边界

- 单任务单模型单点；字节为传输层，不认证 tokenizer/缓存语义；`IDENTICAL` 不外推模型行为不变；运行时 HOME/网络环境差异不作因果主张。
- 不改旧包/旧分/正式 25 格；0 其他产品运行；本环不推导跨 provider 结论。

## 修订与结果状态（发布前补记；时间线以 FS stat 为准，经非作者独审订正）
- 本页冻结于首次成功请求之前（FS birth 17:41:40）。其后两次修订的**真实顺序**：①零请求失败重试上限 ≤1→≤3（FREEZE-AMENDMENT.json，FS 17:45:39，先于任何成功请求；三次失败均为调用层错误：key 未导出/包装器参数位置/代理端口不符，均未触达模型）；②新增归因对照 run（FREEZE-AMENDMENT-2.json，FS 17:49:18）——**写于 runA（attempt4，双 key）3 请求完成（17:47:02）之后、runB（attempt5，仅 ZAI key）首请求（17:49:22）之前 4 秒**，其内容引用 runA 漂移事实自证；预登记期望/反证覆盖 runB，不覆盖 runA。同一 run 内不构成有效预登记对照的部分仅 runA 自身。
- 结果：期望命中、反证未触发——跨日漂移完全归因凭据条件化的 web 工具注入面；固定凭据面下跨日请求字节稳定。最终 six 件见本目录，独立审计记录见私档。
