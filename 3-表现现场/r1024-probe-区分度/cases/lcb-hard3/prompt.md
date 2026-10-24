# lcb-hard3：三道 LeetCode hard 题（LiveCodeBench 题包）

## 任务

`inputs/problems.json` 里有 3 道**竞赛难度**的算法题（题目原文 + 函数签名 + 测试组数）：

1. `2879` —— minimum-changes-to-make-k-semi-palindromes（15 组测试，入口 `Solution.minimumChanges`）
2. `3223` —— count-complete-substrings（14 组测试，入口 `Solution.countCompleteSubstrings`）
3. `3091` —— count-of-sub-multisets-with-bounded-sum（15 组测试，入口 `Solution.countSubMultisets`）

对每道题，在当前运行目录写一个 Python 文件：

```
solutions/<problem_id>.py
```

文件里必须包含与题面 `starter_code` 一致的 `class Solution`，并实现 `(见各题)` 对应的方法
（题面 `starter_code` 给了类名与方法签名；判分按 `Solution().<fn_name>(*args)` 调用）。

- 允许 import Python 标准库（`typing` 等）；**不联网**；
- 每个文件是独立模块，只放该题的解法；
- 你可以在本地用 `python3` 自己写测试验证，但最终判分用题包自带测试。

## 判分

每题 15 组测试**全过**才算该题通过；3 题里通过 ≥2 题记 reward=1，加权分按通过题数比例给。
只写产物文件即可，不需要解释。
