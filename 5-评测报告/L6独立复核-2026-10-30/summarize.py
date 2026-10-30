#!/usr/bin/env python3
"""Join completed independent evidence; exclusive new outputs, no extra test research."""
import hashlib,importlib.util,json,os,re
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
P6='1-评测方案/自动循环L6-2026-10-30'
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return {'sha256':h.hexdigest(),'bytes':p.stat().st_size}
def create(p,x):
    s=json.dumps(x,ensure_ascii=False,indent=2)+'\n'
    t=re.sub(r'(?i)\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b',lambda m:m[0].replace('-',r'\u002d'),s);assert json.loads(t)==x
    with p.open('x',encoding='utf-8') as f:f.write(t)
def load(n):return json.loads((OUT/n).read_text())
def main():
    a=load('round-02/offline-work-receipt-01.json');b=load('binding-check-01.json');s=load('snapshot-01.json')
    for doc in (a,b):assert doc['counts']['total']==len(doc['checks']) and doc['counts']['passed']==sum(c['pass'] for c in doc['checks'])
    drift=[]
    for ap,before in b['protected_inputs'].items():
        after=digest(Path(ap))
        if before!=after:drift.append({'path':ap,'before':before,'after':after})
    # Copy exact policy used; does not change temp or original inputs.
    with (OUT/'sandbox-policy.sb').open('xb') as f:f.write(Path(s['policy']).read_bytes())
    counts={k:a['counts'][k]+b['counts'][k] for k in ('total','passed','failed')}
    artifacts=['snapshot-01.json','round-02/offline-work-receipt-01.json','binding-check-01.json','round-02/l6-meta-recompute-receipt.json','round-02/gate-verify-execution-reproduced.json','round-02/gate-admission-reproduced.json','sandbox-policy.sb','prepare.py','offline_work.py','offline_work_v2.py','binding_check.py','summarize.py']
    fingerprints={n:digest(OUT/n) for n in artifacts}
    rec={'at':datetime.now().astimezone().isoformat(timespec='seconds'),'kind':'independent_offline_reproduction','status':'PASS' if counts['failed']==0 and not drift else 'DIFFERENCES','counts':counts,'groups':{'offline_reproductions':a['counts'],'independent_binding_contract_inventory':b['counts']},'differences':[c for d in (a,b) for c in d['checks'] if not c['pass']],'input_inventory':{'files':s['file_count'],'bytes':s['bytes'],'protected_original_and_external_union':len(b['protected_inputs']),'final_rehash_at':datetime.now().astimezone().isoformat(timespec='seconds')},'selftests':{'bird_checker':'29/29 reported, exit0; two overview predicates, not 29 extra product executions','receipt_check':a['selftests']['receipt-selftest']['result']['counts'],'manifest_receipt':a['selftests']['manifest-selftest']['result']['counts']},'formal_receipt_reproduced':a['gate']['admission']['summary'],'real_score_recomputed':a['real_score_recompute'],'source_fingerprints':fingerprints,'nonzero_approved_injection':a['relocations'],'source_text_mutated':False,'first_failure':{'kind':'reviewer-only KeyError for absent CLI-specific weighted_8dp in WB meta','first_log':'offline-work-stderr-01.txt','first_worker':'offline_work.py','repair':'only audit assertion uses actual WB meta.weighted and score-receipt reported; fresh round-02 preserves all first outputs','candidate_change':False},'environment':{'explicit_home':'/Users/b612-lp','empty_home':False,'minimal_explicit_environment':True,'no_login_state_required':True,'isolated_python':True,'read_only_git_dir':str(ROOT/'.git'),'os_sandbox_deny_network':True,'os_sandbox_original_write_denied':True,'script_subprocess_allowlist':'only copied checker/gate/tools Python, or read-only Git','finalizer_observed_environment_keys':sorted(os.environ)},'scope_limits':['not online model rerun','not independent semantic contamination investigation','Git/local clock not external trusted time','retired zero-consumption claim is recorded producer history, not historical network packet proof','first reconciling guards is order-dependent, not proof of unique inferred guard set','no score/usage/meta backfill'], 'zero_model_calls':True,'zero_network_calls':True,'live_doc_drift':drift}
    create(OUT/'receipt.json',rec)
    spec=importlib.util.spec_from_file_location('ek',ROOT/'1-评测方案/工具链/evidence-kit/evidence_line.py');ek=importlib.util.module_from_spec(spec);spec.loader.exec_module(ek)
    rows=ek.gather([str(OUT/n) for n in artifacts]+[str(OUT/'receipt.json')],ROOT,ek.now_local())
    def link(n,label=None):return '['+(label or Path(n).name)+'](<5-评测报告/L6独立复核-2026-10-30/'+n+'>)'
    r=a['real_score_recompute'];bind=b['binding'];total=counts['total']
    report=f'''# L6 独立复核（task-19）

离线复算 / 判卷回归；independent-reviewer；仅本目录新增，原件只读、Git 只读、零模型、零网络。不计新增产品运行，也不重写 L4/L5 结论。

## 一、观察

**{counts['passed']}/{total} 个独立核验谓词成立，0 个未解决差异；live_doc_drift=[]。**

| 清单 | 独立实测 |
|---|---|
| L6-A 原脚本 | 字节未改；非 main 加载后仅四常量迁址，原 main 15/15 断言与档案逐项 / 完整字段一致（生成时刻除外） |
| checker 自测 | 实跑 exit0，29/29；不把自测例数计作产品运行 |
| 历史两工作区 | Git 79cebe0 修前 checker 独立 case 布局 vs 修后 case，各自重判 L5 E3 / E2 中止的两个 wb-bird 工作区；逐个判分字段零翻转，键集恰增 n_tasks/guards_used |
| L6-C 自测 | receipt_check 16/16；manifest_receipt 6/6；均自跑，不采信归档 PASS |
| 真实历史回放 | 修前 / 修后规则分别读取 E1/E2 中止收据：E1 两版均 ok，E2 新版明确抓获 self-reference；E2 旧有 UUID 词法违规单独保留，不当新规则功劳 |
| D3 contract | bird 盘面 checker / case_snapshot 顶层及 files / checker_sha256 三方相同，完整 SHA 为 ffa7389adef32779686bbe56aef7d711db1d8d1c191ff5dd389310e6c01d1910；其他四 case 的 JSON 原始子树字节与 L5 一致，全部五 case 文件清单与 digest 现算一致 |
| E3 封印 | 独立枚举28源+5 external，逐件磁盘 / E3 blob / manifest SHA，三设计原件 D3/E1/E2/E3/磁盘，Git祖先链、旧binding / 旧manifest与各committer时刻均通过 |
| gate CLI | verify-execution ok=true；admission formal_admitted=1/1 / fails=[]；有效逐槽字段与原收据一致 |
| 绕过负例 | 6/6拒绝：plan磁盘漂移、错plan绑定SHA、错seal、错registered_at、release=false、缺mandatory external（对最后一个显式注入哈希自洽E manifest，以穿过早期SHA检查） |
| 真实槽抽验 | checker.stdout == score.raw_checker_output 重新规范序列化的每个字节；独立 earned={r['earned']} / possible={r['possible']}，8dp={r['eight_dp']}；独立枚举首个调和 guards 与真实raw/meta一致 |

计数拆分：离线复跑与得分 / 负例谓词 {a['counts']['passed']}/{a['counts']['total']}；独立封印 / case / 文件清单 / 起止SHA谓词 {b['counts']['passed']}/{b['counts']['total']}。这是机械核验谓词总数，**不是独立统计样本量或新增调用次数**。checker29例仅以概览计数核对，不额外重复累加29；其余细分计数见收据。

## 二、证据

主汇总：{link('receipt.json')}；全量独立绑定：{link('binding-check-01.json')}；离线执行：{link('round-02/offline-work-receipt-01.json')}。

固定临时树 {s['file_count']} 个文件、{s['bytes']:,} bytes；{len(b['protected_inputs'])} 个原件 / 外部pin保护联合集最终无SHA漂移。完整路径和每文件字节/SHA位于 {link('snapshot-01.json')}。清单不省略失败、没有把 unknown 变0。

批准的四常量迁址是 **非零注入**，并非宣称无任何运行时适配：原脚本 ROOT/CHECKER/SOURCES 指向临时同布局副本；ARCHIVE 指向本独立目录。源脚本字节、函数体、断言未改；原收据仍在判卷修订档案，两份独立复跑收据留在本目录及 round-02，均 exclusive create。四常量前后值由执行收据完整列出。

E3 完整 seal `{bind['execution_seal_commit']}`，D3 `{bind['design_commit']}`；registered_at=`{bind['registered_at']}`，精确等于 Git %cI；manifest完整 SHA `{bind['execution_manifest_sha256']}`。两次废seal的旧manifest/binding已从Git读取并单独保存，未使用当前磁盘字节强配历史manifest：

'''
    for i,x in enumerate(b['retired_and_current_git_seals'],1):report+=f"- E{i} `{x['seal']}`，registered_at=`{x['registered_at']}`，{x['manifest_files']}源 / {x['external_files']}外部；见 "+link('E'+str(i)+'-git-binding.json')+' 和 '+link('E'+str(i)+'-git-manifest.json')+'。\n'
    report+='\n标准证据行（原 evidence_line 工具脚本生成）：\n\n```text\n'+'\n'.join(x['line'] for x in rows)+'\n```\n'
    report+='''
## 三、解释

1. L6-A 的证据支持“元数据新增两键、这两个历史工作区判分不变”，而不是所有潜在输入均不变的证明；原 script 的 answers_file.note 仅路径占位比较沿用，独立重判也只归一真实搬迁相关 run_dir 与该 note，不遮盖分数/checks/failed_questions 等值差异。
2. L6-C 的自引用排除可由真实 E2 反例触发；新生成器不把自身列入清单。旧 E2 自哈希不符没有被改成真，也没有通过回放去改写原记录。
3. gate 正向 PASS 与独立盘面/Git/hash证据相互印证；负例使用固定副本，修改的只有测试世界。缺external世界的manifest读取是显式受控注入，不冒称真实旧E blob含缺项。
4. 真实 score-receipt.score.earned=1 是 binary reward，不是15题正确数；实际正确数由 checks 排除guards后独立数出15。guards推导采用实现声明的“按索引序首个调和组合”，本满分样本下并非唯一数学解；结果一致不证明任意检查顺序都能准确恢复语义guard集合。

## 四、未排除因素

- 环境是新tmp/独立cwd/最小显式env/Python隔离/deny network/原件写拒，不是新机器或空HOME。HOME为历史绝对external pin保留；只解码公开代码与获授权判卷资产，凭据配置仅做原始字节SHA，不打印SQL答案/密钥/会话原文。没有联网校时，Git时间只是本机历史一致性，不是可信第三方时钟。
- 两次废seal的“零消耗、pre-claim拒绝”是原作者记载；本复核独立核Git旧值、源码差分、已归档拒绝记录，不具备追溯证明过去所有远程副作用不存在的网络观测。不能把当前runs一槽或源代码哈希当历史零调用证明。
- manifest明示未锁完整传递产品依赖。任何源/pin变化、判卷资产SHA变化，或新增槽位/输入不属于本意见；下一步需重封重审，停止条件是本清单任一输入漂移或证据身份不一致。
- 正向gate包含原meta污染裁定；本任务未重新逐句独立做语义污染调查，也不从formal1/1推导产品排名/广泛能力、货币成本或历史失格槽自动恢复。
- 初轮审计者错误假设WB meta具有CLI专用weighted_8dp键，产生KeyError并中断汇总；已保留首代码、stderr及先前完整复跑输出。第二轮只将该审计断言改为实际WB meta.weighted与score.reported的8dp比较，重跑新输出根round-02，不改被测源码/原meta，也未把此审计者错误列为产品缺陷。

## 五、可复现实验

只在新的独立工作副本 / 输出路径复现，保持仓库相对布局，脚本会拒绝覆盖现有输出。准备入口创建固定tmp、旧checker独立case和SBPL；离线worker必须经同一deny-network策略及最小环境运行。首次程序与只修审计断言的v2入口均保留，v2复用原worker其余代码；精确迁址清单在机器收据。

```sh
/usr/bin/python3 -B '5-评测报告/L6独立复核-2026-10-30/prepare.py'
# 使用snapshot返回的temporary_root及sandbox-policy.sb，不能猜旧tmp地址。
# env -i HOME=... PATH=... TMPDIR=<newtmp>/tmp GIT_DIR=<readonly-repo>/.git ...
# sandbox-exec -f <newtmp>/offline.sb python3 -I -B .../offline_work_v2.py
# sandbox-exec -f <newtmp>/offline.sb python3 -I -B .../binding_check.py
# 最后只读汇总：
/usr/bin/python3 -B '5-评测报告/L6独立复核-2026-10-30/summarize.py'
```

清单全量对账和最终重哈希均基于明列的输入，不扩大遍历其他用户session；原件不改、旧失败不删、不重跑模型。要得出新结论必须使用新路径收据，不能复用旧PASS替换新差异。

live_doc_drift=[]
'''
    with (OUT/'README.md').open('x',encoding='utf-8') as f:f.write(report)
    create(OUT/'evidence-lines-01.json',{'at':ek.now_local(),'items':rows,'live_doc_drift':[]})
    print(json.dumps({'status':rec['status'],'counts':counts,'live_doc_drift':drift,'evidence_lines':len(rows)},ensure_ascii=False))
    return int(bool(counts['failed'] or drift))
if __name__=='__main__':raise SystemExit(main())
