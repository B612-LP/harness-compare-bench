# 当期上游条款观察（2026-11-05）

本补充提供**当前观察到的条款/版权notice证据**，不修订[原来源与复用边界](<../来源与复用边界-2026-11-05/README.md>)及其固定清单，不证明2026-10-22历史取材适用这些版本，不为本仓原创件选择许可。日期是来源观察日，不是对发布日或许可生效日的推断；正式25格、A/B/W分轨、n、gold、历史分数均不由本补充更改。

## 公开内容分层

| 来源 | 可离线阅读的本包内容 | 版本与不能推出的结论 |
|---|---|---|
| Exercism Python | [完整MIT正文](<exercism-MIT.txt>)，1065B/21行，保留©2021 Exercism、条件与免责 | commit `6105f6d9d3ef66ce3d5c8f529d2882af3d76b706`；不证明Aider历史打包版本，不覆盖problem-specifications等未查项目 |
| Terminal-Bench | [完整Apache-2.0正文](<terminal-bench-Apache-2.0.txt>)，11357B/201行，模板原样保留 | commit `73d6279f91eb773bd51af2e2572a6fa044342e7a`；附录`[yyyy] [name of copyright owner]`不是已填项目通知，不证明旧Cargo任务NOTICE全链已核 |
| DABstep dataset | [完整具名版权/许可notice原文件](<dabstep-NOTICE.txt>)，321B/1行 | commit `22a0bb5708f36d0ccda1355be1868c07050cc7e2`；上游文件名LICENSE不等于完整CC法律正文，不自动覆盖Space/scorer代码 |
| BIRD | [机器清单](<observations.json>)内的短引文/中文摘要、canonical URL、新闻日期、响应metadata和摘要值 | [官方主页](https://bird-bench.github.io/)新闻日期2024-04-27，当前响应Last-Modified `Thu, 29 Oct 2026 14:32:10 GMT`；仅为数据许可声明，不是完整CC法律正文 |
| AtCoder | [机器清单](<observations.json>)内的短引文/中文摘要、canonical URL、修订标示和摘要值 | [官方英文条款](https://atcoder.jp/tos)标示June 29, 2026修订，无已建立的不可变commit；不是本仓题面/测试复用授权，LCB仓库MIT不替原素材授予权利 |

BIRD与AtCoder完整HTML仅留非公开副本，分别350031B和16463B。本包有对应观察时的SHA/HTTP/UTC时间，但**公布私档SHA不等于公众能够离线逐字复核未公开的完整HTML**；公众可检查所发布的短引文/摘要及访问源站当前页面，当前页面可能变化。本包仅三件正文镜像支持其离线逐字核对，不宣称五来源完整条款全部公开。

DAB原notice具名六位作者，保留原始©2025与CC BY 4.0链接；不因其与原规格组织级来源名称不同，就认定历史署名违法或版权主体链已认证。Apache第4节的提供副本、修改说明、保留通知及“若发行含NOTICE”的条件可直接阅读，保存这份许可本身不证明其他材料的义务已全部满足。

## 获取收据与失败分账

[结构化观察及必要获取字段](<observations.json>)保留官方URL、真实UTC起止、HTTP状态、curl退出值、响应bytes/SHA、观察版本与内容类别。主体获取时段为2026-11-05 14:42:17Z–14:44:58Z；不是把本地时钟时间标成UTC。

- 12次HTTPS请求：7次HTTP200、2次API403限额、2次精确根路径NOTICE404、1次TLS退出35且无HTTP响应。JSON对无HTTP响应使用`null`，不是源站HTTP0或404；无body时bytes=0、SHA=null。
- curl退出0不等于HTTP成功；403错误体不是目录/条款正文。两次NOTICE404只限精确固定commit根路径，不能推断全仓、任务、嵌套目录或历史版本没有NOTICE。
- 另有3次fetch服务层404，不是源站404，独立分账且不混入12次请求。只有必要失败摘要公开，不将服务层错误体冒充源站内容。
- DAB固定commit顶层listing可读，但没有递归或Space/scorer核查；Exercism目录请求TLS失败、Terminal-Bench目录请求限额，NOTICE覆盖仍为unknown。
- 固定commit LICENSE原字节与BIRD/AtCoder当前页面观察分开；当前commit解析观察不等于已核验签名或历史取材绑定。未知不得因为HTTP200或摘要匹配自动变为已认证。

## 四层状态，不授新权

1. 当前观察：取得指定版本/时点的正文或声明；三正文镜像可离线核对。
2. 历史材料适用版本绑定：`unknown`，绑定版本`null`。既有BIRD发行快照、LCB v6/题目日期等已知记载没有因此被抹去。
3. NOTICE全链覆盖：`unknown`；顶层listing和精确路径404不等于递归完整检查。
4. 原创owner许可：`not_selected`、值`null`、决策主体仍为仓库维护者，不替其选MIT/Apache或统一许可。

`new_license_granted=false`、`legal_compliance_certified=false`；不认证版权主体链，不是全仓法律审计、律师意见、第三方见证或来源原件真实性认证。

## 离线复核

仅Python 3.9+标准库；不联网、不执行下载内容或旧用例代码，不改文件。默认读取脚本同目录的[观察清单](<observations.json>)与三件镜像，`--root`覆盖的也是**包目录**，不是仓库根。

```bash
python3 -I -S -B '2-用例/上游条款观察-2026-11-05/verify.py'
python3 -I -S -B -O '2-用例/上游条款观察-2026-11-05/verify.py'
python3 -I -S -B '2-用例/上游条款观察-2026-11-05/test_verify.py'
python3 -I -S -B -O '2-用例/上游条款观察-2026-11-05/test_verify.py'
```

[验证器](<verify.py>)检查严格JSON重复键/有限值/精确类型、固定五来源与12响应事实、三镜像内容条件/固定字节SHA，以及四件数据前后读取稳定性；成功stdout JSON/退出0，拒绝退出1。输入仅限指定四个文件名，拒绝路径穿越、祖先/根/文件符号链接及非普通文件；单件上限256KiB。文件系统/标准库/受审源码是信任边界，前后比对不是OS沙箱或抗TOCTOU证明；不验证未公开HTML原字节，不主动访问URL。

[测试](<test_verify.py>)在显式运行时才加载同目录这一个新验证器，不自动discover或导入旧程序。纯结构/关系负例直接改内存对象并调用`validate_document`，与镜像pin负例分层；直接内容负例不经hash门，另核即使改写清单SHA也不能替换固定镜像。精确事实常量和内容短语是本补充的有限合同，不是通用许可证识别器；源码/测试/说明书自身完整性仍需外部冻结SHA，不由这四数据文件检查自证。
