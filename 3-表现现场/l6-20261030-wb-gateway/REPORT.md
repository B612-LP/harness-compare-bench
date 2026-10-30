# L6 WorkBuddy 网关评测摘要（事后脱敏）

> 本文是事后脱敏摘要，不是历史封印原件；不能证明旧验收时序，也不表示重新验证。静态预检、mock、自检、拒绝与真实运行分开记账。

## 预检、失败与废封

- 初始静态预检未全过：bird checker 哈希仍为旧合同 pin；其余检查通过。缺 binding 的验证按 fail-closed 拒绝。初始 selftest 70/71，唯一失败 T22d 的身份字段仍锚定 L5；这些都不是产品运行。
- E1 废止，原记录称站点常量适配遗漏，零模型调用；适配后预检 all_pass=True，但 selftest 仍为 70/71，T22d 未修。不可将预检转绿描述为全部自检通过。
- E2 因计划哈希不匹配 REFUSED，零调用、零残留；适配计划目录后该检查通过。随后又发现 binding 的外部锁定文件列表为空，不满足 gate 必需项，验证拒绝。需补齐锁定项并重封，不能把拒绝或 mock 当作实际运行。
- dry/mock 夹具仅为自测产物，不代表真实槽。[站点复制收据](<receipts/site-copy-receipt.json>)仍可查看；适配差异及运行默认值审计原件不公开，不能凭摘要独立核验。原记录提及 E1 废封纪要，但该纪要未在公开工作树提供，故无法据其公开复核。

## E3 真实槽

原记录称 E3 验证全绿后，bird-ca-schools-15-r1 单次真实执行，status=ok，148 秒，earned=1、weighted=100.0，correct=15/15；checker pin 为 `ffa7389a`，四项 guard 已记录，输入核对 4 项通过。原生模型为 deepseek-v4.1-flash，renderer ready，原记录完整性为 clean。证据见 [得分收据](<runs/l6-20261030-wb-gateway-bird-ca-schools-15-r1/score-receipt.json>) 和同目录其他记录。

clean 是原记录的完整性结果，并不自动排除污染，也不等于正式准入。正式裁定、未排除因素及未知项应依据独立判定与完整证据核对，本摘要不替代该核查。
