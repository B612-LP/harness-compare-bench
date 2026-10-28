# v2 技术修正预注册（任何真实API之前）

2026-10-29，Asia/Shanghai。v1唯一尝试在插件挂载阶段exit=1，未发任何API，已冻结的v1脚本和收据完整保留。原因是 `tools.restrict` 不支持全局上下文；并非模型结果或实验机制不成立。

v2只改变实现隔离工具集的方法：禁用profile中全部内置工具插件，移除全局restrict调用；仍发送前验证只有fixture_output一个schema。首调基线、官方host/low/max_tokens=1024/两个响应model与usage门全部保留。因素12500 vs512、固定6场排序、任务、输出规则、预算、停止条件、负对照与最窄结论完全不变。v2在新仓外子目录和新证据子目录独立冻结；不覆盖v1。

v1的失败归interface_preflight，不能记为product_run失败。v2只有确证实际API的场才归product_run/research/experiment。每场独立首调可能产生不同thinking/assistant文本，分析必须精确记录这种残余随机性，不能声称第二请求逐字只差工具结果；优先裁定原生spill的直接传输机制及usage配对差，不将全部usage差无条件归因策略。
