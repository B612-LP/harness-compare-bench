# 第三周公开包独立复核

**PASS（限定为公开包离线复核）— 125/125 独立检查通过，最终 exit 0。**

未调用模型 API、未读取认证、未复制私有驱动；不宣称线上复现。双最终 ready 后才运行。完整逐命令/退出码/输出/输入 SHA 见[final-03 收据](<final-03.json>)，简明机器入口见[receipt](<receipt.json>)；预先标准见[criteria](<criteria.md>)。

## 观察

- 在全新 `/private/tmp/hcb-independent-20261029-0rwa0q88/public` 复核2366个公开文件（381197872 bytes）。空 HOME、清空环境后，sandbox 对原仓库、原 HOME 私有工作区、旧 tmp、旧原生 spill 树的读取及网络 connect 均实测 `EPERM`；本次公开副本正常可读。没有依赖原仓库/私有工作区的隐式 fallback。
- 先验证发布物，再在另一个输出目录重建：冻结入口 verify/build、发布物与重建结果逐字节对比、作者38项自测均通过。38断言属于一次 self_test 子命令，不是38场产品运行。
- 原1542件保护对象在检查前后均字节相同。326条历史源引用中242条公开原件 SHA 一致，84条私有引用明确不可公开取得；不回原 HOME 补齐。保留25格有限历史候选，正式 A=0、B=0；未知分数保持 null，不变成0或满分。旧96行是混合历史账，不是96场产品运行。
- 最终六类已登记事件分别为97/8/7/3/5/9（产品、自测、离线、回归、裸模型、接口）。这些是有定位收据的登记范围，含无效/研究事件，不是正式有效产品样本数，也不是所有历史活动总量。
- 六场机制证据对应12次实际请求；本次只离线解析，新增在线请求为0。首请求完整 JSON 六场全部一致；profile 除唯一 inline 预算干预外一致。

## 证据

[原创干净环境 runner](<clean_room.py>)调用[原创独立检查器](<independent_checks.py>)：独立生成合成正例与反例，直接读取原始 request、SSE、持久化 session、CLI trace、tool-output 和 process SHA，不把作者 summary 当证明。机制188文件[manifest](<../../../3-表现现场/r20261029-mechanism/evidence-manifest.json>)、四版冻结源及原作者只读 manifest/analyze 入口均复验通过，分析重建仅忽略 generated_at 后与发布物相同。

反例覆盖：原账字节篡改、完整 inputs 树漂移、必需字段缺失、错误事实 pointer、污染、未冻结、无效最终裁定、重复 event ID、同一原始 run_id 换名、研究变体及冒充 canonical、同名模型换非官方路由、跨计划重启首样、丢弃登记首样、首低后高不挑最佳、未知无管理项、按已评子集折满分。原始篡改和 malformed 输入返回非零；语义无资格但结构有效的输入保留明确拒绝理由，不伪装成产品能力失败。

| 配对 | full 第二输入 | bounded 第二输入 | full−bounded | 独立核到的剩余差异 |
|---|---:|---:|---:|---|
| 大输出第一对 | 19697 | 1509 | 18188 | tool_result + thinking；full首场无原始SSE |
| 大输出第二对（交叉次序） | 19697 | 1492 | 18205 | 只剩 tool_result 文本 |
| 小输出负对照 | 504 | 524 | -20 | 工具结果完全相同，只剩 thinking |

上表输入为 provider 三个输入字段（uncached/cache-read/cache-creation）之和；原字段分别保留、与 stdout usage 交叉一致。归一化只处理消息工具调用 ID、tool_use_id 与 thinking signature，不抹掉 thinking 内容或其他字段。两个大输出原文均35767 bytes、SHA `fed57592028c9d8a9180c2b97f74a3cd5e0daa841aab244cf4aad78fe44626a2`；由独立 Python 重建固定420行噪声后核对。bounded 保留两端目标、移除中段，真实请求具官方 host、deepseek-flash、low、max_tokens=1024、唯一 fixture 工具和HTTP200。

### 首次失败与修正（未覆盖）

1. [初始 sandbox 探针收据](<sandbox-preflight.json>)保留“socket 创建不等于联网”的错误假设及 connect 修正。
2. [final-01](<final-01.json>)：reviewer 正向读探针错误使用未被 git tracked/copy 的根 AGENTS；未执行被验代码。改读明确复制的检查脚本，不放宽 sandbox。
3. [final-02](<final-02.json>)：121/125通过，4项失败均定位为 reviewer 假设错误：BIRD正例误用10而不是15的完整分母，连带首样选择正例失败；两场 large/full 的 CLI stdout 工具结果实际仅8192字符精确前缀，不能要求等于35767字节 wire 原文。修正正例与显式展示截断规则，不改任何被验实现/冻结证据。
4. [final-03](<final-03.json>)：全新副本125/125通过。保留全部首次失败收据；[机制 v1 首失败](<mechanism-v1-first-failure.json>)亦保留，未改写成模型失败或成功。

