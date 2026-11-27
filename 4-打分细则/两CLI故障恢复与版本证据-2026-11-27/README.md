# 两 CLI 故障恢复与被测版本证据 — 2026-11-27

## 1. 问题与范围

[11-25 命令面](<../两CLI命令面剖面-2026-11-25/README.md>)登记了 Codex 35 条命令中 6 条结构非零、DSH 14 次工具调用（13 bash + 1 read）全为 `completed`。这两个计数不能直接比较：“命令退出”和“调用完成”不是同一个指标。此次复核既有同题公开流，按**结构终态 → 正文故障 → 故障对象 → 恢复/绕行 → 最终被测版本**追索；不重跑产品、命令、解答或 checker，也不以样例自测代替判卷。

## 2. 口径与证据入口

固定 [Codex 原流](<../../3-表现现场/r20261125-five-lcb/codex/stdout-r2.jsonl>) 与 [DSH 原流](<../../3-表现现场/r20261125-five-lcb/dsh/stdout-r2.jsonl>)，SHA256 分别为 `d85c7d724ed4fed1e839aa6fc534cc025cca2288bdc08987d88c73643467be10` 和 `105717eaca150dd36eab255bff74945509a3488837bb1b8df5e143aa337e2508`。C/D 序号是各流内调用编号，**不是行号**。Codex 以同 ID、同完整命令绑定起止；DSH 以 `callId` 绑定调用和回包，正文的 `[exit code: …]` 不充结构退出字段。11 例是事后固定的诊断实例，不是全部失败、独立根因或新增样本。

把日志中明确的候选写入视作数据：只投影固定的带引号 heredoc、可静态还原的常量/切片替换与唯一上下文小补丁，再与公开归档和中间回读比较完整 UTF-8 字节。不能把后继出现、同路径或状态 OK 当作写入成功。投影器不解释通用 shell；空补丁或条件分支需另证，不能仅凭解析器“识别出写入”认证生效。

## 3. 十一条故障怎么恢复

