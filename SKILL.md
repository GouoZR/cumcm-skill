---
name: cumcm-skill
description: CUMCM 全国大学生数学建模竞赛端到端协作工作流。Use when a user explicitly works on CUMCM (国赛/全国大学生数学建模竞赛) or asks to run/review a CUMCM paper from problem selection through modeling, solving, robustness, writing, compliance, and final submission review. Provides 10 stages, persistent decision state, competition-specific rules/templates, deterministic scoring helpers, numbered decisions, Sciverse academic literature search, multi-Agent parallel solving/writing, and Markdown+DOCX output. Claude Code only. Do not trigger for generic model selection, ordinary data analysis, or non-CUMCM paper review.
---

# cumcm-skill — CUMCM 国赛数学建模工作流 (v7.0)

10 阶段把 72 小时的国赛协作变成可恢复、可检查的流程。用户回答关键问题，Agent 维护状态与脚本。每阶段产出经过 rubric 自评、定向精修与跨阶段一致性回检；Stage 8–9 先遵守当届官方规则，再做多视角终审。

**v7.0 更新**: 专精 CUMCM 国赛，移除多竞赛/多 CLI 兼容层；Markdown + DOCX 输出管线替代 LaTeX；集成 Sciverse MCP 真实文献检索，全阶段可溯源引用；支持多 Agent 并行求解/写作/文献查阅；PackyAPI gpt-image-2 概念图 + Python 数据图双轨图表系统。

---

## 平台要求

| 项目 | 说明 |
|---|---|
| **运行环境** | Claude Code (唯一支持) |
| **用户交互** | `AskUserQuestion` 工具 |
| **文献检索** | Sciverse MCP Server (`npx -y sciverse-mcp-server`) |
| **AI 概念图** | gpt-image-2 (PackyAPI: `POST /v1/images/generations`) |
| **数据图** | matplotlib / plotly (Python 脚本) |
| **输出格式** | Markdown (`paper.md`) → pandoc → DOCX (`paper.docx`) |
| **状态持久化** | `<cwd>/state/decision_log.json` |

---

## 问答式优先 (Friendly Mode)

**核心原则**: 用户只需回答**编号问题**，不应被要求手敲 bash / python / json。

- 离散选项 (选题 / 选模型 / verdict 决策) → **必须**用 `AskUserQuestion`
- 自由文本 (PDF 路径 / 截止时间) → 单行回复
- 状态读写 (decision_log.json) → Agent 自动完成
- 每个 stage 的关键决策点都有 "让我决定 (推荐 X)" 兜底选项

---

## 路径解析协议 (任何阶段必读)

| 类型 | 位置 | 例 |
|------|------|-----|
| skill 内通用 | skill 根目录的相对路径 | `references/stage_05_subproblem_loop.md`, `templates/shared/decision_log.json` |
| 竞赛特化 | `competitions/cumcm/...` | `competitions/cumcm/winning_patterns.md` |
| 算法参考 | `references/algorithms/...` | `references/algorithms/01-优化算法说明.md` |
| 写作规范 | `references/writing/...` | `references/writing/写作规范.md` |
| 可视化规范 | `references/visualization/...` | `references/visualization/可视化规范.md` |
| 文献检索 | `references/sciverse_guide.md` | Sciverse MCP 接入指南 |
| 用户产物 | 用户工作目录的相对路径 | `<cwd>/state/`, `<cwd>/results/`, `<cwd>/figures/`, `<cwd>/paper_workspace/` |
| state 持久化 | `<cwd>/state/decision_log.json` | 各 stage 必读必写 |
| 环境变量 | `MATHMODEL_STATE_DIR`（兼容 `CUMCM_STATE_DIR`）/ `SCIVERSE_API_TOKEN` / `PACKYAPI_TOKEN` | scripts 路径解析与外部服务 |

约定: `<skill>/` = skill 安装目录 (`~/.claude/skills/cumcm-skill/`), `<cwd>/` = 用户 cwd。

---

## Quick Start (用户说"开始建模" / "打国赛" / "CUMCM")

```
1. 一段话介绍 (≤50 字): "CUMCM 国赛建模工作流, 10 阶段 + Sciverse 文献 + 多 Agent 并行, 全程问答式."

2. 收集启动字段；已提供或 state 已记录的字段不再询问，只把尚缺字段合并成一轮 AskUserQuestion:
   - 题号 (A-F; "未公布"亦可)
   - 队员数 + 各人擅长 (建模/编程/写作)
   - 截止时间 (ISO 字符串或 "距现在 X 小时")
   - 题目 PDF 路径 ("未公布"亦可)

3. 自动初始化 (Agent 自动完成):
   - 不存在 `<cwd>/state/decision_log.json` → 创建目录并复制 `<skill>/templates/shared/decision_log.json`
   - 写入 decision_log.competition = "cumcm"
   - 已存在 → 读 current_stage 字段决定恢复点

4. 加载 `competitions/cumcm/current_rules.md`，打开其中官方链接核对当届规则；再加载 winning_patterns

5. 进入 Stage 0 (`references/stage_00_kickoff.md`)，若题面未公布则等待
```

