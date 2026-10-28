# v4 只修复流取证，继续剩余五场，不重跑真实结果

2026-10-29 Asia/Shanghai。v3首场large/full已发生2次真实HTTP200，正常完成并给出正确答案。取证实现仅在TransformStream.flush时写SSE，但原生transport在message_stop后取消读取，flush没有发生，故原始SSE丢失。首场stdout、两个实际请求、HTTP状态、已恢复的隔离session持久化stream/usage仍保留；持久化stream不是原始SSE，不能混称。runner基于缺失SSE触发停止。该场保留，不替换、不重跑、不声称actual_api_gate通过。

v4在任何后续调用之前冻结：唯一技术改变是observer在每个流chunk立即保存原始响应字节（并标注是否见message_stop）；模型可见输入与实验因素不变。继续原排序的剩余5场large/bounded、large/bounded、large/full、small/full、small/bounded。实际总样本仍6场、预期12请求、上限18请求（v3已有2请求计入），输入预算带入v3已报告20140输入token（443+19313+384），不因新版本重置预算。

正式裁定将首对标记取证降级：首场无原始SSE、response model仅adapter持久化来源，不用其作最强证据。第二交叉对和小输出负对照若均有实际请求/原始SSE/usage，则作为最强闭环；不得悄悄补一个full增加样本。所有v1/v2/v3冻结源字节保持不变，技术失败和已真实执行均保留，不把它们改写成成功。

这是取证修复而非根据模型答案选择样本。若剩余场出现真实API失败，仍按原停止规则，不改模型路由，不重试结果。
