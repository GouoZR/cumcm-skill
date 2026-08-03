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
  - reviews/subagents/stage_01/*.md
---

# Stage 1 — 查漏补缺与正式建模

## 目标

基于 Stage 0 的事实拆解，形成 Claude 可直接实现、可检验、可回退的正式模型规格。

## 执行

1. Codex 主 Agent 先独立梳理题目主线、逐问依赖和决定性建模选择，不把关键路径整体委派。
2. 按 `references/runtime/codex_subagents.md` 动态启用 2–4 个互补角色，重点审查模型备选、假设/约束/可辨识性、实现可行性和文献证据需求；SubAgent 不可用时做对应的串行独立复核。
3. 检查题意遗漏、变量定义、量纲、约束、数据泄漏、不可辨识性和目标冲突。
4. 对每个关键子问题比较少量候选模型，说明选择理由、适用前提和弃选方案；优先最简单且能回答题目的模型。
5. 按 `templates/shared/model_spec.md` 固化假设、符号、核心公式、求解流程、基线、评价指标、敏感性与边界测试。
6. 按 `templates/shared/implementation_contract.md` 写实现契约：输入输出、模块、随机种子、参数、测试、结果表、证据图和复现要求。
7. 写文献查询计划，只定义需要什么证据；可用时检索，不可用时不阻断建模。
8. 主 Agent 核验并整合 SubAgent 发现，在 handoff 的“SubAgent 审查轨迹”中记录采用报告、驳回发现与理由或串行降级，再交给 Claude Stage 2。

## 国奖级建模门

- 每一问都有“目标—输入—模型—输出—指标—验证”闭环；
- 关键选择有基线或可比较备选，假设有验证方式或失效边界；
- 公式、符号、量纲、约束、数据口径和代码接口一致；
- 每个主要结论预先绑定结果表/图与稳健性证据；
- 模型规格足以让实现者不依赖聊天上下文编码；
- 不以复杂度和算法堆叠代替题意适配与合理性。

未满足上述门槛时，主 Agent 必须先修订模型规格，不得把未决核心问题转嫁给 Stage 2。