**已有 state 触发** (用户中途回到 skill):
```
1. 读 `<cwd>/state/decision_log.json` 的 current_stage
2. 加载对应 stage_NN.md
3. 不重复读 winning_patterns
```

---

## 三模式

| Mode | 上下文策略 | 反馈层 | 用途 |
|---|---|---|---|
| fast | 只保留当前阻断项与最小证据 | L1 单次 | 选题试跑 / sanity check |
| standard | 按阶段加载并保留决策摘要 | L1+L2 | 默认主流程 |
| championship | 扩展证据与独立视角 + 多 Agent | L1+L2+L3+L4 + red-team | 提交前最后冲刺 |

模式自动推荐 (按距 deadline 剩余):
- > 48h: standard (最后 6h 升 championship)
- 12-48h: standard
- 6-12h: fast 关键阶段 + championship 终审
- < 6h: 直接进 stage 9 (championship)

---

## 10 阶段索引

| # | 阶段 | reference | 时长 | 反馈 | 说明 |
|---|------|-----------|------|------|------|
| 0 | 团队启动 + 资料预扫 | `stage_00_kickoff.md` | 1h | L1 | 环境准备、Sciverse 背景调研 |
| 1 | 选题 (多题对比 → 1) | `stage_01_problem_selection.md` | 2-4h | L1 | 5 维矩阵 + Sciverse 文献辅助 |
| 2 | 问题深度解析与分解 | `stage_02_analysis.md` | 2-3h | L1 | 子问题拆解 |
| 3 | 模型选型 | `stage_03_model_selection.md` | 2-4h | L1 + 反事实 | 算法库 + Sciverse 文献验证 |
| 4 | Foundation (假设+符号+术语) | `stage_04_foundation.md` | 1h | L1 | 假设表 + 符号表 |
| 5 | **递归子问题循环** | `stage_05_subproblem_loop.md` | 按题目分配 | L1 + 子检查点 | **多 Agent 并行求解** |
| 6 | 全局灵敏度 / 稳健性 | `stage_06_robustness.md` | 2-3h | L1 + L2 | Tornado 图 |
| 7 | 模型评价 + 推广 | `stage_07_evaluation.md` | 1-2h | L1 | 优点/缺点/推广 |
| 8 | 论文写作 + 图表生成 | `stage_08_writing.md` | 12-20h | L1 + L2 | **多 Agent 并行写作 + 双轨图表** |
| 9 | 提交合规 + Panel | `stage_09_review.md` | 2-6h | L1 + L3 | 规则合规门 + 多视角终审 |

---

## 多 Agent 并行架构

在 Stage 5 和 Stage 8 通过 Claude Code `Agent` 工具派发子任务:

### Stage 5 — 求解并行

```
主 Agent (协调)
  ├── 求解 Agent 1 → Q1 建模 + 代码 + 结果
  ├── 求解 Agent 2 → Q2 建模 + 代码 + 结果  
  ├── 求解 Agent 3 → Q3 建模 + 代码 + 结果
  └── 文献 Agent   → Sciverse 检索各 Qi 相关文献
```

### Stage 8 — 写作并行

```
主 Agent (装配 + 一致性检查)
  ├── 写作 Agent 1 → §1-4 (问题重述→符号说明)
  ├── 写作 Agent 2 → §5 (模型建立与求解，主体)
  ├── 写作 Agent 3 → §6-7 (灵敏度+评价推广)
  ├── 文献 Agent   → §8 参考文献核验 (Sciverse 溯源)
  └── 图表 Agent   → 数据图 (matplotlib) + 概念图 (gpt-image-2)
```

详细分派协议见 `references/stage_05_subproblem_loop.md` 和 `references/stage_08_writing.md`。

---

## 图表系统 (双轨制)

| 图表类型 | 工具 | 格式 | 用途 |
|---|---|---|---|
| **数据图** | matplotlib / plotly (Python) | PNG ≥300 DPI + SVG | 折线图、柱状图、热力图、Tornado、散点等 |
| **概念图** | gpt-image-2 (PackyAPI) | PNG | 系统架构图、算法流程示意、问题场景图 |

概念图调用封装在 `scripts/generate_concept_image.py`，通过 PackyAPI (`POST /v1/images/generations`) 生成。环境变量 `PACKYAPI_TOKEN` 需提前配置。

---

## 加载协议