| 既有故障命令 | 结构与正文 | 后继能说明什么 |
| --- | --- | --- |
| [C4](<../../3-表现现场/r20261125-five-lcb/codex/stdout-r2.jsonl#L12-L13>)、[C5](<../../3-表现现场/r20261125-five-lcb/codex/stdout-r2.jsonl#L14-L15>) | 各 exit 1；先缺 C++ 头，改用标准头后又在 SDK 链接失败 | C6 输出 B1..18，[C32](<../../3-表现现场/r20261125-five-lcb/codex/stdout-r2.jsonl#L74-L75>)输出 19/20，合计覆盖 **Python 绕行回包**，不证明 C++/SDK 修复或统计真值。初版漏查 C32，已据原流订正。 |
| [C7](<../../3-表现现场/r20261125-five-lcb/codex/stdout-r2.jsonl#L18-L19>) | exit 130；穷举报告 n2..7 后中断 | 操作者未知；后继随机/小规模验证不补 n8..9。 |
| [C13](<../../3-表现现场/r20261125-five-lcb/codex/stdout-r2.jsonl#L31-L32>) | exit 1；草稿统计对 `None` 调用 `len` | C14 使用别的统计脚本，非原脚本修复。 |
| [C24](<../../3-表现现场/r20261125-five-lcb/codex/stdout-r2.jsonl#L56-L57>) | exit 1；自建 oracle 使用不兼容的 `int.bit_count` | C25 读到 Python 3.9.6；C26 对同一辅助文件改用 `bin(...).count(...)` 后取得四题 OK。这里修的是同一 oracle 的兼容性，不是候选算法。 |
| [C27](<../../3-表现现场/r20261125-five-lcb/codex/stdout-r2.jsonl#L63-L64>) | exit 1；后段 shell 报 `=== not found` | C28 绕开坏的后段命令；[C30 回读](<../../3-表现现场/r20261125-five-lcb/codex/stdout-r2.jsonl#L69-L70>)证实前段源码改写已生效。整体非零不是事务回滚。 |
| [C34](<../../3-表现现场/r20261125-five-lcb/codex/stdout-r2.jsonl#L79-L80>) | completed/exit 0，但 `py_compile` 创建缓存目录有 `PermissionError` | 后继样例/oracle 有实际 OK 文本，不证明缓存权限恢复，也不能仅看 exit 0。 |
| [D7](<../../3-表现现场/r20261125-five-lcb/dsh/stdout-r2.jsonl#L35-L36>)、[D8](<../../3-表现现场/r20261125-five-lcb/dsh/stdout-r2.jsonl#L40-L41>) | 都 completed；原 oracle 出现 `bit_count` 错且正文 exit 1；随后 `sed` 报 `undefined label` | 同对象编辑未证实成功；另起的 Python 脚本得到 389 小规模 OK，是绕行。不能把第二段成功归给 `sed`。 |
| [D10](<../../3-表现现场/r20261125-five-lcb/dsh/stdout-r2.jsonl#L50-L51>) | completed，正文 exit 1；同一命令四次缓存目录权限报错 | 后继能直接运行或比较样例，不等于 `py_compile` 的缓存写权限恢复；四个诊断不是四次独立试验。 |
| [D13](<../../3-表现现场/r20261125-five-lcb/dsh/stdout-r2.jsonl#L65-L66>) | completed；自测包装器将 bytes 与 `text=True` 一起传入，父进程编码失败 | [D14](<../../3-表现现场/r20261125-five-lcb/dsh/stdout-r2.jsonl#L70-L71>)改用字符串，实际打印 11 项 OK。证明同功能的后继包装器绕过该输入错误，没有持久文件身份或子进程未启动证明。 |

固定集外 [C22](<../../3-表现现场/r20261125-five-lcb/codex/stdout-r2.jsonl#L50-L51>)另有 exit 0 下的三个真实样例不匹配，随后才改写。不能把以上故障对象的分类推广成“运行没有算法问题”。

## 4. 最终八件与可见自测链

| 归档程序 | 最后可见写入 | 归档长度 / SHA256 |
| --- | --- | --- |
| [Codex 387F](<../../3-表现现场/r20261125-five-lcb/codex/solutions/abc387_f.py>) | C34 | 1696 / `4ff13ed6cc434da2034e75d125c4eee9fcd33f3a53de2ef3d2b88ec15942bc37` |
| [Codex 388F](<../../3-表现现场/r20261125-five-lcb/codex/solutions/abc388_f.py>) | C34 | 1274 / `d1702fae6ce60470007c3c124509da168ec1fcea7cb9614608d1812074ee8702` |
| [Codex 388G](<../../3-表现现场/r20261125-five-lcb/codex/solutions/abc388_g.py>) | [C23](<../../3-表现现场/r20261125-five-lcb/codex/stdout-r2.jsonl#L53-L54>) | 1441 / `959138871953840a3afaa73ea9578f52f47d2b968f8b2e75ab1ab122d7965b16` |
| [Codex 389G](<../../3-表现现场/r20261125-five-lcb/codex/solutions/abc389_g.py>) | C34 | 3434 / `6abcbda98be451f1999898e2503e5b5086486abb7581e3869f20de4d13cf17fc` |
| [DSH 387F](<../../3-表现现场/r20261125-five-lcb/dsh/solutions/abc387_f.py>) | [D3](<../../3-表现现场/r20261125-five-lcb/dsh/stdout-r2.jsonl#L15-L16>) | 1985 / `f03cfec68342d20c7745ccb88507b3b75372759a02f037b4948800f6386c6a08` |
| [DSH 388F](<../../3-表现现场/r20261125-five-lcb/dsh/solutions/abc388_f.py>) | D3 | 2065 / `7297268ac7abb6c07a0c108c8fa2ae0d56c7acdef120bee6e615c615945b6c9e` |
| [DSH 388G](<../../3-表现现场/r20261125-five-lcb/dsh/solutions/abc388_g.py>) | D3 | 1532 / `9c57caff3eecac28c9627c7e8101b63044e79c77b572ec5ec47ecd3c7cc71d77` |
| [DSH 389G](<../../3-表现现场/r20261125-five-lcb/dsh/solutions/abc389_g.py>) | [D5](<../../3-表现现场/r20261125-five-lcb/dsh/stdout-r2.jsonl#L25-L26>) | 4125 / `e6ac90a8a434a3151d81eca69108f0b5b2e367bca56e68f7076f9dc872ee0615` |

项目内非作者从公开原流独立重做绑定与静态投影：**8/8 最终归档字节相同，C30 四份中间源码和 [D9](<../../3-表现现场/r20261125-five-lcb/dsh/stdout-r2.jsonl#L45-L46>) 一份源码回读也逐字节相同（5/5）**。随后确有可见自测调用和结果：C34 的 `ALL SAMPLES OK` 与自建 oracle 的 `ALL OK`；D14 的 3+3+2+3 条样例 OK。读的是回包文本，不是最后的完成自述或仅看状态码。保留重要限制：两边自测都不是独立真值，一些比较失败路径也不保证非零退出。

## 5. 改变了什么，还不能说什么

- 可以把这八件从“后继出现同名文件”提升到“**可见最后写入、后继自测路径与实际回包、归档字节相符**”。C27/C34 也给出两种相反方向的聚合状态反例。
- 不认证运行瞬间读到的文件描述符、进程哈希或不可见写入；不给这八件打正确分，不做产品优劣或 Harness 因果归因。判卷隔离仍不达标，正式 25 格、历史成绩和旧门不变。
- 此处是项目内非作者复核，**不是受控第三方**。完整公开原流链接可供按行核查；本文公开的是派生结论，不宣称提供了通用的安全回放器。
