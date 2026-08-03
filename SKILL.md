---
name: cumcm-skill
description: "CUMCM 全国大学生数学建模竞赛的 Codex + Claude Code 双 Agent 接力工作流。Use when the user explicitly works on CUMCM/国赛 and wants problem intake, mathematical modeling, implementation, result auditing, Markdown paper writing, literature evidence checking, or final review. Coordinates seven file-based stages through a shared workspace: Claude Code handles intake, implementation, writing, and delivery; Codex handles model design and audits. Produces paper.md only. Do not trigger for generic data analysis, ordinary academic writing, or non-CUMCM tasks."
---

# cumcm-skill v2.0

把 CUMCM 项目组织为 **Claude Code 与 Codex 共用同一 Skill、依靠共享文件轮流接力**的 7 阶段流程。聊天记录不是接口；`state/workflow.json`、阶段产物和 handoff 才是接口。

## 不可违反的原则

1. **单一真源**：两个宿主应指向同一份 Skill 安装目录，不维护相互复制的独立版本。
2. **单一 owner**：只有 `current_owner` 可以修改共享状态和产物；另一 Agent 只报告应由谁继续。
3. **文件化交接**：下一位 Agent 只依赖工作区文件，不要求用户复制上一个聊天的上下文。
4. **最少设问**：默认扫描用户已放入 `input/` 的题面和附件。只有缺少真正阻断输入或存在多个无法区分的题目版本时，才问一个必要问题。
5. **职责分离**：Claude偏实践与写作，Codex偏建模推理与审计。任何模型偏离必须显式记录。
6. **外部能力可选**：Sciverse 文献检索和 PackyAPI 生图不可用时，不阻断无关建模阶段。
7. **唯一论文交付**：最终交付 `paper.md`；Word/WPS 排版、PDF 转换和当届格式核验由用户完成。
8. **高质量而非奖项承诺**：按可复现、逐问闭环和强证据链的国奖级目标执行，但不保证奖项，不把历史模式当官方阈值。

## 宿主适配

先判断当前宿主并只加载对应说明：

- Codex：`references/runtime/codex.md`
- Claude Code：`references/runtime/claude_code.md`

若无法判断，允许用户明确说“以 codex 身份继续”或“以 claude 身份继续”。宿主身份只允许为 `codex` 或 `claude`。

## 启动与恢复

在用户的建模项目目录执行：

1. 查找 `state/workflow.json`。
2. 不存在时，由 Claude 初始化：
   `python <skill>/scripts/init_workspace.py <cwd>`
3. 读取状态：
   `python <skill>/scripts/workflow.py --workspace <cwd> status`
4. 检查 `current_owner` 是否等于当前宿主身份。
5. 若匹配，读取 `active_handoff` 和当前阶段文件；以当前 revision 调用 `workflow.py start`。
6. 完成本阶段产物、验证、artifact manifest 和 handoff；校验交接单后调用 `workflow.py handoff`。
7. revision 冲突时停止写入，重新读取状态；不得覆盖另一 Agent 的修改。

工作区已有状态时直接恢复，不重复询问题号、队伍人数、成员分工、截止时间或 fast/standard/championship 模式。

## 7 阶段职责

| Stage | Owner | 任务 | 阶段文件 |
|---|---|---|---|
| 0 | Claude | 题面解析、附件清点、初始框架 | `references/workflow/stage_00_claude_intake.md` |
| 1 | Codex | 查漏补缺、正式模型、实现契约、文献计划 | `references/workflow/stage_01_codex_modeling.md` |
| 2 | Claude | 数据处理、代码实现、求解、结果与图表 | `references/workflow/stage_02_claude_implementation.md` |
| 3 | Codex | 模型—代码—结果一致性与稳健性审计 | `references/workflow/stage_03_codex_audit.md` |
| 4 | Claude | 基于已验证产物撰写 Markdown 论文 | `references/workflow/stage_04_claude_writing.md` |
| 5 | Codex | 论文逻辑、数学、结果和文献终审 | `references/workflow/stage_05_codex_final_review.md` |
| 6 | Claude | 应用修改单并装配最终 `paper.md` | `references/workflow/stage_06_claude_delivery.md` |

合法流转和交接格式见 `references/handoff_protocol.md`。Stage 3 不通过退回 Stage 2；Stage 5 不通过退回 Stage 4。

两个宿主都可以在自己的阶段内使用 SubAgent，但 `current_owner` 不变，主 Agent 必须亲自完成关键路径、核验证据和最终裁决，不得新增 SubAgent 状态机：

- Codex 在 Stage 1、3、5 做只读专家审查，按需加载 `references/runtime/codex_subagents.md`；
- Claude 在 Stage 2、4 按子问题或章节做独占路径并行产出，按需加载 `references/runtime/claude_subagents.md`；Stage 0、6 默认串行。

## 共享工作区

```text
<cwd>/
├── input/                      # 用户放置题面和附件
├── state/
│   ├── workflow.json           # 唯一流程状态，schema 4.0
│   ├── capabilities.json       # 可选能力状态，不含密钥
│   ├── artifact_manifest.json
│   └── handoffs/
├── artifacts/                  # 问题分析、模型规格、实现契约、运行清单
├── literature/                 # 查询计划、文献库、claim map、笔记
├── code/
├── results/
├── figures/
├── reviews/
│   └── subagents/               # Codex 内部专家报告，不是流程状态
├── paper_workspace/
├── paper_draft.md
└── paper.md
```

旧 v1 `state/decision_log.json` 和 10 阶段资料只用于兼容旧项目；v2 新项目以 `workflow.json` 和 `references/workflow/` 为准。

## 文献能力：保留但解耦

读取 `state/capabilities.json`：

- Codex负责定义查询词、权威来源优先级和需要支撑的 claim；
- 哪一宿主可用 Sciverse，哪一宿主执行检索并把结果写入 `literature/`；
- Claude只把已验证文献写入论文；Codex审查元数据、证据等级和 claim 对应关系；
- 仅有标题或 metadata 的记录不得用来证明实质结论；
- 优先级：官方政策/国家标准/行业规范 → 国内同行评审期刊 → 场景相关学位论文 → 国内会议或研究报告 → 国外高质量论文 → 普通网页背景材料；
- 在最终引用前运行 `scripts/validate_literature.py`。

Sciverse MCP 不是启动硬依赖。MCP 只能配置到用户全局作用域，禁止创建项目级 `.mcp.json`。不得要求用户把 API key/token 粘进聊天，也不得把凭据写入工作区、日志、论文或交接单。

## 图表与可选生图

优先级：**Python 数据图 > Mermaid/SVG 技术图 > AI 概念图**。

PackyAPI 默认关闭，只有用户明确要求概念图时才检查能力。AI 图不得承载关键公式、参数、数字或唯一算法说明；不可用时继续使用可复现技术图，不阻断流程。

## 加载纪律

每次只加载：

1. 当前 runtime adapter；
2. `state/workflow.json` 与 `active_handoff`；
3. 当前阶段文件；
4. 当前阶段明确需要的算法、写作、可视化或竞赛资料。

不要一次加载全部参考资料。官方规则具有时效性；提交前核验 `competitions/cumcm/current_rules.md` 的核验日期和当届官方原文，官方材料始终覆盖仓库经验。

## 完成边界

Stage 6 只能在 `paper.md` 存在后标记完成。可附带：

- `submission_checklist.md`
- `support_materials_manifest.md`

不得自动宣称字体、页边距、分页、页眉页脚或 PDF 已符合当届要求。最终人工校核、排版、导出和提交责任属于参赛团队。
