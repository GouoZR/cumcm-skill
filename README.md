# cumcm-skill

> CUMCM 全国大学生数学建模竞赛端到端 Agent 工作流 — 10 阶段把 72 小时竞赛变成可恢复、可检查的流程。

[![Version](https://img.shields.io/badge/version-v7.0.0-6f42c1)](./SKILL.md)

---

## 快速开始

```bash
# 安装
git clone https://github.com/<your-repo>/cumcm-skill.git ~/.claude/skills/cumcm-skill

# 前置依赖
claude mcp add -s user sciverse -- npx -y sciverse-mcp-server  # Sciverse 文献检索
export SCIVERSE_API_TOKEN="your-token"                          # Sciverse Token
export PACKYAPI_TOKEN="your-token"                              # gpt-image-2 概念图

# 启动
# 在 Claude Code 中说: "开始建模" / "打国赛" / "CUMCM"
```

---

## 核心特性

| 特性 | 说明 |
|------|------|
| **10 阶段工作流** | kickoff → 选题 → 分析 → 选型 → 求解 → 灵敏度 → 评价 → 写作 → 审核 → 提交 |
| **全程问答式** | 用户只需回答编号问题，Agent 自动维护状态和脚本 |
| **多 Agent 并行** | Stage 5 并行求解 + Stage 8 并行写作 (championship 模式) |
| **Markdown + DOCX** | 不再依赖 LaTeX，pandoc 一键转换 |
| **Sciverse 文献** | MCP 接入 4.66 亿学术元数据，所有引用可溯源 |
| **双轨图表** | matplotlib 数据图 + gpt-image-2 概念图 |
| **AI 披露合规** | 自动记录 AI 使用，生成国赛要求的披露文件 |
| **测试 + Preflight** | doctor.py 赛前检查 + 完整测试套件 |

---

## 输出管线

```
Markdown 写作 (paper.md)
    → pandoc 转换 (paper.docx)
        → 用户调格式
            → 导出 PDF 提交
```

---

## 目录结构

```
cumcm-skill/
  ├── SKILL.md                     # 主工作流定义 (Claude Code 入口)
  ├── AGENTS.md                    # 维护者指南
  ├── README.md                    # 本文件
  ├── competitions/cumcm/          # 国赛特化层
  │   ├── current_rules.md         # 当届规则基线
  │   ├── winning_patterns.md      # 获奖论文模式 (59 份样本)
  │   ├── empirical.json           # 观察分位数据
  │   ├── phrase_bank.md           # 句式库
  │   ├── anti_patterns.md         # 42 条反模式检查
  │   ├── paper_skeleton.md        # Markdown 论文骨架
  │   ├── abstract_template.md     # 摘要模板
  │   └── ...
  ├── references/
  │   ├── stage_00_kickoff.md ~ stage_09_review.md  # 10 阶段细则
  │   ├── feedback_layer*.md       # 4 层反馈协议
  │   ├── rubrics.md               # 评分细则
  │   ├── model_catalog.md         # 模型目录
  │   ├── sciverse_guide.md        # Sciverse MCP 接入指南
  │   ├── algorithms/              # 60+ 算法详情 (7 类)
  │   ├── visualization/           # 可视化规范 + 脚本
  │   └── writing/                 # 写作规范 + 章节模板 + 自审框架
  ├── scripts/
  │   ├── doctor.py                # Preflight 检查
  │   ├── score_artifact.py        # 5 维评分 + verdict 计算
  │   ├── generate_concept_image.py # gpt-image-2 概念图生成
  │   └── render_ai_usage.py       # AI 使用披露生成
  ├── templates/shared/            # 共享模板 (decision_log, 代码模板等)
  ├── config/                      # 维度权重配置
  └── tests/                       # 测试套件
```

---

## 10 阶段概览

| # | 阶段 | 时长 | 关键能力 |
|---|------|------|---------|
| 0 | 团队启动 + 资料预扫 | 1h | 环境准备、Sciverse 背景调研 |
| 1 | 选题 | 2-4h | 5 维矩阵 + Sciverse 文献辅助 |
| 2 | 问题解析与分解 | 2-3h | 子问题拆解 |
| 3 | 模型选型 | 2-4h | 算法库 + Sciverse 文献验证 |
| 4 | Foundation | 1h | 假设 + 符号 + 术语 |
| 5 | 子问题求解循环 | 6-12h×n | **多 Agent 并行求解 + 文献查阅** |
| 6 | 灵敏度分析 | 2-3h | LHS / Sobol / Tornado |
| 7 | 模型评价 | 1-2h | 优点/缺点/推广 |
| 8 | 论文写作 | 12-20h | **多 Agent 并行写作 + 双轨图表** |
| 9 | 提交审核 | 2-6h | 合规门 + Panel 多视角终审 |

---

## 数据来源

- 91 份 CUMCM 来源文档 (2023-2025)，其中 59 份文本提取进入观察分位
- 数据来源: 教育部"中国大学生在线"论文展廊 + GitHub 公开仓库
- 经验数据是观察基线，不是官方阈值或获奖预测
- Sciverse: 4.66 亿学术元数据，实时检索可溯源

---

## 许可与致谢

基于 [mathmodel-skill](https://github.com/handsomeZR-netizen/mathmodel-skill) (v6.1.0, 作者: 徐子锐) 定制开发。

MIT License. 详见 `LICENSE`。
