# L7-A 历史复算设计变更说明（dated，2026-10-30）

## 结论

L7-A（gate 语义默认值显式化）的历史复算**不采用跨批重演**，改用「基线收据引用固定 +
修订版自身行为验收」。r1-r6 五版探索全档保留（收据 VOIDED 链），其结构性发现本身
构成对封印钉定设计的强化证明。

## 探索过程（全部留档）

| 版本 | 设计 | 结局 | 结构发现 |
|---|---|---|---|
| r1 | 修订版 gate 复判三批 | 17 断言 5 过 | E manifest 钉 gate.py=38b42a87，修订版字节必 mismatch——**fail-closed 按设计工作** |
| r2 | git 提取修前 gate 复判 | 提取到 /var/folders | gate 以 `HERE.parents[2]` 推导 REPO，副本错位即崩（WB 准入加载 runner validator 时暴露） |
| r3 | 冻结副本放真实目录树 | L4 缺 receipt_check 旧字节 | manifest 钉**全套**工链（含 evidence-kit）；L6-C 演进后 L4 世界不可部分重构 |
| r4 | git worktree@E 提交 | 树内 binding 是废封遗物 | 封印提交树内 runtime-binding 落后盘面终版（E 后重写），用树内 binding=拿废 pin 判终版世界 |
| r5 | worktree+ROOT binding | L4 executed=0/partial=6；L5 缺槽 | 封印树**不含 E 后证据**；L4 基线形态本就是 executed=0/partial=17（发射缺口），「重演 executed=17」是伪期望 |
| r6 | worktree+证据子树覆盖 | L6 1/1 ✓；L4/L5 仍不齐 | L4/L5 证据与钉定工链在盘面代际交错，覆盖面无法既全又纯净 |

## 不可行性的结构根源

每批 admission 的 `manifest-files-safe-and-consistent` 步要求「manifest 钉值 == E blob ==
磁盘」三方一致。共享工链（gate、evidence-kit）在后续环演进后，历史批的三方一致在当前
盘上**按设计不可满足**——这正是封印钉定系统的目的：历史批的裁定由封印时刻的字节与
收据永久固定，不随 HEAD 漂移。重建「封印世界+后置证据」的混合体需要逐批考古式拼装，
其自身复杂度与可信度都不如引用封印时刻的原始收据。

## L7-A 最终验收面（r7 收据）

1. **修订版自身行为**：selftest PASS；近似错误例 N1-N4（缺参即拒、None 即 GateError、
   坏目录 fail-closed）；
2. **封印 pin 精确性**：修订版 gate 复判 L6 恰因 `gate.py sha-mismatch want=38b42a87`
   拒（P4）——证明失败=封印 pin 而非语义漂移；
3. **基线收据引用固定**：L4 0/17（L4 收官收据）、L5 5/6（L5 R4 复算收据 + judge
   canonical）、L6 1/1（gate-admission-e3.json）三份冻结收据存在且哈希入档（G 组）；
   其可信性由各自封印时刻的独立验收（L4 双验、L5 三路、L6 三路）背书。

## 遗产

r1-r6 的结构发现已反哺两处：①「共享工链演进=历史批重判通道按设计关闭」写入本说明，
供后续环直接引用；②L6 收官已立的「收尾必跑不变量测试」制度继续有效。

live_doc_drift: none（0 项）
