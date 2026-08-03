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

1. 先按 `_patch_item_contract` 检查 `reviews/final_patch_plan.json` 的字段、`verdict` 和 `target_stage`，再逐项应用并更新 `status`；`accepted` 必须同时写 `resolution_note`。字段缺失时退回 Codex，不得猜测，也不得借机更换模型或新增未验证结果。
2. 检查标题层级、公式、表格、图片相对路径、参考文献、术语、符号和交叉引用。
3. 生成 `paper.md`；可额外生成 `submission_checklist.md` 与 `support_materials_manifest.md`。
4. 确认 `paper.md` 存在后调用 `workflow.py complete`。

## 国奖级交付门

调用 `workflow.py complete` 前必须逐项确认：

- `final_patch_plan.json` 中每一项 `status` 都是 `applied`、`verified` 或 `accepted`，没有遗留 `pending`；其中 `accepted` 仅用于 Stage 5 已明确说明接受理由且无需改动文件的 medium/low 项，不得用来跳过应执行的修改；
- 全文无占位符、`TODO`、`<...>` 模板残留、伪造引用、未验证数字或凭据；
- 公式编号、图号、表号、符号和交叉引用全文连续一致，图片相对路径可解析；
- 正文引用与参考文献一一对应，中文来源保留中文原名；
- `paper.md` 的数字与 `results/` 一致，未在装配阶段引入新结论或新结果。

任一项不满足时先修复；字段缺失或修改单本身有问题则退回 Codex，不得猜测。

## 程序化预检

`workflow.py complete` 会先要求 `paper.md` 存在，再强制执行：

```text
python <skill>/scripts/validate_stage.py --workspace <cwd> --stage 6
```

预检不过则 `complete` 报错，工作流不能标记完成，`workflow.json` 不变。常见失败与修法：

| 报错 | 修法 |
|---|---|
| `paper.md 为空` | 真正装配全文 |
| `final_patch_plan verdict/target_stage 必须是 passed/6` | Stage 5 未放行，退回 Codex |
| `修改项仍为 pending` | 逐项改成 `applied` / `verified` / `accepted` |
| `severity=blocker/high 不得使用 accepted` | 真正修掉；无法修就退回 Codex，不得用 accepted 跳过 |
| `status=accepted 必须填写 resolution_note` | 写明为什么不改也可交付 |
| `paper.md 未以 status=final 登记` | 在 `state/artifact_manifest.json` 登记为 `final` 并写入正确 sha256 |
| 占位符 / 图片路径 / 引用 / 凭据类报错 | 同 Stage 4，全文重新自检 |

预检不判断论文质量高低，只拦可机械发现的交付缺陷。

## 最终边界

Skill 不自动生成最终 Word、WPS 或 PDF，不声称已经满足字体、页边距、分页、页眉页脚等版式要求。用户必须依据实际参赛当届的官方通知手工排版、复核并导出 PDF。

## 验收

- `paper.md` 是唯一论文主交付；
- 不含占位符、伪造引用、未验证数字或密钥；
- 支撑材料清单完整；
- 用户得到清晰的手工排版与提交检查清单。
