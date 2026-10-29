#!/usr/bin/env python3
"""Generate the five-part independent report from saved measurements; never rewrites it."""
import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('evidence_line',ROOT/'1-评测方案/工具链/evidence-kit/evidence_line.py')
ek=importlib.util.module_from_spec(spec);spec.loader.exec_module(ek)
r=json.loads((OUT/'independent-check-02.json').read_text());snap=json.loads((OUT/'input-snapshot-01.json').read_text())
def link(rel,label=None):
    p=Path(rel);p=p if p.is_absolute() else ROOT/p
    return '['+(label or p.name)+'](<'+str(p.relative_to(ROOT))+'>)'
def own(n,label=None):return link(OUT/n,label)
diff=r['differences'][0]['detail'];a1=r['aborted_archives']['E1'];a2=r['aborted_archives']['E2'];commits=r['binding']['commits']
paths=[OUT/'independent-check-02.json',OUT/'independent-check-01.json',OUT/'whitelist-negative-receipt-01.json',OUT/'input-snapshot-01.json',OUT/'reproduction-run-summary-02.json']
paths += [OUT/(n+'-reproduced-receipt-02.json') for n in ('r4-acceptance','r4-history','r5-mapping')]
paths += [OUT/(n+'-run-02.json') for n in ('r4-acceptance','r4-history','r5-mapping')]
paths += [OUT/'whitelist-negative-run-01.json']
paths += [OUT/n for n in ('prepare_review.py','guarded_run.py','run_reproductions.py','independent_verification.py','finalize_verification.py','whitelist_negative.py','build_readme.py')]
paths += [ROOT/'1-评测方案/自动循环L5-2026-10-30'/n for n in ('execution-manifest.json','runtime-binding.json')]
paths += [ROOT/a1['path']/'abort-receipt.json',ROOT/a2['path']/'abort-receipt.json',ROOT/a2['path']/'abort-receipt-supplement.json',ROOT/a2['path']/'abort-receipt-supplement-2.json']
evidence=ek.gather([str(p) for p in paths],ROOT,ek.now_local())
text=f'''# L5 干净临时环境独立复核（task-16）

分类：离线复算 / 判卷回归；不计产品运行、裸模型探针或接口预检。审计者 independent-reviewer；写界仅本目录。

## 一、观察

**复核完成，非全过：{r['passed']}/{r['check_count']} 项成立；保留一项真实的 E2 档案自哈希不符。** 本次零模型、零网络、零产品 CLI/判卷器执行。所调用判卷准入模块是离线规则判断，不是题目 checker。

| 要求 | 独立结果 |
|---|---|
| R4 正例 / 近似错误例 | 原样脚本复跑 exit 0；8 个断言与在档收据逐项一致，其他有效 JSON 字段完全一致 |
| R4 历史复算 | 17 个唯一计划槽 / 4 个断言；逐字段等于在档收据；唯一投影差异仍是 bird 白名单 fail 消失，formal 仍为 0/17 |
| R5 映射复算 | 18 槽、28 个断言（含 responses erratum 逐槽比对）、另 6 个单元例全部一致；完整 raw/mapping/normalized 视图一致，别名不相加 |
| E3 绑定 | D/E3/磁盘三份原件逐字节一致；独立枚举 {len(r['binding']['manifest_files'])} 个仓内源与 17 个 external pins；源码 E3 blob/磁盘/manifest 三方 SHA 一致；registered_at 精确等于 E3 committer 时刻 |
| 中止档案 | E1 {a1['listed_count']} 项 + E2 {a2['listed_count']} 项，全量核 {a1['listed_count']+a2['listed_count']} 项 SHA；213 项匹配、1 项自引用不符；两份文件清单均无缺漏；两份 supplement 已对账 |
| 自选负例 | 恰 1 个大小写绕过 `Registrations`，加恰名 `registrations` 正对照；8 个细分判断成立，绕过仍 fail，score 保持 null |
| 输入保护 | {len(r['protected_inputs'])} 项受保护输入（含复跑收据与外部原件）最终重哈希无变化 |

唯一真实差异是 {link(ROOT/a2['path']/'abort-receipt.json','E2 中止主收据')} 的 `files_sha256["abort-receipt.json"]`：记录的 SHA 为 `{diff['expected_sha256']}`，当前原件实算为 `{diff['actual']['sha256']}`，{diff['actual']['bytes']:,} bytes。该自引用不满足“当前字节等于表内 SHA”，**未豁免、未改写原收据、未记作通过**；其余 213 项的实际原件与记录相符。这不等于所有中止证据均无效，也不能说档案全哈希通过。

## 二、证据

- 主机器收据：{own('independent-check-02.json')}；其中完整列出逐断言比较、每个 E3 源 / external pin、214 项归档核验、Git 只读命令及其输出哈希、输入起止 SHA。
- 首次机器收据：{own('independent-check-01.json')}，连同 {own('independent_verification.py','首次独立程序')} 原样保留；最终说明见 {own('finalize_verification.py')}。首次 11 个 false 中 10 个来自审计者把准备态 null 错当已绑定运行值；另 1 个即上述真实自哈希差异。五份 Codex 准备模板的十个字段明确为 null，不补值、不当已登记证据；实际 claim / run 中的已知封印及时间另与 Git committer 实测核对。
- 原样复跑：{own('r4-acceptance-reproduced-receipt-02.json','R4 8 断言')}、{own('r4-history-reproduced-receipt-02.json','R4 17 槽历史表')}、{own('r5-mapping-reproduced-receipt-02.json','R5 18 槽映射')}。唯一允许的比较差异是脚本生成时刻，以及 R5 `scope` 从原工作树到临时树的精确绝对前缀替换；没有归一化掉状态、fails、SHA、得分或 usage 值。
- 环境与副本：{own('input-snapshot-01.json')}、{own('reproduction-run-summary-02.json')}。固定副本 {snap['file_count']} 个文件、{snap['bytes']:,} bytes；独立临时根 `{snap['temporary_root']}`。源码脚本与原件逐字节相同，未执行 builder、模型、产品或题目 checker。
- 负例：{own('whitelist-negative-receipt-01.json')}。恰名目录通过；大写目录明确产生目录额外文件 fail，record_valid=false、formal=false，未被错误列为白名单证据。

只读 Git 实测（没有 git 写态命令）：

| 标识 | 完整 commit | committer 时间 |
|---|---|---|
'''
for n in ('D','E1','E2','E3'):text+=f"| {n} | `{commits[n][0]}` | `{commits[n][1]}` |\n"
text+=f'''
D → E1 → E2 → E3 → 核验时 HEAD 的祖先链全部成立，committer 顺序不倒退；E1/E2 中止事件位于各自 seal 之后及下一 seal 之前。已知原 claim/meta 时间与对应 commit 时间一致；E2 目录中的 E3 作废 claim 按 {link(ROOT/a2['path']/'abort-receipt-supplement-2.json','supplement 2')} 明确视为 E3，不冒充 E2 运行。准备态 null、目录名时间及文件系统 mtime 均不被拿来补造 registered_at。

当前 {link('1-评测方案/自动循环L5-2026-10-30/runtime-binding.json','E3 binding')} 记载且独立实算相符的 manifest SHA 为 `{r['binding']['manifest_sha256']}`；以这一绑定值而非任务提示的截断示例为准。

标准证据行（下述代码块由原 evidence_line 工具生成；路径 / SHA / 字节 / 时刻均非手填）：

```text
'''
text+='\n'.join(x['line'] for x in evidence)
text+='''
```

## 三、解释

R4/R5 的在档结论已由独立进程对同样字节输入复现，不是直接采信实现者总结。R4 修订修复的是 not_executed 目录白名单记账，不能把 formal=false 改成通过；R5 修订修复的是映射覆盖，不代表新增任何模型请求、cache 收益或经济成本结论。

“干净环境”在这里的精确定义是：全新临时输入树 / cwd、最小化显式环境、Python 隔离模式与禁止写 pyc、OS `deny network*`，原件不可写，Python 仅准只读 Git 子进程。为了验证历史封印中的绝对外部路径，HOME 明确保留；不是空 HOME、容器或异机。OS 拒读该 HOME，除仓库及逐一枚举的 external pin；CPATH / SDKROOT 等系统 Python 启动注入键在运行收据中可见，未冒充完全空环境。只读取明确的外部文件做字节哈希，未解码任何凭据正文。

`live_doc_drift=[]` 仅表示审计起止输入没有变化，**不表示已有自哈希矛盾不存在**。最终主收据退出码 1 是这一保留差异，不是 R4/R5 复跑失败。

## 四、未排除因素

1. E2 自引用记录的哈希不是当前主收据哈希：影响是不能宣称整个归档自校验全过；下一步如需修正，应由授权所有者新建外置、不可覆盖的更正侧车并注明所指版本，不能为了自指固定点而重写原表；停止条件是出现其他文件 SHA 漂移或新旧版本无法区分时，不继承本意见。
2. E3 仅验证显式源 / 配置 / 构建 pin，manifest 明示并未锁完整传递产品依赖。影响是不能推出整个主机、供应商内部实现或运行语义已冻结；下一步只有在新增代码 / 依赖 / pin 后重新审查；任一现有 pin 变动即停止继承本次绑定意见。
3. Git 时间与文件时间属于本机记录，不是 NTP 或外部可信时间戳。这里只能支持已列 seal、已知 registered_at 与中止事件间的一致性；需外部时钟结论时应另取授权证据，不能以本复核替代。
4. 中止两批的真实消耗在原档案中已明确披露。本次只核字节与已列元数据，不重建 HTTP 尝试分母、不证明进程组历史停止、不证明所有 trace 的语义完整或无污染；不可用本复核恢复 formal、回填 usage，或把未计计划槽解读为未发生消耗。
5. 此处一项大小写负例是规定的抽测，不是完整安全证明，也不推广成所有路径 / 软链 / 损坏 JSON 都已覆盖。

## 五、可复现实验

入口程序按固定相对布局识别仓库。复制到同样布局的独立工作副本并使用全新输出路径后，依次运行：

```sh
/usr/bin/python3 -B '5-评测报告/L5独立复核-2026-10-30/prepare_review.py'
/usr/bin/python3 -B '5-评测报告/L5独立复核-2026-10-30/run_reproductions.py'
/usr/bin/python3 -B '5-评测报告/L5独立复核-2026-10-30/independent_verification.py'
# whitelist_negative.py 须按 guarded_run + 同一 deny-network SBPL 运行；完整调用已在工具运行日志保留。
/usr/bin/python3 -B '5-评测报告/L5独立复核-2026-10-30/finalize_verification.py'
/usr/bin/python3 -B '5-评测报告/L5独立复核-2026-10-30/build_readme.py'
```

现有输出均 exclusive create，直接原地复跑会拒绝覆盖；不得删除原证据来“清理失败”。复现结果应仍为三脚本 exit 0、逐断言一致、大小写负例拒绝，以及同一 E2 自引用差异；若输入变了，明示新差异，不得套用旧 PASS。

第一次三项包装器 exit 1 的 stdout/stderr 已保留：审计者的初版 SBPL 把中文输出目录编码为 JSON ASCII 转义，未匹配真实路径，导致包装器写运行收据被拒。后续只修审计策略的 UTF-8 路径表达，未改变被测源码或原件。另一次审计者准备态 null 判断失误的首程序 / 首收据亦完整保留；这些不得归咎于 gate 产品缺陷或抹掉真实自哈希问题。

live_doc_drift=[]
'''
with (OUT/'README.md').open('x',encoding='utf-8') as f:f.write(text)
with (OUT/'evidence-lines-01.json').open('x',encoding='utf-8') as f:json.dump({'generated_at':ek.now_local(),'items':evidence,'live_doc_drift':[]},f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'report':str((OUT/'README.md').relative_to(ROOT)),'evidence_lines':len(evidence),'status':r['status']},ensure_ascii=False))
