# corpus-squeeze 判分规格（spec）

版本：**v0.1（2026-10-22，轻量判卷）** ｜ 判分入口：`checker.py`
定位：**hard · RE-Bench 风格迭代优化题**（受限压缩达标），与 `int-sum-sort` / `word-freq-report` 的产物直出题互补。

## 1. 用例定位

投喂 `inputs/corpus.txt`（204,180 字节中英混合语料，固定落盘），要求产品在运行目录交付 `compressed.bin` + `decompress.py`，同时满足：字节级 roundtrip、压缩率 ≤ **THRESHOLD=0.35**、解压器多重静态约束（≤8KB、stdlib 白名单、禁 zlib/lzma/bz2、只读 argv[1]）。
测的不是「一次答对」，而是**写 → 自测 → 调优 → 再验证**的任务链：实现自定义二进制格式与位级编解码、满足四重约束、迭代到达标。用户反馈既有候选「太简单」，本题与 jielong-fullchain / ledger-replay 同批补区分度。

## 2. 判分模式

- **headline 为二值 0/1**（`BINARY=True`：全 PASS=1，任一 FAIL=0）。
- 逐项权重只用于复核定位与加权参考；partial 口径 = `weighted/100×10`（单题上限 10）。ratio 项未达标但已压缩时按达标程度给部分 credit（见 §3），不影响二值口径。
- 三个守卫：**输入完整性**（附带的 corpus.txt 被改 → 直接 0）、**truth 交叉校验**（SHA-256 / 长度 / threshold 任一漂移 → 启动即 ERROR，退出码 2）、**静态约束扫描**（不满足 → 0）。

## 3. 观察项

| id | 观察项 | 权重 | 通过条件 | 0 分条件 |
|---|---|---:|---|---|
| artifacts_exist | 产物存在 | 10 | `compressed.bin` 与 `decompress.py` 均在约定位置 | 任一缺失（其余项连带「无法检查」判 fail） |
| input_integrity | 输入完整性（守卫） | 10 | 运行目录附带的 `corpus.txt` 与 canonical 字节一致 | 被修改（直接 0）；未附副本 → **未核验**（不扣分） |
| decompress_constraints | 解压器静态约束 | 15 | 见下方约束清单全部满足 | 任一不满足 |
| roundtrip | 还原一致性 | 40 | `python3 decompress.py compressed.bin`（subprocess，cwd=run_dir，stdin=/dev/null，**超时 60s**）exit=0 且 stdout 与 canonical 语料**逐字节相等** | 非零退出 / 输出不一致 / 超时 |
| ratio | 压缩率 ≤ 0.35 | 25 | `len(compressed.bin)/len(corpus) ≤ 0.35`（float 比较 +1e-12 容差） | 超标；credit 按达标程度线性给：`credit = 25 × max(0, (1−ratio)/(1−0.35))` |

**静态约束清单**（decompress.py 源码字节级/AST 级）：

1. 大小 ≤ **8192 字节**（8KB）；
2. import 白名单：`sys io math heapq collections itertools functools struct array bisect string types typing argparse json re base64 binascii time`——白名单外一律 FAIL（故意排除 os/pathlib/subprocess 等有文件/进程能力的模块；`gzip` 因包装 zlib 同样被排除；相对 import 拒绝）；
3. 源码（含注释）不得出现 `zlib` / `lzma` / `bz2` / `corpus` 字样（大小写不敏感）；
4. 所有 `open()` 调用（含属性形式）第一参数必须 unparse 为 `sys.argv[1]` 或其直接别名变量（`x = sys.argv[1]` 赋值过的 Name）；未调用的死代码同样拒绝；
5. 禁止 `eval` / `exec` / `compile` / `__import__` 调用（防动态绕过静态扫描）。

## 4. 运行目录约定

```
<run_dir>/
  compressed.bin   # 必需产物（也接受 run_dir/output/、run_dir/outputs/ 下同名文件）
  decompress.py    # 必需产物（同上）
  corpus.txt       # 可选，建议附：本次实际使用的语料副本（用于完整性守卫）
  meta.json        # 可选：产品/版本/模型/操作人/日期/迭代日志等，不参与判分
```

