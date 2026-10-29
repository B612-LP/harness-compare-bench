# L4 执行封印工具独立合成预审

**局部PASS：v3固定快照的8/8独立检查与作者13/13自测通过。原source/manifest绑定逃逸阻断在该版本解除。** 这不是实际E manifest/source闭包、四runner代码、生产准入消费者或API放行验收；task-7继续in_progress。

live_doc_drift: []（本报告局部工具快照收据；不宣称尚未完成的E代码无漂移）。设计层及R1/R2依据见[design-review](<design-review.md>)。

## 观察与证据

原v1作者6/6绿，但独立发现3项应拒攻击仍生成released=true；v2修复前3项后，新增nested-directory-symlink逃逸仍通过；v3拒绝运行源码树任意symlink节点并将全regular文件纳入封印，独立8项全符合预期。每轮先复制Lead工具/自测至新tmp固定字节，随后只在独立synthetic git仓库运行manifest/bind，从不在真实仓库创建绑定或执行payload。

| 固定版本 | 作者自测 | 独立检查 | 原始收据 |
|---|---|---|---|
| v1 | 6/6、exit0 | 正例过；空files/漏澄清/同字节source软链未拒，exit1 | [作者](<author-seal-selftest-v1.json>) / [首失败](<seal-adversarial-v1.json>) / [快照](<seal-source-snapshot-v1.json>) |
| v2 | 10/10、exit0 | 5/6；nested目录软链逃逸未拒，exit1 | [作者](<author-seal-selftest-v2.json>) / [第二失败](<seal-adversarial-v2.json>) / [快照](<seal-source-snapshot-v2.json>) |
| v3 | 13/13、exit0 | 8/8、exit0 | [作者](<author-seal-selftest-v3.json>) / [独立成功](<seal-adversarial-v3.json>) / [快照](<seal-source-snapshot-v3.json>) |

### v3独立固定用例

1. 完整必需源码集合和真实synthetic git时刻绑定正例。
2. E提交的manifest.files={}必须拒绝。
3. E提交的files省略澄清必须拒绝。
4. E后将required regular source换为仓外同字节symlink必须拒绝。
5. E后新增未封.py helper必须拒绝。
6. 必需gate声明import helpers.payload、helpers目录软链指向仓外payload.py：manifest或bind必须拒绝；payload从不实际执行。
7. E后新增无扩展名helper必须拒绝。
8. E后在runs/workspace生成受评产物代码，不能误当运行基础设施源而拒绝绑定；这不豁免将产物动态导入为runner依赖的真正越界。

## 解释与解除边界

Lead修复对required set/schema/nonempty、安全相对路径、regular/non-symlink、运行树全文件和D/E blob绑定进行了强制。v3自动发现范围缩为tools/runner/driver-snapshot，避免把后续被测产物当未封基础设施。原3项与第二轮目录软链反例均独立复验拒绝，非仅引用作者总结。

因此本预审只解除**已复现source/manifest逃逸**；实际E仍须验证：所有真实入口/动态读取配置/外部profile、第三方驱动快照及加载链均在预期manifest闭包，D/E设计/澄清blob与祖先关系、注册时刻准确，消费者实际执行前重核drift与release，生产未知白名单与失败真值表没有误收。未受测代码后缀、读取路径或动态加载不能据“8/8”推成全程序无逃逸。

## 未排除因素与停止条件

- 合成正例使用假的必需runtime文件，验证封印机制，不执行真实runner、CLI、API或模型，也不读取题库答案。
- 源码树普通缓存被排除，需要实际E运行采用禁止字节码缓存/明确加载来源，不能从未封pycache或外部path导入隐含代码。
- hash/本地git时刻不是数字签名或可信第三方时间戳；工作树发生动态变更仍需执行时检查。实际release决定属于Lead。
- 任一实际E依赖缺封、变更、软链/路径逃逸、非法准入或未授权外发，立即停执行并保留首失败，不用新封条覆盖旧失败。

## 可复现实验

[原创v3检查器](<seal_adversarial_v3.py>)复用[独立synthetic harness](<seal_adversarial_v2.py>)；输出路径必须全新：

```bash
/usr/bin/python3 -B '5-评测报告/L4首请求前评审-2026-10-29/seal_adversarial_v3.py' \
  --source /private/tmp/l4-seal-reviewed-v3-gulv_58p/execution_seal.py \
  --out '<新的review收据路径>'
```

各机器收据保存source SHA、reviewer脚本SHA与异常/绑定详情；tmp快照可能清理，其源版本可依SHA与仓库修复链追溯。作者测试与独立检查各为一次self_test命令，不按13或8断言数计产品运行。无真实API，无真实仓库git提交，无builder代码改动。

## 脚本生成证据行

```text
5-评测报告/L4首请求前评审-2026-10-29/seal-source-snapshot-v3.json · 6fb08b79 · 584B · 2026-10-29T20:21:47+08:00
5-评测报告/L4首请求前评审-2026-10-29/seal_adversarial_v3.py · c8db836c · 3884B · 2026-10-29T20:21:47+08:00
5-评测报告/L4首请求前评审-2026-10-29/seal-adversarial-v3.json · 72bd706e · 4548B · 2026-10-29T20:21:47+08:00
5-评测报告/L4首请求前评审-2026-10-29/author-seal-selftest-v3.json · 8a296288 · 1477B · 2026-10-29T20:21:47+08:00
```
