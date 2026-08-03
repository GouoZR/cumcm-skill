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

1. 按当届官方要求和 `competitions/cumcm/paper_skeleton.md` 组织摘要、问题重述、假设、符号、模型、求解、检验、评价和结论。
2. 每一问建立“问题要求—方法—结果—解释—验证”的闭环；不能只堆公式或代码过程。
3. 所有数字回链到 `results/`，所有图表回链到 `figures/`，模型表述与 Stage 3 通过版本一致。
4. 只引用 `literature/library.json` 中已核验且由 claim map 支持的来源；metadata-only 记录不得支撑实质结论。
5. 若无可用文献服务，可使用用户提供或官方可核验来源；不得伪造引用。缺失证据写入阻断项或局限性。
6. 输出 `support_materials_manifest.md`，不生成 DOCX/PDF。

## 验收

- 摘要包含方法、关键结果、验证和结论；
- 正文没有超出已验证产物的数字或论断；
- 引文与参考文献一一对应；
- Markdown 结构稳定，公式、表格和图片路径可读。