**只在进入阶段 N 时加载** `references/stage_NN_*.md`。**切勿**一次性全读。

各阶段额外加载:
- 每阶段开头/结尾: `<cwd>/state/decision_log.json` 必读/必写
- stage 1-9: `references/rubrics.md` 对应章节
- **stage 1**: `competitions/cumcm/topic_specs.json`
- **stage 3**: `competitions/cumcm/distilled_naming.md` (按需: 命名变体模板, 与 winning_patterns §4 互补)
- stage 3, 5: `references/model_catalog.md` + `references/algorithms/` 对应算法
- **stage 5**: per-Qi 评分后调 `scripts/score_artifact.py --mode aggregate_qi`
- **stage 0/8/9**: `competitions/cumcm/current_rules.md`
- **stage 8**: `competitions/cumcm/{winning_patterns, phrase_bank, abstract_template, paper_skeleton}.md`
- **stage 8** (按需): `competitions/cumcm/distilled_{phrases,structures,formats}.md` (段落/结构/格式模板, 与 phrase_bank/paper_skeleton 互补)
- **stage 8**: `references/writing/{写作规范, 章节模板, 自审框架}.md`
- **stage 8**: `references/visualization/{可视化规范, 图表选择与避坑}.md`
- **stage 8**: `competitions/cumcm/empirical.json` (59 份样本观察分位)
- **stage 8**: `references/sciverse_guide.md` §Stage_8
- **stage 9**: `anti_patterns.md` + `rubric_overlay.json` panel personas
- 触发反馈时: 对应 `references/feedback_layer*.md`

---

## 收敛准则

| verdict | 触发 | 行为 |
|---------|------|------|
| `block` | issues 含 ≥1 high-severity | 暂停, 用户介入 |
| `pass_early` | raw_min ≥ 9 AND weighted_mean ≥ 9 | iter-1 早退 |
| `pass` | raw_min ≥ 7 AND weighted_mean ≥ 8 | 进下一阶段 |
| `pass_with_review` *(stage 5)* | 任 Qi mark_for_review 但加权满足 | 进 stage 6, L2 读 review_qis |
| `refine` | 其他 | section-patch 精修, iter+=1 (cap 3) |
| `refine_partial` *(stage 5)* | 任 Qi.min < 7, 其他已 pass | 仅 refine 该 Qi |
| `carryover` | iter == 3 仍 refine | 进下一阶段, L2 标记 |

`weighted_mean` = Σ(s_i × w_i) / Σ(w_i), 权重来自 `config/dim_weights.json[cumcm][<task_type>]`。

---

## 状态持久化

每阶段开头读、结尾写 `<cwd>/state/decision_log.json`。

关键字段 (v3.1 schema):
- root: `competition`, `task_type`, `mode`, `current_stage`, `budget`, `events`, `compliance`
- stage_5 扩展: `qi_count`, `qi_weights`, `qi_status`
- scores 扩展: `weighted_mean`, `review_qis`, `refine_qis`
- 文献扩展: `sciverse_queries` (检索历史去重)

---

## 上下文预算纪律

- L1 Critic 强制 JSON 输出, ~500 token/次
- 精修策略: section-level patch, 优先只传相关 section
- references/ 与 competitions/ 文件**懒加载**
- 阶段完成后, artifact 摘要 + 路径写入 decision_log
- 多 Agent 并行时，子 Agent 独立上下文，结果通过 decision_log 汇聚
- 必要时建议 championship → standard → fast 降级

---

## 用户指令快捷

- "进入 stage N" / "重做 stage N" → 跳转
- "升级到 championship" → L3 + L4 + red-team + 多 Agent
- "切到 fast" → 关闭迭代和多 Agent 并行
- "回退到 stage M" → 回退 current_stage 并清理 ≥M 节点
- "做 L2 回检" → 立即触发 cross-stage backtrack
- "看进度" → 输出 decision_log 摘要 + 当前评分
- "并行求解" / "串行求解" → 切换 Stage 5 Agent 模式

---

## 数据来源声明

- `competitions/cumcm/`: 91 份来源文档，59 份文本提取进入观察分位；非官方阈值
- `references/model_catalog.md` 跨 task_type 复用
- `references/algorithms/` 为维护者整理的参考资料
- Sciverse: MCP 实时检索，`doc_id` + `offset` 可溯源；中文文献覆盖较少
- gpt-image-2: PackyAPI 中转，概念图/流程图生成

---

## 外部资源

- 国赛官方: `dxs.moe.gov.cn` 优秀论文展廊
- Sciverse: `sciverse.space` (MCP Server, 4.66 亿学术元数据)
- 概念图: PackyAPI (`packyapi.com`) gpt-image-2
- 社区: `personqianduixue/Math_Model`, `datawhalechina/intro-mathmodel`
