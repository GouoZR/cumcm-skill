---
stage: 5
owner: codex
name: final-review
inputs:
  - paper_draft.md
  - artifacts/quality_contract.json
  - results/result_registry.json
  - verified artifacts
  - literature/library.json
  - literature/claim_map.json
outputs:
  - reviews/final_review.md
  - reviews/final_patch_plan.json
  - reviews/subagents/stage_05/*.md
---

# Stage 5 — 论文终审

## 目标

从评审视角检查论文逻辑、数学、结果、引用与跨文件一致性，并给出可机械执行的修改单。

## 执行

1. Codex 主 Agent 先独立阅读全文，建立“题目要求—章节—模型—结果—结论”覆盖表。
2. 按 `references/runtime/codex_subagents.md` 动态启用 3–5 个互补角色，覆盖逐问与结构、数学符号、结果图表、文献证据和竞赛评委视角；SubAgent 不可用时做对应的串行独立复核。
3. 检查摘要和结论是否准确覆盖主要贡献、定量结果和适用边界。
4. 以 `results/result_registry.json` 为核心数字真源，核对符号、公式、假设、指标口径、单位、作用域、算法描述、结果数字、图号、表号和路径。
5. 对照质量契约、模型规格、求解审计和原始结果，识别夸大、跳步与证据越界；重点拒绝“局部→全局”“OAT→无交互”“单次→稳定”“相关→因果”“拟合好→泛化好”“启发式最好值→全局最优”等推断。
6. 审核文献元数据、证据等级与 claim map；国内来源优先但不以数量替代权威性。
7. 按需对照 `competitions/cumcm/winning_patterns.md` 与 `competitions/cumcm/anti_patterns.md`，但只把它们当经验性质量参考；官方规则相关内容必须基于已核验的当届通知。
8. 主 Agent 复核所有发现，按 `templates/shared/final_review.md` 输出正式终审，并依照 `templates/shared/final_patch_plan.json` 的 `_patch_item_contract` 生成 `reviews/final_patch_plan.json`；`verdict` 与 `target_stage` 必须对应，每项字段完整。

## 国奖级论文门

- 摘要与正文逐问作答，贡献有准确的定量结果而非空泛形容；
- 主要结论有直接结果证据和验证证据，适用时补充机理/流程证据；
- 符号、公式、数字、图表、结论与已验证产物跨文件一致，论文核心数字均可在结果注册表定位；
- 不把局部扰动写成全局稳健，不把单因素分析写成无交互，不把单次运行写成稳定，不把相关写成因果，不把启发式最好值写成全局最优；
- 不夸大创新、泛化能力或获奖可能性；
- 实质性外部 claim 均由已核验内容支撑，metadata-only 不得证明结论；
- blocker/high 问题清零，medium/low 问题已修复、明确接受或写入限制。

## 流转

- 存在影响正确性、完整性、可复现性或引用可信度的问题：`needs_revision`，退回 Claude Stage 4；
- 仅剩装配性修改且全部明确，并满足论文门：`passed`，交给 Claude Stage 6。

Codex原则上不大面积重写论文，而是提供结构化、可验证的修改单；不得按 SubAgent 多数票替代主 Agent 裁决。
