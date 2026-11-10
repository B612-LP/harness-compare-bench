# 溯源：dabstep-payments-10 夹具与 DABstep 上游逐字节对照（2026-11-11）

**身份**：溯源披露（数据有效性证据，非派生分析）。目的=证明本仓库 [dabstep-payments-10](<../../2-用例/dabstep-payments-10/>) 的判分夹具未被本地改写：判分判的就是 DABstep 官方 dev 划分的原题原数据。对照时点 2026-11-11，上游=HuggingFace `adyen/DABstep` dataset repo `main` 分支当前版。

## 对照结果

| 文件 | 本仓库路径（`2-用例/dabstep-payments-10/inputs/` 下） | sha256（本地==上游，逐字节一致） |
| --- | --- | --- |
| fees.json | `fees.json` | `9a833666ae9be5a8…`（前 16 位，全值见复现） |
| manual.md | `manual.md` | `bb7f4ca6fdc759af…` |
| merchant_data.json | `merchant_data.json` | `f158e834de27ee84…` |
| payments.csv | `payments.csv` | `5fbb26210a45427d…` |
| 题目集合 | `questions.jsonl`（10 题） | task_id 集合 == 上游 `data/tasks/dev.jsonl` 全部 10 题（5/49/70/1273/1305/1464/1681/1753/1871/2697；easy 3 + hard 7） |

四个数据文件**逐字节一致**（4/4 SAME）；题目集合与上游 dev split **完全相等**。本仓库 `truth.json` 的 gold 与官方 dev 答案一致性另由判分器启动时交叉校验（见 [q2697 复算](<../派生分析-q2697gold复算-20261111/README.md>)所述 `gold_note`）。

## 上游已知缺陷在当前版仍未修正

- q2697 gold `E:13.57` 在全语义空间不可复现（[完整复算](<../派生分析-q2697gold复算-20261111/README.md>)）；
- guidelines 格式说明 `{card_scheme}:{fee}` 实为 ACI 字母（措辞 bug）——上游当前版仍如此。

即：本批 dabstep 判分结论（含模型侧失分）建立在官方原题原判分上；判分层缺陷属上游缺陷的如实披露，非本地引入。

## 复现指引

```bash
export HTTPS_PROXY=http://127.0.0.1:7897   # 访外按需
for f in fees.json manual.md merchant_data.json payments.csv; do
  curl -sL "https://huggingface.co/datasets/adyen/DABstep/resolve/main/data/context/$f" -o /tmp/$f
  sha256sum /tmp/$f "2-用例/dabstep-payments-10/inputs/$f"
done
curl -sL "https://huggingface.co/datasets/adyen/DABstep/resolve/main/data/tasks/dev.jsonl" -o /tmp/dev.jsonl
# 题集对照：/tmp/dev.jsonl 的 task_id 集合应与本地 questions.jsonl 完全相等
```

HF 文件为公开稳定资源；若上游未来更新导致 sha 漂移，以本表快照时点为准（2026-11-11，`main`）。

## 边界

- 本件只披露溯源事实，不改变任何判分、正式行或批次记录；零发射。
- acquirer_countries.csv / merchant_category_codes.csv 为上游 context 附属文件，本夹具 inputs 未使用（判分链不依赖），未列入对照。
