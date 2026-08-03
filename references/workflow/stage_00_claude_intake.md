---
stage: 0
owner: claude
name: intake
inputs:
  - input/problem.pdf or input/problem.md
  - input/data/
outputs:
  - artifacts/problem_analysis.md
  - artifacts/data_inventory.md
  - state/artifact_manifest.json
---

# Stage 0 — 题面解析与初始框架

## 目标

把用户已放入工作区的题面和附件转成可供建模的事实基础。默认自动扫描，不询问队伍人数、成员擅长、截止时间、运行模式或已确定的题号。

## 执行

1. 清点 `input/` 中的题面、附件、数据字典和说明文件；记录格式、大小、编码、表字段和缺失情况。
2. 将题目拆成子问题、显式要求、约束、评价目标、最终需回答的量和交付物。
3. 区分题面事实、合理推断和待验证事项，不编造缺失条件。
4. 输出初始问题结构、候选建模方向和风险，但不冻结正式模型。
5. 更新 artifact manifest，并生成交接单给 Codex Stage 1。

只有以下情况可以提一个阻断性问题：没有任何题面；存在多个无法判定的题目版本；关键附件无法读取且没有可替代输入。

## 验收

- 每个子问题有输入、输出、约束和评价目标；
- 数据清单可追溯到原文件；
- 未把候选模型写成既定方案；
- 没有为启动而索取非必要团队信息。
