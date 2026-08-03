---
stage: 3
owner: codex
name: solution-audit
inputs:
  - artifacts/model_spec.md
  - artifacts/implementation_contract.md
  - artifacts/run_manifest.json
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
3. 抽查关键公式到代码的映射，核对变量、目标函数、约束、参数和指标。
4. 复核数据清洗、训练/验证划分、随机性、数值稳定性、量纲和边界情况。
5. 运行或复查最关键的复现实验、独立复算、基线、敏感性和 sanity check。
6. 核对图表、表格、正文候选结论是否来自同一结果版本。
7. 检查 `model_deviations.md` 是否合理、已披露并通过验证。
8. 主 Agent 对 SubAgent 证据做独立复核，按 `templates/shared/solution_audit.md` 输出正式审计：只给 `passed` 或 `needs_revision`。

## 国奖级求解门

- 关键结果可按运行清单复现，且至少独立复跑或复算一个决定性输出；
- 公式、变量、代码、结果表和图表可追溯；
- 主要结论有基线/对照以及敏感性、稳健性或误差证据；
- 数据泄漏、约束违反、量纲错误、随机性和数值不稳定风险已排查；
- 图表与正文候选数字来自同一结果版本；
- 所有 blocker 和影响正确性/可复现性的 high 问题已闭环。

## 流转

- `passed`：满足求解门，交给 Claude Stage 4；
- `needs_revision`：生成明确、可执行、按优先级排序的修改单，退回 Claude Stage 2；旧结果标记为 `stale` 或 `needs_revision`。

任何关键结果不可复现、与模型不一致、缺少基本合理性检查、存在未披露偏离，或仍有 confirmed blocker/未闭环 high 问题时，必须退回，不得按 SubAgent 票数带病通过。
