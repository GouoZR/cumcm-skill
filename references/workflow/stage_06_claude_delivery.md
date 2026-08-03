---
stage: 6
owner: claude
name: delivery
inputs:
  - paper_draft.md
  - reviews/final_patch_plan.json
  - verified artifacts
outputs:
  - paper.md
  - submission_checklist.md
  - support_materials_manifest.md
---

# Stage 6 — 修改应用与 Markdown 交付

## 目标

逐项应用 Codex 已通过的修改单，装配稳定的最终 `paper.md`，然后把排版和 PDF 转换责任明确交还用户。

## 执行

1. 逐项应用 `reviews/final_patch_plan.json`，记录完成状态；不得借机更换模型或新增未验证结果。
2. 检查标题层级、公式、表格、图片相对路径、参考文献、术语、符号和交叉引用。
3. 生成 `paper.md`；可额外生成 `submission_checklist.md` 与 `support_materials_manifest.md`。
4. 确认 `paper.md` 存在后调用 `workflow.py complete`。

## 最终边界

Skill 不自动生成最终 Word、WPS 或 PDF，不声称已经满足字体、页边距、分页、页眉页脚等版式要求。用户必须依据实际参赛当届的官方通知手工排版、复核并导出 PDF。

## 验收

- `paper.md` 是唯一论文主交付；
- 不含占位符、伪造引用、未验证数字或密钥；
- 支撑材料清单完整；
- 用户得到清晰的手工排版与提交检查清单。
