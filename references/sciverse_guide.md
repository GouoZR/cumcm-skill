# Sciverse 文献能力指南

Sciverse 是 `cumcm-skill` 的首选文献检索 provider，但在 v2 中属于**按需启用的可选能力**，不是工作流启动条件。具体工具名和接口可能随服务版本变化，运行时以当前宿主实际暴露的 MCP 工具为准。

## 配置原则

1. MCP 只能配置在用户全局作用域，禁止项目级 `.mcp.json`。
2. 凭据只放在宿主支持的用户级安全配置或环境变量中。
3. 不要求用户把 token 粘贴进聊天；不把 token 写入工作区、状态、日志、论文、测试或 handoff。
4. 不要求 Codex 和 Claude Code 都配置。哪一端可用，哪一端执行检索；结果通过工作区共享。
5. `state/capabilities.json` 只记录 `ready`、`unavailable`、`not_checked` 等能力状态，不记录密钥。

## 双 Agent 分工

- **Codex**：将模型与论文中的关键论断拆成查询需求，规定来源层级和验收标准；审查文献是否真正支撑 claim。
- **检索执行宿主**：运行语义检索、元数据检索和原文核验，把结构化记录写入 `literature/`。
- **Claude Code**：只把已经核验、已映射到 claim 的文献写入论文，保持正文引用与参考文献一致。

## 工作区文件

```text
literature/
├── query_plan.json       # Stage 1 的主题、关键词、来源和证据需求
├── queries.jsonl         # 实际查询及时间、provider、结果数
├── library.json          # 去重后的文献元数据与证据等级
├── claim_map.json        # 论文论断到文献证据的映射
├── rejected.json         # 拒绝原因：不相关、不可核验、来源过弱等
└── notes/                # 原文摘记；不得保存无授权的完整受限文本
```

每条 `library.json` 记录至少包含：

- `id`, `title`, `authors`, `year`, `venue`；
- `language`, `source_type`, `provider`；
- `doc_id` 或 `doi`；
- `retrieved_at`；
- `evidence_level`：`metadata_only` / `abstract` / `full_text` / `official_document`；
- `metadata_verified`, `content_verified`。

`claim_map.json` 的每条支持关系必须记录 `record_id` 和页码、章节或摘要位置 `locator`。

## 国内来源优先级

1. 官方政策、国家标准、行业规范和权威统计；
2. 国内同行评审期刊；
3. 与场景直接相关的学位论文；
4. 国内会议论文或权威研究报告；
5. 国外高质量论文；
6. 普通网页只作背景，不承担核心方法或结论证明。

中文来源的题名和机构名应保留官方中文原文，不把英文转译名当作原始题名。

## 检索流程

1. 从 `model_spec.md` 和论文大纲提取少量关键 claim。
2. 为每个 claim 设计中文、英文和中英混合查询；记录年份、领域、文献类型等筛选条件。
3. 先搜综述、经典方法和国内权威来源，再搜题目场景和参数细节。
4. 按 DOI、doc_id 和规范化题名去重。
5. 对关键记录读取摘要或原文片段，核对作者、题名、年份、期刊以及具体论断。
6. 将不能核验、只看标题、与场景不符或来源太弱的记录写入 `rejected.json`。
7. 运行：

```text
python <skill>/scripts/validate_literature.py \
  --library <cwd>/literature/library.json \
  --claim-map <cwd>/literature/claim_map.json
```

## 证据边界

- `metadata_only` 只能证明“存在这篇文献”，不能证明方法有效、参数合理或结论成立。
- 摘要证据只能支撑摘要明确表达的内容；细节、参数和限制应查看全文。
- 不因来源是中文就自动判定权威，也不以文献数量替代相关性和证据强度。
- 服务不可用时，继续建模；最终写作可使用用户提供且可核验的来源或官方材料，但绝不伪造引用。
