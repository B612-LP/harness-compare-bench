# lcb-recent-hard-4 判卷器审计与 oracle 恢复收据(2026-10-26)

## 范围与结论

- 对象:`2-用例/lcb-recent-hard-4/checker.py`(v0.1,与 judge-staging 副本 SHA 一致 `e07654d42450…`)。
- 结论:**自测 11/11 全绿**(正例 2、负例 8、守卫/ERROR 1),原始输出见
  [selftest-2026-10-26.stdout.txt](<selftest-2026-10-26.stdout.txt>);
  负例含「只过公开样例不过私有」(每题首个失败点=公开测试数,逐题验证)、
  超时死循环 fail_kind=timeout、输出格式多空格、输入副本篡改被 input_integrity 拦截、truth SHA 漂移 exit2。
- 本次为**审计与证据恢复**,无模型重跑、无改分、无 git commit;不新增独立运行样本数。

## oracle 恢复(staging `solution/`,私有,不入仓库正文)

checker `--selftest` 依赖 `staging/solution/<pid>.py` 四题 oracle。恢复前该目录缺失(与 inputs/problems.json 同期遗失)。恢复与实证:

| 文件 | 性质 | 出处与实证 |
|---|---|---|
| abc387_f.py | 真实解 | 元宝 r1031 会话 0RXLHr0Aocq;组装临时 run_dir 过 checker:43/43 |
| abc388_f.py | 真实解 | 元宝 r1030 胜者;同法实证 43/43 |
| abc388_g.py | 真实解 | 元宝 r1031 会话 0RXLIyBTM5g;同法实证 42/42 |
| abc389_g.py | **truth 重放夹具(非真实解)** | 全盘无真实解(见下);文件头显式披露,仅用于判分管路自检 |

哈希全录 [oracle-sha256.json](<oracle-sha256.json>)。

## 过程发现(影响台账,已另行落账)

1. **豆包 r1026 的 abc389_g 真解在归档时丢失**:r1026 现场仅存 matrix,工作区未归档;
   r1029 豆包另一次运行的 389_g 解经 checker 实证仅 3/43(=公开样例数,即只对样例)。
   → 未知登记新增 `lcb-389g-oracle`。
2. **truth 未变证据**:repo truth.json mtime 2026-10-22 20:43(早于 r1026 全部运行),
   与 staging 副本逐字节一致 → 历史 lcb 分数与现行隐藏测试可比。
3. **元宝专家模式默认联网检索题解(integrity_scan-v1 机器复核发现,人工终审确认)**:
   - r1030 `abc388_g`(42/42 得分题):会话 0RXBtdJegT2 内 web_search「ABC388 G 题解」,
     命中 gdst.dev/cnblogs 题解页,提交解正是该会话产出 → **r1030 判 suspect/X,干净口径 50 分**;
   - r1030/r1031 `abc389_g`(0/43):两轮均检索至少 8 篇题解(vjudge/cnblogs/个人博客)后仍 0/43
     → 反向坐实能力墙;
   - r1031 三个得分题会话(387_f/388_f/388_g)无检索痕迹 → **r1031 = 50 分为元宝干净口径**;
   - r1029 WorkBuddy×lcb 再次命中 web_search×7 + luogu 题解页(与 r1026 被判 X 同类)→ suspect/X。
   扫描报告(过程材料,仓外):`~/bench-automation/runs/integrity-scan-2026-10-26.json`;
   豁免与误报裁定:exercism/bird 的 GitHub 链接=题面原文;workbuddy×dabstep 的 web_search 命中=
   Bash 本地脚本误报(无 http/curl);bird 的「spec.md 提及」=任务书自述。

## 引用

- 判卷器修复方法论:同目录 [execution](<../execution/README.md>)、[numeric](<../numeric/results.json>)。
- 未知台账:`5-评测报告/未知登记.json`(lcb-389g-oracle、b-group-websearch-policy)。
- 运行总账:2026-10-26 补录 r1029-desktop-auto(10 场)/r1030(1 场)/r1031(1 场),含本轮 integrity 裁决。
