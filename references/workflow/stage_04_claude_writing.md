---
stage: 4
owner: claude
name: writing
inputs:
  - verified artifacts from stages 0-3
  - literature/library.json
  - literature/claim_map.json
outputs:
  - paper_workspace/
  - paper_draft.md
  - support_materials_manifest.md
---

# Stage 4 — Markdown 论文写作

## 目标

只使用已验证的模型、结果、图表和文献，形成完整、连贯、可由用户最终排版的 `paper_draft.md`。

## 执行

1. 主 Agent 先按当届官方要求和 `competitions/cumcm/paper_skeleton.md` 冻结章节骨架、符号表和图表编号，作为各章共用基线。
2. 按 `references/runtime/claude_subagents.md` 动态启用 3–5 个按章节文件分区的 SubAgent（摘要与前置章节 / 模型主体 / 验证与评价 / 参考文献 / 图表核验），各自只写独占的 `paper_workspace/<NN>_*.md`；SubAgent 不可用时按同样分区串行完成。
3. 每一问建立“问题要求—方法—结果—解释—验证”的闭环；不能只堆公式或代码过程。
4. 所有数字回链到 `results/`，所有图表回链到 `figures/`，模型表述与 Stage 3 通过版本一致。
5. 只引用 `literature/library.json` 中已核验且由 claim map 支持的来源；metadata-only 记录不得支撑实质结论。
6. 若无可用文献服务，可使用用户提供或官方可核验来源；不得伪造引用。缺失证据写入阻断项或局限性。
7. 主 Agent 装配 `paper_draft.md` 前，先用 `competitions/cumcm/anti_patterns.md` 做自检，逐类清掉可机械发现的写作缺陷（摘要 A 类、假设与符号 B 类、结果分析 E 类、呈现 I 类），不把这些留给 Codex Stage 5 才发现。
8. 输出 `support_materials_manifest.md`，不生成 DOCX/PDF。

## 国奖级写作门

进入 Stage 5 前，主 Agent 必须确认：

- 摘要含方法、可核验的定量结果、验证方式与适用边界，且与正文的模型、数据版本和结果表一致；
- 每一问闭环完整，关键数值有现实解释而非只报数字；
- 符号、单位、公式编号、图号、表号全文唯一且连续，首次出现处有定义；
- 每条假设有依据和影响范围，未进入推导的假设已删除；
- 主要结论有直接结果证据和验证证据，未夸大因果、创新或泛化能力；
- 正文引用与参考文献一一对应，无 metadata-only 支撑的实质结论；
- `anti_patterns.md` 自检已执行，命中项已修复或写入明确的限制说明。

未满足上述门槛时，主 Agent 必须先修订，不得把可自检的写作缺陷转嫁给 Stage 5。

## 验收

- 摘要包含方法、关键结果、验证和结论；
- 正文没有超出已验证产物的数字或论断；
- 引文与参考文献一一对应；
- Markdown 结构稳定，公式、表格和图片路径可读。
