---
stage: 1
owner: codex
name: modeling
inputs:
  - artifacts/problem_analysis.md
  - artifacts/data_inventory.md
  - active handoff
outputs:
  - artifacts/model_spec.md
  - artifacts/implementation_contract.md
  - literature/query_plan.json
---

# Stage 1 — 查漏补缺与正式建模

## 目标

基于 Stage 0 的事实拆解，形成 Claude 可直接实现、可检验、可回退的正式模型规格。

## 执行

1. 检查题意遗漏、变量定义、量纲、约束、数据泄漏、不可辨识性和目标冲突。
2. 对每个子问题比较少量候选模型，说明选择理由、适用前提和被放弃方案；优先最简单且能回答题目的模型。
3. 固化假设、符号、核心公式、求解流程、基线、评价指标、敏感性与边界测试。
4. 写 `artifacts/implementation_contract.md`：输入输出、模块、随机种子、参数、测试、结果表和图表要求。
5. 写文献查询计划，只定义需要什么证据；可用时检索，不可用时不阻断建模。
6. 生成交接单给 Claude Stage 2。

## 验收

- 模型规格足以让实现者不靠聊天上下文编码；
- 题目每一问都映射到模型、算法、结果和验证；
- 公式、数据口径和代码接口一致；
- 关键结论有预定验证方式；
- 不以复杂度代替合理性。
