# Claude Code Runtime Adapter

Claude Code 在共享工作流中的身份固定为 `claude`，负责 Stage 0、2、4、6。

## 启动

1. 从用户当前工作目录定位 `state/workflow.json`；不存在时运行 `python <skill>/scripts/init_workspace.py <cwd>`。
2. 运行 `python <skill>/scripts/workflow.py --workspace <cwd> status`。
3. 仅当 `current_owner == "claude"` 时执行；否则只报告下一位负责人和活动交接单，不修改共享产物。
4. 开始阶段时使用当前 revision 调用 `workflow.py ... start --actor claude --expect-revision N`。
5. 读取 `active_handoff`、本阶段说明及其明确列出的输入，不依赖另一客户端的聊天记录。

## 工作边界

- Claude负责题面和附件落盘解析、工程实现、求解、结果生成、Markdown 写作与最终装配。
- Stage 0 只建立事实框架，不提前冻结正式模型。
- 不得静默改变 Codex 的模型规格；必要调整写入 `artifacts/model_deviations.md`，说明原因、影响和验证。
- 只有已验证的结果和文献可以进入论文。
- 若使用内部子 Agent，对共享工作区仍由 `claude` 单一 owner 负责。

## 外部能力

- Sciverse 和 PackyAPI 都是可选增强项，不得阻断无关阶段。
- MCP 配置只能位于用户全局作用域；不得创建项目级 `.mcp.json`。
- 不要求用户把 token/API key 粘贴到聊天；凭据只保存在宿主支持的用户级安全配置或环境变量中。
