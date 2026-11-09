# frozen-checkers —— r1109-mech-n3 判卷字节依据（v2 冻结副本）

本批判卷一律使用 [可信冻结-2026-10-29-v2](../../../4-打分细则/可信冻结-2026-10-29-v2/config.json) 快照字节的 checker。逐文件核验结论：

- 五案 truth.json / instruction.md / spec.md / case.json 等其余 pinned 文件：与公开树 `2-用例/<case>/` **逐字节一致**（sha256 == v2 config `files` 快照，本批发射前全量核验通过），不重复随档；
- 唯一字节差异文件：**bird-ca-schools-15 的 checker.py 与 spec.md**（公开树现行版本经 2026-10-30 发布重写已非 v2 字节）。本目录仅随档判卷直接依赖的 `bird-ca-schools-15/checker.py`（sha256 `994be0b3b766e457b5b7d91de6b1ef814dbd6886c9e4a4f9ee63cded69abca54` == v2 快照）；v2 版 spec.md（sha256 `1916b2a0d7fdfa1bfbda24922bf2dfcd6f84ba1cf21d83d6d0676e28ad8e6a20`）不随档，可经 git 历史（发布重写前的提交）按该 sha 复取，不用于本批判卷。

判卷调用：`python3 frozen-checkers/bird-ca-schools-15/checker.py <workspace> --json`（其余四案直接用公开树 2-用例 checker）。
