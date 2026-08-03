---
stage: 3
owner: codex
name: solution-audit
inputs:
  - artifacts/model_spec.md
  - artifacts/quality_contract.json
  - artifacts/implementation_contract.md
  - artifacts/run_manifest.json
  - results/result_registry.json
  - code/
  - results/
  - figures/
outputs:
  - reviews/solution_audit.md
  - reviews/stage2_patch_plan.md
  - reviews/subagents/stage_03/*.md
---

# Stage 3 — 模型、代码与结果审计

## 目标

判断实现是否真的执行了既定模型、结果是否可信，以及是否足以开始论文写作。

## 执行

1. Codex 主 Agent 冻结被审计的 run manifest/结果版本，并亲自追踪至少一条决定性“公式—代码—结果”链。
2. 按 `references/runtime/codex_subagents.md` 动态启用 3–4 个互补角色，分别覆盖数学一致性、模型—代码映射、数值/稳健性和反例检查；SubAgent 不可用时做对应的串行独立复核。
3. 读取 `references/audit/competition_quality_gates.md`，按题型核对最低验证集；不适用项必须有理由。
4. 抽查关键公式到代码的映射，核对变量、目标函数、约束、参数、指标、聚合顺序、重复计数和归一化口径。
5. 逐条审计 `quality_contract.json`：分析单位、指标定义、不变量、基线/oracle、保真度/离散化和结论边界是否真正执行。
6. 复核数据清洗、训练/验证划分、随机性、数值稳定性、量纲和边界情况。
7. 主 Agent 至少选一个决定性结果，从原始输入、决策或中间量重新构造；不得只再次调用生产目标函数。运行或复查基线、反例、敏感性和 sanity check。
8. 核对 `result_registry.json` 的 primary 指标能否定位到真实结果文件，且值、单位、作用域、seed、图表和候选结论来自同一结果版本。
9. 检查 `model_deviations.md` 是否合理、已披露并通过验证；涉及语义或离散化变化时，质量契约和哈希必须同步更新。
10. 主 Agent 对 SubAgent 证据做独立复核，按 `templates/shared/solution_audit.md` 输出正式审计：只给 `passed` 或 `needs_revision`。

## 国奖级求解门

- 关键结果可按运行清单复现，且至少用不复用生产总目标函数的方式独立复跑或复算一个决定性输出；
- 每问的数学语义、聚合/去重规则、约束和结论作用域没有歧义，质量契约中的不变量均有证据；
- 预测、评价、优化、仿真、机理、空间网络等题型的适用最低验证集已完成；
- 公式、变量、代码、结果表和图表可追溯；
- 主要结论有基线/对照以及敏感性、稳健性或误差证据；
- 数据泄漏、约束违反、量纲错误、随机性和数值不稳定风险已排查；
- 图表与正文候选数字来自同一结果版本；
- 所有 blocker 和影响正确性/可复现性的 high 问题已闭环。

## 流转

- `passed`：满足求解门，交给 Claude Stage 4；
- `needs_revision`：生成明确、可执行、按优先级排序的修改单，退回 Claude Stage 2；旧结果标记为 `stale` 或 `needs_revision`。

任何关键结果不可复现、与模型不一致、缺少基本合理性检查、存在未披露偏离，或仍有 confirmed blocker/未闭环 high 问题时，必须退回，不得按 SubAgent 票数带病通过。
