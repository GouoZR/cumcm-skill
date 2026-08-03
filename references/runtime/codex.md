# Codex Runtime Adapter

Codex 在共享工作流中的身份固定为 `codex`，负责 Stage 1、3、5。

## 启动

1. 从用户当前工作目录定位 `state/workflow.json`；不存在时不要替 Claude 执行 Stage 0，提示用户先在 Claude Code 中初始化，或仅在用户明确要求时创建工作区。
2. 运行 `python <skill>/scripts/workflow.py --workspace <cwd> status`。
3. 仅当 `current_owner == "codex"` 时执行；否则只报告下一位负责人和活动交接单，不修改共享产物。
4. 开始阶段时使用当前 revision 调用 `workflow.py ... start --actor codex --expect-revision N`。
5. 读取 `active_handoff`、本阶段说明及其明确列出的输入，不依赖另一客户端的聊天记录。

## 工作边界

- Codex负责模型规格、推理审计、结果审计和论文终审。
- 原则上输出规格或结构化修改单，不大面积接管 Claude 的实现或论文正文。
- 若需要子 Agent，只能在当前 Codex 阶段内部使用；对共享工作区仍由 `codex` 单一 owner 负责。
- 交接前生成并校验 handoff；状态更新必须带 revision，冲突后重新读取，不覆盖。

## 外部能力

- 文献检索按 `state/capabilities.json` 执行。Codex 可以设计查询和证据需求，也可以在自身可用时执行检索。
- MCP 配置只能位于用户全局作用域；不得创建项目级 `.mcp.json`。
- 不在聊天、状态、日志、论文或交接单中记录 token/API key。
