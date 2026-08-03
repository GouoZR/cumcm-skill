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

## 产物状态

`state/artifact_manifest.json` 记录关键产物的路径、生成阶段、owner、输入依赖、校验和与状态。建议状态为：

- `draft`：尚未审计；
- `verified`：已通过对应审计；
- `needs_revision`：必须返工；
- `stale`：上游规格或输入变化后失效；
- `final`：Stage 6 装配采用。

发生回退时，不直接删除历史产物；将受影响产物标为 `stale` 或 `needs_revision`，新版本使用新文件或更新 manifest。

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