```bash
python3 checker.py <run_dir>          # 人读报告 + RESULTS_JSON
python3 checker.py <run_dir> --json   # 只输出 JSON（供脚本聚合）
python3 checker.py --selftest         # 负控制/守卫自测，必须全 PASS 才可用于正式评分
```

退出码：`0` = reward 1；`1` = reward 0；`2` = 用法错误 / 自测失败 / 用例自身不一致（truth 漂移）。

## 5. 判卷器自测（三纪律）

1. **验外部产物**：只读运行目录文件 + 实跑解压器 subprocess，不采信产品自述。
2. **负控制必须能变红**：`--selftest` 固定 12 组样例（2 正 + 10 负），负例带失败项精检（`failed` 列表必须精确匹配，防止「错原因红」冒充通过）：
   - golden：R2 参考解全流程产物 → 1；未附输入副本 → 1（未核验不扣分）；
   - 空目录 / 只放 bin 缺解压器 → 0；
   - **R1 朴素解产物 → 0 且 `failed == ["ratio"]`**（负对照：其余四项必须全过，证明判分器是按 ratio 拒绝它）；
   - bin 截断（去尾 64B）/ 篡改 1 字节（token 区 flip）→ 0 且含 `roundtrip`；
   - decompress.py 超 8KB / 尾部 `import zlib`（roundtrip 仍过、仅静态扫描红）/ 尝试 `open('notes.txt')`（死代码也拒绝）→ 0 且 `failed == ["decompress_constraints"]`；
   - 变体语料的 R2 产物（roundtrip 不匹配 canonical）→ 0 且含 `roundtrip`；
   - 附篡改输入副本 → 0 且 `failed == ["input_integrity"]`。
3. **用例自身一致性**：truth.json 记录 canonical 语料 SHA-256、字节数、threshold；checker 启动即校验，任一漂移报 ERROR 退出码 2。

**修改 checker 后必须重跑**：`--selftest` 全绿 + §6 oracle 回归。

## 6. oracle 回归

```bash
# 正对照：R2（LZ77+Huffman，stdlib-only）→ 必须 reward=1
python3 solution/r2_huffman.py inputs/corpus.txt /tmp/oracle_r2
cp inputs/corpus.txt /tmp/oracle_r2/
python3 checker.py /tmp/oracle_r2            # REWARD 1（实测 2026-10-22：ratio 0.2303）

# 负对照：R1（朴素 RLE）→ 必须 reward=0 且 failed=["ratio"]
python3 solution/r1_naive.py inputs/corpus.txt /tmp/oracle_r1
cp inputs/corpus.txt /tmp/oracle_r1/
python3 checker.py /tmp/oracle_r1            # REWARD 0，WEIGHTED 75/100
```

两个参考解各自把独立解压器写进 run_dir 的 `decompress.py`，与真实产品交付形态完全一致；R2 解压器 2,350 字节（上限 8,192），压缩/解压实测均 < 0.2s（超时余量 300 倍以上）。

## 7. 难度论证（为什么这是 hard）

1. **不能一次答对**：roundtrip 字节级一致 + ratio ≤ 0.35 + 四重静态约束必须同时成立。初版实现的高频死法——位流 padding 错位、canonical 码表编解不一致、匹配距离越界（overlap 拷贝）、高熵段拖垮压缩率、解压器超 8KB——每一类都需要「自测 → 定位 → 改格式 → 再验证」循环才能消掉，单轮问答式 harness 会在第 2~4 轮暴露。
2. **捷径全被独立项拦截**：改语料再压缩 → input_integrity；运行时外读语料 → 静态 open 扫描 + `corpus` 字样禁令；用 zlib/gzip → import 白名单 + 字样禁令；贴一个大字典进解压器 → 8KB 上限（8KB 字典最多覆盖 4% 语料，math 上不可能达标）；乱编格式 → roundtrip。
3. **量化区分度**：朴素解 ratio 1.0006、纯 order-0 Huffman 0.8060 均被拒，真 LZ77+熵编码 0.2303 过线——判定线落在「是否真的实现了压缩算法」上，而不是参数调优。对照同批两题（对话链路完整重放 / 账本重放），本题考**工程迭代闭环**，三种失败模式不重叠。

