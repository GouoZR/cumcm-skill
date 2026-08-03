# 双 Agent 交接协议

## 单写者原则

`state/workflow.json` 是流程唯一真源。任一时刻只有一个 `current_owner`：`claude`、`codex`，完成后为 `user`。非 owner 不得修改共享产物、状态或活动交接单。

每次写状态前必须读取 `revision`，写入时带 `--expect-revision`。若 revision 冲突，停止写入并重新读取，不得强制覆盖。

## 合法流转

```text
Claude 0 → Codex 1 → Claude 2 → Codex 3
                         ↑        ├─ needs_revision ─┘
                         │        └─ passed → Claude 4 → Codex 5
                         │                              ├─ needs_revision → Claude 4
                         │                              └─ passed → Claude 6 → user
```

Stage 3 只能回 Stage 2 或前进 Stage 4；Stage 5 只能回 Stage 4 或前进 Stage 6。

## 交接单

路径：`state/handoffs/H<序号>_<from>_to_<to>.md`。使用 `templates/shared/handoff.md`，必须包括：

- From / To；
- Completed Stage / Next Stage；
- Workflow Revision；
- Acceptance：`passed` 或 `needs_revision`；
- 已完成内容和变更文件；
- 已执行验证；
- 已冻结事实与决策；
- 未解决问题；
- 下一位 Agent 的明确任务；
- 禁止修改的文件；
- 验收说明。

先运行：

```text
python <skill>/scripts/validate_handoff.py <handoff.md> --from <actor> --to <recipient> --next-stage <N>
```

校验通过后再调用 `workflow.py handoff`。交接单中的 revision 是交接前的当前 revision。

`validate_handoff.py` 不只检查标题存在，还拒绝未填写的模板：已完成内容、变更文件、已执行验证、下一位 Agent 任务、验收说明必须有实质内容，写 `<...>` 占位或只写“无”会被判为 `章节未填写` / `章节不得为空占位`。允许显式写“无”的只有已冻结事实与决策、未解决问题、禁止修改的文件。

Completed Stage 为 2 或 4 且 From 为 `claude` 时，还必须填完 `SubAgent 并行产出轨迹` 的四行：`Partitions`、`Main-agent verification`、`Rejected or reworked output`、`Fallback mode`。`Fallback mode` 只能是 `none`、`serial-main-agent` 或 `not-applicable`；填 `none` 表示确实用了 SubAgent，此时 `Partitions` 不得为“无”。没用 SubAgent 就写 `serial-main-agent`，但必须显式写出来。`Main-agent verification` 在 Stage 2/4 不得写“无”。

## 阶段完成预检

Stage 2、4、6 的完成条件由 `scripts/validate_stage.py` 程序化判定，并由 `workflow.py` 强制执行：

```text
python <skill>/scripts/validate_stage.py --workspace <cwd> --stage <2|4|6>
```

| 触发点 | 预检阶段 | 失败后果 |
|---|---|---|
| `handoff` 2→3 | 2 | 命令失败，`workflow.json` 不变 |
| `handoff` 4→5 | 4 | 命令失败，`workflow.json` 不变 |
| `complete`（Stage 6） | 6 | 命令失败，工作流不能标记完成 |
| `handoff` 3→2、5→4 | 不执行 | 退回不跑被退回阶段的完成预检 |

主要失败条件与修法：

- Stage 2：`artifacts/model_spec.md`、`implementation_contract.md`、`model_deviations.md` 缺失；新工作区的 `artifacts/quality_contract.json` 或 `results/result_registry.json` 缺失、未填、逐问 id 不一致、缺 primary 指标，或未登记到 artifact manifest；`artifacts/run_manifest.json` 缺失或未填（`spec_checksum` / `quality_contract_checksum` 为空、`subproblems` 为空）；`run_id` / `input_fingerprint` 与 `workflow.json` 不一致；规格或质量契约 checksum 与实际文件不符；子问题缺 `command`、`seed`、`code`、`results` 或 `figures`；声明的文件不存在或为空。
- Stage 4：`paper_draft.md`、`support_materials_manifest.md` 或 `paper_workspace/*.md` 缺失；正文残留 `TODO` / `FIXME` / `TBD` 或模板占位符；图片相对路径解析不到文件；有标题但正文和子标题都空；正文引用编号在参考文献中没有对应条目；命中凭据模式；引用的图在 manifest 中是 `needs_revision` 或 `stale`。
- Stage 6：`paper.md` 缺失或为空；`reviews/final_patch_plan.json` 不是 `verdict=passed, target_stage=6`；仍有 `pending` 条目；`blocker` / `high` 被写成 `accepted`；`accepted` 没写 `resolution_note`；`paper.md` 未以 `status=final` 登记到 `state/artifact_manifest.json`。

预检只覆盖机器能可靠判定的内容。模型是否正确、结果是否合理、创新点是否成立不在预检范围内，仍由 Codex Stage 3/5 审查；不得把这些包装成硬验证。

## 产物状态

`state/artifact_manifest.json` 的每条产物必须有 `path`、`stage`、`owner`、`status`、`sha256`、`inputs`。`path` 为工作区相对路径且文件必须存在，不得重复登记同一路径；`sha256` 写成 `sha256:<64 位小写十六进制>` 且必须与文件实际哈希一致；`stage` 取 0–6，`owner` 取 `claude` / `codex`。状态为：

- `draft`：尚未审计；
- `verified`：已通过对应审计；
- `needs_revision`：必须返工；
- `stale`：上游规格或输入变化后失效；
- `final`：Stage 6 装配采用。

发生回退时，不直接删除历史产物；将受影响产物标为 `stale` 或 `needs_revision`，新版本使用新文件或更新 manifest。`needs_revision` 和 `stale` 的产物不得作为正式交付件：论文引用了这类图会在 Stage 4 预检失败，`paper.md` 必须在 Stage 6 完成前登记为 `final`。

`artifacts/run_manifest.json` 记录本轮求解的可复现信息：`run_id`、`input_fingerprint`、`spec_checksum`（`model_spec.md` 的哈希）、`quality_contract_checksum`、`result_registry`、`environment`，以及每个子问题的 `id`、`command`、`seed`、`code`、`results`、`figures`。模板初始化后是空壳，Stage 2 预检会因此拒绝流转，必须真实填写。`seed` 为 `null` 表示该子问题确定性求解。启用 `quality_contract_version=1.0` 的新工作区要求质量契约、运行清单和结果注册表的逐问 id 完全一致，且每问至少有一个 primary 指标；旧 v2.0 工作区不强制新增文件。

## SubAgent 报告

Codex Stage 1、3、5 的 SubAgent 报告只是审查证据，不是状态真源：

- SubAgent 不拥有工作流阶段，不修改状态、manifest、共享产物或正式 handoff；
- Codex 主 Agent 核验证据后，将采用的报告保存到 `reviews/subagents/stage_01/`、`stage_03/` 或 `stage_05/`；
- 正式交接单应列出采用的报告、被驳回发现及理由，以及仍未解决的风险；
- 阶段结论由主 Agent 按质量门裁决，不按报告数量或多数票决定。

## 禁止事项

- 依赖复制聊天记录完成交接；
- 非 owner “顺手”修共享文件；
- 静默更换模型、数据口径、目标函数或约束；
- 在交接单中记录密钥；
- 未验证就宣称结果、文献或格式合规。
