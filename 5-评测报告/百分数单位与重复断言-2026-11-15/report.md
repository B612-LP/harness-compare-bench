# 百分数单位与重复断言：q62 的固定库离线分解

## 观察

既有 W 轨三次重复的 q62 判定为 false/true/true，加权分为 93.33/100/100；不是新产品样本。r1 的最终答案选择 18% 口径，r2/r3 选择 0.18% 口径，同时表与过滤字段也改变。本次补齐研究者独立构造的四格，**只在这份固定数据库上，命中行集的 200 行差可以由单位步骤分解；表/过滤步骤及交互均为 0**。这不是两表一般等价或 Harness 因果结论，正式 25 格、历史得分及金标均不改。

| 表及过滤面 | 18%：`free * 1.0 / enroll < 0.18` | 0.18%：`CAST(free AS REAL) * 100 / enroll < 0.18` |
|---|---:|---:|
| F：frpm 的 County Name、Charter School (Y/N) | 201 | 1 |
| J：schools 内连 frpm，以 schools.County、Charter 过滤 | 201 | 1 |

两面均取 Los Angeles、Charter=0；不附加 Active 条件，不使用存储的 Percent 字段。

## 证据

- 题面明示 0.18% 及 `free * 100 / enroll`，见[题面:33–42](<../../2-用例/bird-ca-schools-15/inputs/questions.json#L33-L42>)；当前[金标:50–52](<../../2-用例/bird-ca-schools-15/truth.json#L50-L52>)使用 CAST REAL、J 过滤及 COUNT(School)。既有[断言差分:73–76](<../断言级重复性-diff-2026-11-02/r20261101-wb-n3-assertion-diff.json#L73-L76>)及三份公开收据 [r1](<../../3-表现现场/r20261101-wb-n3/runs/bird-ca-schools-15/run-bird-ca-schools-15__r1.json>)、[r2](<../../3-表现现场/r20261101-wb-n3/runs/bird-ca-schools-15/run-bird-ca-schools-15__r2.json>)、[r3](<../../3-表现现场/r20261101-wb-n3/runs/bird-ca-schools-15/run-bird-ca-schools-15__r3.json>)保留原分。
- [最小派生证据](<evidence.json>)只收录答案形式、既有断言、必要可见语句与匿名槽位来源哈希。当前三槽答案/输入与 after 的哈希一致，execution 指向当前 after，公开收据指向当前 execution，轨迹 session ID 一致；槽内 DB/questions/schema 与 canonical 字节相同。它认证的是**当前文件链的吻合**，不认证完整历史执行或导出原件真实性。
- [确定结果](<results.json>)保存四格命中行键与 COUNT。行键为 `SHA256("q62-row-v1:" + CDSCode)`：由公开库可重算的去标识派生，不是不可逆隐私承诺。F/J 同单位的双向行集差均空，排序多重集也相同。两条有序路径 F18%→J18%→J0.18% 为 `[0,-200]`，F18%→F0.18%→J0.18% 为 `[-200,0]`；差中差交互为 0。
- 四格 COUNT(*) 与 COUNT(CDSCode) 各为 201/1/201/1；J 两节点 COUNT(School) 为 201/1，School=NULL 命中集均空。**F 没有 School，记 null/不可用，不记 0。**因此 COUNT 对象不是三次候选之间的变化量；它与金标的语义差在本次命中集上没有数量贡献。
- 过滤前 F=1866、J=1865，已说明两过滤面并非一般等价。各有 3 行 free=NULL，enroll=NULL/0 均 0，公式值为 NULL 的各 3 行不命中；两公式在各过滤面恰等于阈值的行数均 0。F 实际 typeof 为 REAL/REAL 1863、NULL/REAL 3，J 为 1862/3；全 frpm 为 9986 行（REAL/REAL 9930、NULL/REAL 56）。全库连接缺学校键 0、县名差 0，但 Charter 以 `IS NOT` 作 NULL 安全不等比较时有 7 行不同，不能由命中集相同外推两表全库一致。三次候选中的未 CAST `free*100/enroll`，在此固定库上与 CAST 版本的完整记录相同。

## 解释

研究前只有三个已定位的数值节点，不能排除第四格的表交互。现在第四格及行集均已实际核实，支持**固定库内的单位数值分解**，不是只凭 201=201 推断行集相同。

过程层面比“漏乘 100”更具体：r1 可见文本先写 `ratio<0.0018`，随后明确选择 `I'll use f.FreeMeal*1.0/Enrollment < 0.18`；最终答案吻合此选择。r2 同样犹豫，但以 `evidence explicitly gives the formula` 收口并写 `Going with 1 (the *100 version)`；r3 按 *100 口径写出 count=1。故可描述为：**三槽可见决策中，r1 对预期 gold 的猜测压过了已理解的当前定义，另外两槽选择当前 evidence。**这些是导出文本中的优先顺序与最终产物关系，不是隐藏思考的全部因果真相，也不证明其所称上游 gold 或训练记忆真实。

## 未排除

本分析是既有数据的事后探索，三个会话没有重新控制实际思考量、缓存、模型后端或输入运行时状态。n=3 不能估普遍随机性、未来成功率或某产品的稳定机制；当前哈希链不能弥补缺失的独立历史见证。可见 reasoning 可能不忠实于内部计算，不能称评分投机、记忆污染事实或 Harness 故障。未访问或认证所谓官方上游 gold，也未执行候选 SQL/Python 或历史 checker。

负分支仍真实可达：[内存反例结果](<controls.json>)中，School=NULL 令 COUNT(*)=1、COUNT(School)=0；Charter 冲突或缺 join 键令 F/J 不同；相反方向的两个 Charter 冲突令计数相同而行集不同；INTEGER 的 `free*100/enroll` 可截断，与 CAST REAL 不等。NULL/零分母按 SQLite 产生 NULL，不当作零餐数。另有严格等值与相邻浮点边界、numeric TEXT、无效 TEXT、负数探针：验证器忠实报告 SQLite 运算，不冒充数据清洗或一般业务合法性证明。缺完整矩阵时分支为 unknown，绝不填 0。只有本固定库的实际类型与命中行集支持当前数值结论。

## 复核

Python 3.9+、仅标准库；在本目录执行：

```sh
python3 -B verify.py
python3 -B -O verify.py
python3 -B test_verify.py
python3 -B -O test_verify.py
```

[验证器](<verify.py>)自行构造研究 SELECT，只以 SQLite URI `mode=ro&immutable=1` 打开 canonical 静态用例库，设置 query_only 并以 authorizer 限定 SELECT/READ/FUNCTION/RECURSIVE；不打开任何活跃产品数据库。源哈希在查询前后核对，源缺失/变化直接 fail closed。内存反例只写临时 `:memory:`，不写文件；完整结果按 JSON 类型敏感比较，`1`、`1.0`、`true` 不互换。[测试](<test_verify.py>)覆盖 14 组，含独立于单位结论的“同计数异行集”近错及直接严格边界探针，普通与 -O 均已通过；软件测试数不是产品样本数。

[SHA 清单](<SHA256.json>)绑定报告、两类证据、验证器和测试；清单自身的可信锚须由外部保存，不能自证历史真实性。公开复核只验证固定库重算与派生关系，必要可见语句的原件真实性、完整轨迹、隐藏状态仍不在其认证范围。本目录是有限离线解释补充，不修改旧页或历史判分；非作者验收与整合状态由外部另记，作者不自署独审通过。
