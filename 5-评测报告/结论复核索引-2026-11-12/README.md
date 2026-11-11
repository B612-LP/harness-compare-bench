# 一页结论—绑定提交—公开复算—私档缺口

对应[第四周反馈](<../../反馈/2026-11-11-第四轮/README.md>)与[当前整合报告 v1.11](<../竞品评测报告-v1.11.md>)。绑定的是每条结论的证据/实现快照，不是“任意 HEAD 全部可核”。新分析是事后重算/方法检验，不新增产品运行，旧协议、报告、25格及原成绩不回写。

| 关键问题 | 当前可说的结论 | 绑定提交 | 公开复算/证据入口 | 不能公开或尚未识别的缺口 |
|---|---|---|---|---|
| 正式25格 | 每格n=1；A10/B10/W5只作轨内观察，不合五款总榜。 | [ababe63](<https://github.com/B612-LP/harness-compare-bench/commit/ababe63694b46db7ed8cd2c5210243155b5cde5c>)（历史可执行代） | [旧版25行来源闭合](<https://github.com/B612-LP/harness-compare-bench/blob/ababe63694b46db7ed8cd2c5210243155b5cde5c/5-评测报告/正式行复核-2026-11-05/README.md>)；该代v1.9与当前v1.9/v1.10/v1.11的§3字节相同。 | 38b2/06ef当前树运行旧verify会在q2697文档SHA门失败；只在左列固定历史代实际通过。来源闭合非重新判卷或原件认证，详见下方漂移与命令。 |
| 输入为何减少 | 18场捕获区间保留旧历史；工具源正文省略与包装差共存，不能只归为等文本重组。 | [06ef6ef](<https://github.com/B612-LP/harness-compare-bench/commit/06ef6ef19272f398466278500d30a8eb8d5fae11>) | [定义/18场分账](<https://github.com/B612-LP/harness-compare-bench/blob/06ef6ef19272f398466278500d30a8eb8d5fae11/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E8%BE%93%E5%85%A5%E6%BA%90%E8%A6%86%E7%9B%96%E4%B8%8E%E6%9C%BA%E5%88%B6%E5%8C%BA%E5%88%86-2026-11-12/README.md>) · [A重算](<https://github.com/B612-LP/harness-compare-bench/blob/06ef6ef19272f398466278500d30a8eb8d5fae11/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E8%BE%93%E5%85%A5%E6%BA%90%E8%A6%86%E7%9B%96%E4%B8%8E%E6%9C%BA%E5%88%B6%E5%8C%BA%E5%88%86-2026-11-12/verify.py>) · [结果](<https://github.com/B612-LP/harness-compare-bench/blob/06ef6ef19272f398466278500d30a8eb8d5fae11/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E8%BE%93%E5%85%A5%E6%BA%90%E8%A6%86%E7%9B%96%E4%B8%8E%E6%9C%BA%E5%88%B6%E5%8C%BA%E5%88%86-2026-11-12/result.json>) | 同DSH六对与原生三block不合n=9；引用不等实际回读，未控制后端历史/思考/cache，不推token/费用。 |
| 30次测了什么 | 30槽/10组重复性，不是M1外溢效果；完整旧门6不通过+4不可核，DSH4/5仅字节子门。 | [06ef6ef](<https://github.com/B612-LP/harness-compare-bench/commit/06ef6ef19272f398466278500d30a8eb8d5fae11>) | [版本化澄清v1.1](<https://github.com/B612-LP/harness-compare-bench/blob/06ef6ef19272f398466278500d30a8eb8d5fae11/4-%E6%89%93%E5%88%86%E7%BB%86%E5%88%99/%E6%9C%BA%E5%88%B6%E9%87%8D%E5%A4%8D%E5%8F%A3%E5%BE%84%E6%BE%84%E6%B8%85-2026-11-12/README.md>) · [B重算](<https://github.com/B612-LP/harness-compare-bench/blob/06ef6ef19272f398466278500d30a8eb8d5fae11/4-%E6%89%93%E5%88%86%E7%BB%86%E5%88%99/%E6%9C%BA%E5%88%B6%E9%87%8D%E5%A4%8D%E5%8F%A3%E5%BE%84%E6%BE%84%E6%B8%85-2026-11-12/verify.py>) · [新安全投影](<https://github.com/B612-LP/harness-compare-bench/blob/06ef6ef19272f398466278500d30a8eb8d5fae11/4-%E6%89%93%E5%88%86%E7%BB%86%E5%88%99/%E6%9C%BA%E5%88%B6%E9%87%8D%E5%A4%8D%E5%8F%A3%E5%BE%84%E6%BE%84%E6%B8%85-2026-11-12/evidence.json>) | 69历史公共源来自38b2；新投影不在该基线，只能公开核算术。24继承meta/缺a1_gate、4基名缺口保留；不认证私档内容。 |
| 零命中如何判 | 在当前检测面未观察到；WB1124个记录≠读取机会，豆包未采≠零命中。 | [06ef6ef](<https://github.com/B612-LP/harness-compare-bench/commit/06ef6ef19272f398466278500d30a8eb8d5fae11>) | [sensor×truth分账](<https://github.com/B612-LP/harness-compare-bench/blob/06ef6ef19272f398466278500d30a8eb8d5fae11/4-%E6%89%93%E5%88%86%E7%BB%86%E5%88%99/%E8%AF%BB%E5%8F%96%E8%A7%82%E6%B5%8B%E8%A3%81%E5%AE%9A-2026-11-12/README.md>) · [C重算](<https://github.com/B612-LP/harness-compare-bench/blob/06ef6ef19272f398466278500d30a8eb8d5fae11/4-%E6%89%93%E5%88%86%E7%BB%86%E5%88%99/%E8%AF%BB%E5%8F%96%E8%A7%82%E6%B5%8B%E8%A3%81%E5%AE%9A-2026-11-12/verify.py>) · [结果](<https://github.com/B612-LP/harness-compare-bench/blob/06ef6ef19272f398466278500d30a8eb8d5fae11/4-%E6%89%93%E5%88%86%E7%BB%86%E5%88%99/%E8%AF%BB%E5%8F%96%E8%A7%82%E6%B5%8B%E8%A3%81%E5%AE%9A-2026-11-12/result.json>) | 合成28试次不能给产品召回率；两个世界兼容同一日志，真实读取分母/FN/非平凡风险上界未知，不证明隔离。 |
| 判分链能否支撑归因 | q2697在216语义组合下不可复现原gold；判卷对象、gold、参考解和自测先于未来能力归因。 | [38b2e13](<https://github.com/B612-LP/harness-compare-bench/commit/38b2e13f63c5aeacb58094d2e977980ab12e8041>) | [金标复算](<https://github.com/B612-LP/harness-compare-bench/blob/38b2e13f63c5aeacb58094d2e977980ab12e8041/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E6%B4%BE%E7%94%9F%E5%88%86%E6%9E%90-q2697gold%E5%A4%8D%E7%AE%97-20261111/README.md>) · [前置门](<https://github.com/B612-LP/harness-compare-bench/blob/38b2e13f63c5aeacb58094d2e977980ab12e8041/4-%E6%89%93%E5%88%86%E7%BB%86%E5%88%99/%E5%88%A4%E5%88%86%E9%93%BE%E5%89%8D%E7%BD%AE%E9%AA%8C%E8%AF%81%E8%A7%84%E8%8C%83-2026-11-11/README.md>) | 兼容历史分保留；不因不复现而猜新gold、回判正式行，交付终点失败不自动等于算法能力失败。 |
| 台账能否全量认证 | 只能按对应generation.head和同一sidecar复算，不能说任意最新HEAD全可核。 | [38b2e13](<https://github.com/B612-LP/harness-compare-bench/commit/38b2e13f63c5aeacb58094d2e977980ab12e8041>)；generation=[66e98ea](<https://github.com/B612-LP/harness-compare-bench/commit/66e98ea25caaeec041a794f8efa3d926f4213a82>) | [复算合同](<https://github.com/B612-LP/harness-compare-bench/blob/38b2e13f63c5aeacb58094d2e977980ab12e8041/4-%E6%89%93%E5%88%86%E7%BB%86%E5%88%99/%E6%A0%B8%E9%AA%8C%E5%8F%B0%E8%B4%A6-2026-11-07/README.md>) · [绑定清单](<https://github.com/B612-LP/harness-compare-bench/blob/38b2e13f63c5aeacb58094d2e977980ab12e8041/4-%E6%89%93%E5%88%86%E7%BB%86%E5%88%99/%E6%A0%B8%E9%AA%8C%E5%8F%B0%E8%B4%A6-2026-11-07/ledger.json>) | 5类公开不可复核缺口与14件私档sidecar分列；机器见证非真人签名或原件真实性认证。 |

## 最小复算（在独立克隆/工作树中）

先取下列确切研究提交，不在有未提交改动的工作目录直接切换：

```sh
git checkout --detach 06ef6ef19272f398466278500d30a8eb8d5fae11
python3 -I -S -B '5-评测报告/输入源覆盖与机制区分-2026-11-12/verify.py' --root .
python3 -I -S -B '4-打分细则/机制重复口径澄清-2026-11-12/verify.py' --root .
python3 -I -S -B '4-打分细则/读取观测裁定-2026-11-12/verify.py' --root .
```

三命令默认只读并输出JSON；同目录 `test_verify.py` 可另在普通/`-O`模式运行。成功只说明各自固定公开字节与声明范围相符，不恢复私档原文、不证明产品效果或历史全部封印通过。各原始usage保持逐场辅助记录，bytes不当token/费用。

**历史复核漂移（本次实际重放）：**旧正式来源校验器在 `ababe63694b46db7ed8cd2c5210243155b5cde5c` 返回 `ok=true`，402项中397匹配、5历史缺失；在38b2/06ef返回 `trusted source SHA mismatch: 4-打分细则/裁定-2026-10-26-dab-q2697.md`。后者为396匹配、5历史缺失、1已改文档不匹配：预期SHA `7a163a5bd803712acc237f0d5da8c71f18218ea558c51999b6f6b0b11362d152`，当前 `48320c5369325790103ca14842e17eebaa1d9908b771cad33a6536a018cc6f39`；不更新旧pin或倒洗原件来造全绿。历史代v1.9与当前v1.9/v1.10/v1.11的§3（从 `## 3.` 起至 `## 4.` 前）均3121B、SHA `ae22e337ff75f089a35577a096a2036e454dd711a22c4a62c687533146965419`，这是字节桥接，不认证后续分析。要重放旧入口，请在另一独立克隆：

```sh
git checkout --detach ababe63694b46db7ed8cd2c5210243155b5cde5c
python3 -I -S -B '5-评测报告/正式行复核-2026-11-05/verify.py' --root .
```

**先解释再增样本：**30次已完成，不能按Issue审阅时点的“尚未运行”重跑；新的序列诊断、首三条内容一致或模型输出波动不替代旧AND主门，不提高正式n。