## 解释

证据支持的最窄机制结论是：**本受限 DSH CLI 研究实验中，单改原生 maxInlineTokens=12500→512，确实改变下一次真实模型请求的工具结果；第二大输出配对在只剩该文本差异时，观察到总输入19697→1492。** 这是机制存在性与本次输入用量观察，不是产品普遍质量、固定节省比例或金钱成本结论。

六场两端提取均正确，只说明该人工受限任务没有观察到答案退化；不能扩写成题库能力或普遍质量优势。正式表空不意味着产品失败；历史原分、两期归档复算和本轮未新判卷的轴保持分离。

## 未排除因素

- 第一大输出配对首场仅有两个实际请求/HTTP200、stdout 和 provider-parsed 持久化 session，缺原始 SSE；原 actual_api_gate=false不改写。该对不能与第二对同等级，也不能把usage全部差值无条件归因于干预。
- **CLI stdout 大输出只显示8192字符前缀**；独立复核严格核其前缀与工具ID链，不声称它包含全量。完整内容证据来自实际第二请求、固定源重建、tool-output/process SHA。
- 初始 runner 错扫 HOME/spill，漏了系统 tmp 原生文件。[事后恢复收据](<../../../3-表现现场/r20261029-mechanism/spill-recovery-posthoc.json>)和两份公有完整副本补证 SHA 一致，但这是 posthoc 文件存在/可读证明，不是运行当时的记录，更不是模型恢复行为。模型没有 read/bash 工具是共同实验约束，不是 DSH 天生不能恢复。
- thinking 随机差异见第一对与小输出负对照；小输出usage不是相同，而是504/524。样本极小、固定顺序、人工任务/工具约束、未做自然恢复实验。服务端只返回模型别名，后端权重实现未独立锁定。
- 本地日志/封条/SHA/JSON pointer 证明包完整性与来源值一致，不等于独立证明来源语义真实性、可信第三方时间戳或绝对无污染。84条非公开源仍是不可复核边界。

## 可复现实验

macOS 自带 sandbox-exec + 系统 Python 标准库，无需安装软件。实际成功命令如下；再次执行应换一个新 label，禁止覆盖现有收据：

```bash
/usr/bin/python3 -B '5-评测报告/独立复核-2026-10-29/reviewer/clean_room.py' \
  --root "$PWD" --ready-freeze --ready-mechanism \
  --check-script '5-评测报告/独立复核-2026-10-29/reviewer/independent_checks.py' \
  --label final-03
```

系统 Python 的 xcrun 曾尝试写旧 tmp 缓存，被 sandbox 拒绝并留 stderr；未放开旧路径，解释器及检查仍 exit0。所有原件/反例变异仅在新副本，未改实现、历史或 CHANGELOG，未提交 git。

### 验收版本 SHA-256

| 对象 | SHA-256 |
|---|---|
| [冻结引擎](<../../../4-打分细则/可信冻结-2026-10-29/freeze.py>) | `f1f8e8e988ea0c22587a96ff606d588cbab6636bd09cf3f77a2521848a4f7681` |
| [冻结封条](<../../../4-打分细则/可信冻结-2026-10-29/freeze.lock.json>) | `c784614e891390682c1fd28fa3d2f5b190fdb833943faedf3b1857ef43ba1bad` |
| [机制 manifest](<../../../3-表现现场/r20261029-mechanism/evidence-manifest.json>) | `998a9f6a17e3517aa012dcd6e2e57dafe8f0a1cf4156a429ada4121de394d25e` |
| [原创 runner](<clean_room.py>) | `24e058f9522f5fc6f0d3e380bd53684a951b07dc73492302a1e7baadf81acba0` |
| [原创 checks](<independent_checks.py>) | `f540031c7f0ff2942b728be2d13d5e66ac8cd5ed2afaf6bd18ff91d6518a1a8b` |
| [完整成功收据](<final-03.json>) | `67bee3dd6a7f353b3b18edaf7ef4c91cded722d148037896faeb4d5ffe873deb` |

四个被验实现/产物 scope 共221文件的规范清单 SHA：`09476ddc52a04913bdd22c4ade99e313de15727caf00a2686b18cb85708d74f9`；编码和完整逐文件清单入口见[receipt](<receipt.json>)。这不包含Lead后续整合的根报告/导航，避免将其文字更新误算成代码验收版本变化。
