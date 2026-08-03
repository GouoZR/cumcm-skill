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
---

# Stage 3 — 模型、代码与结果审计

## 目标

判断实现是否真的执行了既定模型、结果是否可信，以及是否足以开始论文写作。

## 执行

1. 抽查关键公式到代码的映射，核对变量、目标函数、约束、参数和指标。
2. 复核数据清洗、训练/验证划分、随机性、数值稳定性、量纲和边界情况。
3. 运行或复查最关键的复现实验、基线、敏感性和 sanity check。
4. 核对图表、表格、正文候选结论是否来自同一结果版本。
5. 检查 `model_deviations.md` 是否合理并已验证。
6. 输出 `reviews/solution_audit.md`：只给 `passed` 或 `needs_revision`。

## 流转

- `passed`：交给 Claude Stage 4；
- `needs_revision`：生成明确、可执行、按优先级排序的修改单，退回 Claude Stage 2；旧结果标记为 `stale` 或 `needs_revision`。

## 验收

任何关键结果不可复现、与模型不一致、缺少基本合理性检查或依赖未披露偏离时，必须退回，不得带病进入写作。
