# cumcm-skill v7.0

> CUMCM 全国大学生数学建模竞赛端到端 Claude Code Skill — 10 阶段把 72 小时竞赛变成可恢复、可检查的流程。

基于 [mathmodel-skill](https://github.com/handsomeZR-netizen/mathmodel-skill) (v6.1.0, 作者: 徐子锐) 深度定制。专精 CUMCM 国赛，Claude Code 独占，Markdown + DOCX 输出。

---

## 快速开始

```bash
# 安装位置
~/.claude/skills/cumcm-skill/

# 前置：Sciverse 学术文献 MCP
npm install -g sciverse-mcp-server
claude mcp add -s user sciverse -- sciverse-mcp-server

# 前置：环境变量（配在 ~/.claude/settings.json 的 env 字段）
SCIVERSE_API_TOKEN="你的Sciverse Token"   # https://sciverse.space/tokens
PACKYAPI_TOKEN="你的PackyAPI Sora令牌"   # https://www.packyapi.com

# 启动 — 在 Claude Code 中说:
"开始建模" / "打国赛" / "CUMCM"
```

---

## 架构总览

```
用户 ←→ SKILL.md (主入口, 10 阶段定义)
         ↓ 懒加载
      references/stage_00~09  (阶段细则, 按需加载)
         ↓ 读写
      state/decision_log.json (跨阶段持久化状态)
         ↓ 依赖
      ┌─────────────────────────────────────┐
      │ competitions/cumcm/  (国赛规则/模板/经验)  │
      │ references/algorithms/  (7类60+算法)     │
      │ references/visualization/  (数据图规范)    │
      │ references/writing/  (写作规范/自审)      │
      │ references/sciverse_guide.md  (文献MCP)   │
      └─────────────────────────────────────┘
         ↓ 外部服务
      ┌─────────────────────────────────────┐
      │ Sciverse MCP   — 4.66亿学术文献检索    │
      │ PackyAPI REST  — gpt-image-2 概念图    │
      │ MCP web-search — 通用网页搜索          │
      └─────────────────────────────────────┘
```

### 设计原则

- **懒加载**：只在进入阶段 N 时加载对应 stage 文件，不一次全读
- **状态持久化**：所有关键决策写入 `decision_log.json`，换模型/重启不丢进度
- **问答式**：用户只回答编号问题，不手敲 JSON/bash/Python
- **多 Agent 并行**：Stage 5（求解）和 Stage 8（写作）可拆分为多个子 Agent 并行
- **Markdown 优先**：论文全程 Markdown 写作，最后 pandoc 转 DOCX

---

## 完整的文件清单与用途

### 根目录入口

| 文件 | 用途 | 何时读 |
|------|------|--------|
| `SKILL.md` | 主工作流定义，Claude Code 入口 | 用户说"开始建模"时加载 |
| `AGENTS.md` | 维护者指南，说明如何修改本 skill | 维护/二次开发时 |
| `README.md` | 本文件 | 新会话了解全貌 |
| `LICENSE` | MIT 许可证 | — |

### competitions/cumcm/ — 国赛特化层（15 个文件）

| 文件 | 用途 | 关键信息 |
|------|------|---------|
| `README.md` | 国赛基本信息（时长/语言/题号体系） | 72h，中文，A-F 题号路由（有效题号以当届题面为准） |
| `current_rules.md` | 2026 当届官方规则链接 | Stage 0/9 必读，核对不失效 |
| `topic_specs.json` | 题号 → task_type 映射 | Stage 1 选题路由 |
| `winning_patterns.md` | 获奖论文写作模式 | Stage 8 写作锚点 |
| `empirical.json` | 59 份样本的观察分位数据 | 评分参考，不是官方阈值 |
| `empirical_notes.md` | 样本来源与提取限制说明 | 理解数据边界 |
| `phrase_bank.md` | 中文学术句式库 | Stage 8 写作参考 |
| `anti_patterns.md` | 42 条启发式检查项 | Stage 9 终审对照 |
| `paper_skeleton.md` | Markdown 论文骨架（占位符模板） | Stage 8 写作结构 |
| `abstract_template.md` | 5 段式摘要模板 | Stage 8 写摘要 |
| `rubric_overlay.json` | 国赛特化评分维度 | score_artifact.py 加载 |
| `distilled_phrases.md` | 段落模板 | Stage 8 |
| `distilled_structures.md` | 章节结构模板 | Stage 8 |
| `distilled_naming.md` | 命名变体 | Stage 3 |
| `distilled_formats.md` | 格式细节 | Stage 8/9 |

### references/ — 10 阶段细则 + 反馈层（20+ 个文件）

| 文件 | 阶段 | 核心内容 |
|------|------|---------|
| `stage_00_kickoff.md` | 0 | 团队启动、环境检查、题目预扫 |
| `stage_01_problem_selection.md` | 1 | 五维选题矩阵 + Sciverse 文献辅助 |
| `stage_02_analysis.md` | 2 | 问题分解、子问题卡片 |
| `stage_03_model_selection.md` | 3 | 模型候选比较、算法库参考、文献验证 |
| `stage_04_foundation.md` | 4 | 假设表、符号表、术语表 |
| `stage_05_subproblem_loop.md` | 5 | **多 Agent 并行求解** Q1..Qn |
| `stage_06_robustness.md` | 6 | 灵敏度/稳健性分析 |
| `stage_07_evaluation.md` | 7 | 模型优点/缺点/推广 |
| `stage_08_writing.md` | 8 | **多 Agent 并行写作 + 双轨图表** |
| `stage_09_review.md` | 9 | 规则合规门 + Panel 多视角终审 |
| `feedback_layer1_critic.md` | 全阶段 | L1 单阶段评分 + JSON 输出协议 |
| `feedback_layer2_backtrack.md` | 全阶段 | L2 跨阶段回检 |
| `feedback_layer3_panel.md` | Stage 9 | L3 多视角 Panel 评分 |
| `feedback_layer4_calibration.md` | Stage 9 | L4 校准 + red-team |
| `rubrics.md` | 全阶段 | 5 维评分细则 |
| `model_catalog.md` | Stage 3/5 | 跨 task_type 模型目录 |
| `sciverse_guide.md` | 全阶段 | Sciverse MCP 接入与各阶段集成指南 |

### references/ — 定制增强（v7.0 新增）

| 目录/文件 | 内容 | 用途 |
|----------|------|------|
| `algorithms/` | 7 个 Markdown 文件 + README | 60+ 算法详解（优化/预测/评价/图论/统计/综合/ML） |
| `visualization/可视化规范.md` | SCI/Nature 级图表标准 | 数据图规范（配色/字体/分辨率） |
| `visualization/图表选择与避坑.md` | 图型选择决策树 | 什么数据该用什么图 |
| `visualization/plot_style.py` | Python 出版级样式 | matplotlib 全局样式 |
| `visualization/figure_audit.py` | 图表质量审计脚本 | 检查图表合规性 |
| `visualization/repro_manifest.py` | 图表复现清单 | 记录生成参数确保可复现 |
| `writing/写作规范.md` | 通用论文写作标准 | 语言/格式/引用规范 |
| `writing/章节模板.md` | 各章节详细模板 | 每节写什么、怎么写 |
| `writing/自审框架.md` | 提交前自审清单 | Stage 8/9 逐项检查 |
| `writing/论文格式规范.md` | Word/PDF 格式规范 | DOCX 输出格式要求 |

Markdown → DOCX 转换由系统 Pandoc 完成（见 `stage_08_writing.md` §8 与 `references/writing/论文格式规范.md`）；不依赖仓库内模板目录。

### scripts/ — 工具脚本（5 个活跃 + 3 个维护用）

| 脚本 | 状态 | 用途 |
|------|------|------|
| `doctor.py` | ✅ 活跃 | 赛前 preflight 检查（环境/依赖/结构） |
| `score_artifact.py` | ✅ 活跃 | L1 Critic 结果处理、verdict 计算、per-Qi 聚合 |
| `extract_diff.py` | ✅ 活跃 | Section-level diff，定向精修 |
| `render_ai_usage.py` | ✅ 活跃 | 生成 AI 使用披露文件 |
| `generate_concept_image.py` | ✅ v7.0 新增 | gpt-image-2 概念图生成（PackyAPI） |
| `download_cumcm_papers.py` | 📦 维护用 | 下载官方展廊论文（非竞赛时使用） |
| `ingest_papers.py` | 📦 维护用 | 论文文本提取和统计（非竞赛时使用） |
| `requirements-maintenance.txt` | 📦 维护用 | 维护工具依赖 |

### 其他目录

| 目录 | 内容 | 用途 |
|------|------|------|
| `config/dim_weights.json` | CUMCM 题型加权配置 (A-E; 题型以当届为准) | score_artifact.py 加权用 |
| `templates/shared/` | decision_log / 代码模板 / 表格模板 | 各阶段初始化时复制 |
| `state/` | .gitkeep | 运行时状态目录（用户项目下） |
| `tests/` | Python 测试套件 | 维护时验证不破坏功能 |
| `skills/mathmodel-skill/` | 已删除 | v6.0 Codex shim，v7.0 移除 |
| `.codex-plugin/` | 已删除 | v6.0 Codex 插件，v7.0 移除 |
| `agents/` | 已删除 | v6.0 OpenAI agent 配置，v7.0 移除 |
| `competitions/mcm/` | 已删除 | 美赛，v7.0 移除 |
| `competitions/diangong/` | 已删除 | 电工杯，v7.0 移除 |
| `templates/latex/` | 已删除 | LaTeX 模板目录，v7.0 移除 |
| `.github/` | 已删除 | CI 流水线，v7.0 移除 |

---

## 外部服务依赖

### 1. Sciverse MCP — 学术文献检索

| 项目 | 值 |
|------|-----|
| 安装方式 | `npm install -g sciverse-mcp-server` + `claude mcp add` |
| Token | `SCIVERSE_API_TOKEN` 环境变量 |
| 费用 | 免费（需注册） |
| 速率限制 | 60 req / 60s |
| 数据规模 | 4.66亿元数据 + 2800万 OA 全文 |

**可用工具**：`semantic_search` / `search_papers` / `read_content` / `list_paper_relations` / `list_catalog` / `get_resource`

**集成点**：Stage 0（背景调研）→ Stage 1（选题辅助）→ Stage 3（模型验证）→ Stage 5（求解文献）→ Stage 8（引用核验）

### 2. PackyAPI gpt-image-2 — AI 概念图

| 项目 | 值 |
|------|-----|
| 接入方式 | REST API (`POST /v1/images/generations`) |
| Token | `PACKYAPI_TOKEN` 环境变量（Sora 分组） |
| 费用 | 按次计费，约 $0.006~$0.712/次 |
| 封装脚本 | `scripts/generate_concept_image.py` |

**适用场景**：系统架构图、算法流程图、问题场景示意图（不适合数据图表）

### 3. MCP web-search — 通用网页搜索

| 项目 | 值 |
|------|-----|
| 接入方式 | MCP Server |
| 用途 | 搜索官方规则、竞赛通知、补充资料 |

---

## 已知限制与改进方向

### 当前限制

- **MCM/电工杯已移除**：如需其他竞赛，fork 上游 mathmodel-skill v6.1.0 从头定制
- **多 Agent/Sciverse 编排未经自动化测试**：`stage_05_subproblem_loop.md`、`stage_08_writing.md` 中的并行 Agent 分发和文献检索是指令级描述（由运行中的 agent 解释执行），没有对应的自动化测试覆盖其实际行为
- **概念图质量**：gpt-image-2 对中文标注支持不稳定，需测试优化 prompt
- **未做完整 10 阶段真题模拟**：尚未用往年真题走完整条流水线验证实际痛点

### 建议后续打磨方向

1. **完整走一遍流程**：用往年真题（如 2024 C 题）模拟完整 10 阶段，发现实际痛点
2. **优化概念图 prompt**：针对学术论文场景提炼最佳 prompt 模板
3. **算法库与 model_catalog 联动**：确保算法推荐逻辑和参考文献一致
4. **config/dim_weights.json**：根据更多实际求解经验调整题型权重

---

## 验证方法

```bash
# 1. Python 语法检查
python -m compileall -q scripts templates/shared/code_starter

# 2. Preflight 检查（无外部工具）
python scripts/doctor.py --competition cumcm --skip-tools

# 3. 概念图脚本连通性
python scripts/generate_concept_image.py \
  --prompt "test" --output /tmp/test.png --size 1024x1024 --quality low

# 4. Sciverse MCP（在 Claude Code 中）
# "用 Sciverse 搜一篇关于 NSGA-II 的论文"

# 5. 完整测试
python -m unittest discover -s tests -p 'test_*.py' -v
```

---

## 版本历史

| 版本 | 日期 | 核心变更 |
|------|------|---------|
| v7.0 | 2026-07 | 基于 upstream v6.1.0 fork，专精 CUMCM + Claude Code，移除 MCM/电工杯/Codex/LaTeX，MD+DOCX 管线，Sciverse MCP 集成，gpt-image-2 概念图，多 Agent 并行架构，算法库/可视化/写作规范移植 |

---

## 许可与致谢

- 上游项目：[mathmodel-skill](https://github.com/handsomeZR-netizen/mathmodel-skill) v6.1.0 by 徐子锐 (handsomeZR-netizen)
- 本 skill 基于上游 MIT 许可定制，详见 `LICENSE`
