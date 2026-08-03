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

1. 建立可重复的数据处理和求解入口；固定随机种子，保存运行参数、环境和命令。
2. 先完成最小基线，再实现正式模型；对关键中间量做断言、量纲检查和极端输入测试。
3. 生成结构化结果、对比表、敏感性结果和必要图表。技术图优先使用 Python、Mermaid 或 SVG。
4. 将代码、输出和图表登记到 artifact manifest，并保存 `artifacts/run_manifest.json`。
5. 若规格无法实现或需调整模型，必须写 `artifacts/model_deviations.md`；不得静默更换目标函数、约束、指标或数据口径。
6. 自检通过后交给 Codex Stage 3；若 Stage 3 退回，则按修改单完成 Stage 2R。

## 验收

- 从原始输入可重复生成主要结果；
- 结果文件不依赖手工复制；
- 图表数字与结果表一致；
- 模型偏离已显式记录；
- 失败、警告和未完成实验没有被隐藏。