## 8. 行为锚点（人工跑时记 0–3，自动批跑记 N/A）

| 观察项 | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| 自测 roundtrip | 无自测，直接交付 | 跑过一次，失败未修复就交付 | 有自测且修复过问题 | 完整 write→test→fix→re-verify 链路，留有命令/日志证据 |
| 报告压缩率 | 未报告 | 只报了文件大小 | 报了 ratio 数值 | ratio + 与阈值的余量 + 各迭代版本对比 |
| 失败后重试 | 无迭代/静默放弃 | 单次盲目重试 | 有方向性调整（换/调算法或格式） | 多轮迭代且每轮由实测数据驱动（哪项指标差、改了什么、复测结果） |

## 9. 语料构成与阈值校准记录（2026-10-22）

**语料**：`environment/tools/gen_corpus.py`（SEED=20261022）确定性生成，只使用文档保证跨版本稳定的 `random.Random.randrange`，同种子重跑字节一致（实测两次 SHA-256 相同：`e2305230…99f5`，204,180 字节）。构成与分段压缩率（zlib -9 参照，仅校准用）：

| 段 | 字节数 | 内容 | zlib -9 分段压缩率 |
|---|---:|---|---|
| A JSON 行流水 | 33,926 | 结构化键值行 | 0.175 |
| B 管道表格 | 13,550 | 巡检表格 | 0.212 |
| C 伪代码段 | 25,948 | 同构函数群（高冗余） | 0.098 |
| D 中英自然段 | 102,934 | 运营日志（中文 UTF-8 + 英文） | 0.113 |
| E 高熵随机流 | 27,727 | base64(随机字节)，防「全冗余随便压」 | 0.764 |

整体参照：zlib -9 = **0.2187**；order-0 熵 6.412 bits/byte，纯 order-0 Huffman = **0.8060**（字节分布平、冗余在 n-gram 层，单靠熵编码远不够——这是禁 zlib 后必须做 LZ 的原因）。

**校准数据**（2026-10-22，python 3.9.6 本机实测）：

| 解 | 脚本 | 实测 ratio | 相对 THRESHOLD=0.35 | 判定 |
|---|---|---:|---|---|
| R1 朴素 PackBits RLE | `solution/r1_naive.py` | 1.0006（204,301 B） | 超标 185.9% | **FAIL**（负对照，failed=["ratio"]） |
| 纯 order-0 Huffman（无 LZ，测量用一次性脚本） | — | 0.8060 | 超标 130.3% | FAIL |
| R2 LZ77+canonical Huffman | `solution/r2_huffman.py` | 0.2303（47,028 B） | 余量 34.2% | **PASS**（oracle，reward=1） |
| zlib -9（参照，**不允许**用于解题） | — | 0.2187 | — | — |

**选择：方案 A（禁 zlib/lzma/bz2，自实现压缩），THRESHOLD = 0.35 写死进 checker 与 truth。**
依据：① R2 余量 34.2%，远超 ≥5% 要求，覆盖诚实实现间的差异（更弱的自研 LZ/熵编码组合到 0.35 仍可过线）；② R1 与纯 Huffman 被大幅拒收，判定线精确落在「是否实现了真压缩算法」；③ 高熵段占比 13.6% 奠定可达下限（E 段 zlib 后仍占整体 0.098），0.35 不会逼出不可达目标。

**否决方案 B（允许 zlib，阈值 = zlib -9 实测再低 8% ≈ 0.2012）**：0.2012 低于自实现 R2 的 0.2303，会把诚实的自研实现连同 zlib 一起拒在门外；且允许 zlib 后一行调用即得 0.22，题目退化为「调库 + 调参」，失去迭代调优维度。二选一，取 A。

## 10. 变更记录

- 2026-10-22 v0.1：首版入库。语料/gen_corpus.py/r1_naive.py/r2_huffman.py/checker.py/truth.json/instruction.md；`--selftest` 12 组（2 正 + 10 负）全绿；oracle reward=1（ratio 0.2303，余量 34.2%）；R1 负对照 reward=0（仅 ratio 变红）；truth 漂移守卫退出码 2 实测通过。THRESHOLD=0.35（方案 A）。
