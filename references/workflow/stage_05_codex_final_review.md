---
stage: 5
owner: codex
name: final-review
inputs:
  - paper_draft.md
  - verified artifacts
  - literature/library.json
  - literature/claim_map.json
outputs:
  - reviews/final_review.md
  - reviews/final_patch_plan.json
---

# Stage 5 — 论文终审

## 目标

从评审视角检查论文逻辑、数学、结果、引用与跨文件一致性，并给出可机械执行的修改单。

## 执行

1. 检查是否逐问作答，摘要和结论是否准确覆盖主要贡献和定量结果。
2. 核对符号、公式、假设、算法描述、结果数字、图号、表号和路径。
3. 对照模型规格、审计结论和结果文件，识别夸大、跳步、因果误述和未验证主张。
4. 审核文献元数据、证据等级与 claim map；国内来源优先但不以数量替代权威性。
5. 检查官方规则相关内容，只能基于已核验的当届通知，不声称 Word/PDF 排版已合规。
6. 输出 `reviews/final_patch_plan.json`，每项包含目标位置、问题、证据、修改动作和验收标准。

## 流转

- 存在影响正确性、完整性或引用可信度的问题：`needs_revision`，退回 Claude Stage 4；
- 仅剩装配性修改且全部明确：`passed`，交给 Claude Stage 6。

Codex原则上不大面积重写论文，而是提供结构化、可验证的修改单。
