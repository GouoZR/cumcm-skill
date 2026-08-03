---
stage: 2
owner: claude
name: implementation
inputs:
  - artifacts/model_spec.md
  - artifacts/implementation_contract.md
  - input/
outputs:
  - code/
  - results/
  - figures/
  - artifacts/run_manifest.json
  - artifacts/model_deviations.md
---

# Stage 2 — 数据处理、实现与求解

## 目标

严格按模型规格完成可复现实现，产生论文可用且可审计的结果和图表。

## 执行

1. 主 Agent 先固定公共数据清洗模块、随机种子策略和 `references/visualization/plot_style.py` 绘图样式，作为各子问题共用基座。
2. 按 `references/runtime/claude_subagents.md` 动态启用 2–4 个按子问题分区的 SubAgent，各自负责一问的实现、求解、结果表与证据图；SubAgent 不可用时按同样分区串行完成。可从 `templates/shared/code_starter/` 对应骨架起步，不从零重写通用流程。
3. 先完成最小基线，再实现正式模型；对关键中间量做断言、量纲检查和极端输入测试。
4. 每个子问题至少配三类证据图之一（直接结果图、验证/敏感性图；机制可解释时补机理/流程图），不止堆公式或代码过程；用 `references/visualization/figure_audit.py` 做图表体检。
5. 主 Agent 核验各子问题产出（见 `claude_subagents.md`「主 Agent 核验」），核验通过后统一登记到 artifact manifest，并保存 `artifacts/run_manifest.json`。
6. 若规格无法实现或需调整模型，必须写 `artifacts/model_deviations.md`；不得静默更换目标函数、约束、指标或数据口径。
7. 自检通过后交给 Codex Stage 3；若 Stage 3 退回，则按修改单完成 Stage 2R，只修复修改单指出的问题，不重开未受影响的子问题。

## 国奖级实现门

- 每个子问题的结果可从原始输入独立复现，且至少有一个决定性输出被主 Agent 亲自复跑或复算；
- 关键中间量做过断言、量纲检查和极端输入测试，失败未被隐藏；
- 每个子问题至少有直接结果证据图，风险较高的结论补验证/敏感性证据，机制类结论补机理/流程图；
- 图表数字与结果表一致，跨子问题的公共变量口径统一；
- 模型偏离已显式记录并说明影响范围；
- SubAgent 并行不降低验收标准，主 Agent 已核验后才登记 manifest。

## 验收

- 从原始输入可重复生成主要结果；
- 结果文件不依赖手工复制；
- 图表数字与结果表一致；
- 模型偏离已显式记录；
- 失败、警告和未完成实验没有被隐藏。
