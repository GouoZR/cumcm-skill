# cumcm-skill

> CUMCM 国赛 72 小时建模工作流 · Claude Code 独占 · 全程问答式

**基座致谢**：本项目基于 [mathmodel-skill](https://github.com/handsomeZR-netizen/mathmodel-skill) (v6.1.0) 深度定制，原作者为**徐子锐** ([handsomeZR-netizen](https://github.com/handsomeZR-netizen))。上游的流程设计、评分体系与材料组织是本项目的地基。

[![Version](https://img.shields.io/badge/version-v1.0-6f42c1)](./SKILL.md)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](./scripts/doctor.py)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-only-D97757)](./SKILL.md)
[![License](https://img.shields.io/badge/license-MIT-22c55e)](./LICENSE)

## 一眼看出它和别的建模 Prompt 有什么不同

别的建模 skill 给你一段超长 Prompt，剩下的全靠你自己：自己维护状态、自己记得改摘要、自己查文献、自己编译格式。**cumcm-skill 把 72 小时变成一条流水线——你负责判断，它负责执行。**

| 传统建模 Prompt | cumcm-skill |
|------------------------------|--------------------------------------------------------|
| 一段超长指令，靠模型自由发挥 | **10 个阶段**，每步有明确输入、产物和退出条件 |
| 状态在聊天记录里，换上下文就丢 | `decision_log.json` 持久化，换模型/重启/换人都不丢进度 |
| 文献靠猜，引用心虚 | **Sciverse 4.66 亿论文**检索，全阶段可溯源引用 |
| 一个人从头写到尾 | Stage 5 求解、Stage 8 写作**自动多 Agent 并行** |
| 最后 LaTeX 折腾一晚上 | 全程 Markdown，交付即 `paper.md`，不碰 LaTeX |
| 好不好全凭感觉 | **题型加权 + 59 份获奖论文经验分位**，verdict 由脚本重算 |

## 国赛 72 小时，为你省下三件事

**省心** —— 全程问答式，你只回答编号问题，Agent 维护状态、调脚本、整理产物。

**省时间** —— 求解和写作阶段多 Agent 并行；Sciverse 真实文献检索，选题、建模、引用一步到位。

**省风险** —— 断点续赛 + 每阶段评分把关 + Stage 9 合规门，提交前不再靠记忆补匿名、页数和 AI 披露。

## 10 个阶段

| Stage | 任务 | 关键产物 | 主要检查 |
|----:|------------------|-------------------------------------------------|--------------------------|
| 0 | 团队启动与资料预扫 | 竞赛、角色、时限、环境、规则基线 | 可执行性与合规入口 |
| 1 | 多题比较与选题 | 选择理由、放弃项、题型判断 | 资源匹配与失败风险 |
| 2 | 问题拆解 | 子问、变量、约束、依赖图 | 逻辑完整性 |
| 3 | 模型选型 | 候选模型、证据、反事实与淘汰理由 | 模型与问题的匹配程度 |
| 4 | Foundation | 假设、符号、术语表 | 一致性与可解释性 |
| 5 | 递归求解 Q1…Qn | formulation、代码、结果、图表 | per-Qi 评分与定向回修 |
| 6 | 稳健性分析 | 风险匹配的验证、稳健区间、失败边界 | 灵敏度与结论可靠性 |
| 7 | 模型评价 | 优点、局限、改进、迁移条件 | 边界是否诚实、结论能否推广 |
| 8 | 论文装配 | `paper_workspace/*.md` 装配为 `paper.md`、AI 台账 | 跨阶段一致性与格式合规 |
| 9 | 提交前终审 | 最终 `paper.md`、支持材料、Panel 记录 | 合规门、证据链与视觉检查 |

## 反馈模式

三种模式使用同一条主流程，只调整反馈预算和评审深度。

| Mode | 反馈层 | 适用场景 |
|--------------|----------------------------|---------------------------|
| `fast` | L1 单轮 | 选题试跑、快速 sanity check |
| `standard` | L1 + L2 | 默认比赛流程 |
| `championship` | L1 + L2 + L3 + L4 + red-team | 终稿前的深度评审 |

评分工具输出的是流程状态，而不是奖项预测：

`block` · `refine` · `refine_partial` · `pass_with_review` · `pass` · `pass_early` · `carryover`

## 竞赛支持

| 竞赛包 | 语言与模板 | 当前材料 | 可信度说明 |
|--------------|------------------------------|---------------------------------------------------------------------------------|----------------------------------------|
| **CUMCM 国赛** | 中文；Markdown 交付 | 收集 91 份公开论文源样本，其中 59 份成功提取文本并进入统计；42 项维护者反模式检查 | 观察分位不是官方门槛，规则以当届通知为准 |

截至 2026-08-01，仓库已核对：

- [CUMCM 2026 竞赛规则](https://www.mcm.edu.cn/html_cn/node/9d8e511fe7a1447b35f53a82c908e2e0.html)
- [CUMCM 2026 论文格式规范](https://www.mcm.edu.cn/html_cn/node/4cd596519c9eb9fbd866398f6df0caa3.html)

这些链接构成仓库当前的规则基线，但不能替代参赛当年的官方文件。

## Quick Start

```bash
# 1. 安装 skill（全局）
git clone https://github.com/your-name/cumcm-skill.git \
  ~/.claude/skills/cumcm-skill

# 2. 前置：Sciverse 学术文献 MCP
npm install -g sciverse-mcp-server
claude mcp add -s user sciverse -- sciverse-mcp-server

# 3. 前置：环境变量（配在 ~/.claude/settings.json 的 env 字段）
SCIVERSE_API_TOKEN="你的Sciverse Token"   # https://sciverse.space/tokens
PACKYAPI_TOKEN="你的PackyAPI Sora令牌"   # https://www.packyapi.com

# 4. 可选：赛前 preflight 检查
python ~/.claude/skills/cumcm-skill/scripts/doctor.py \
  --competition cumcm

# 5. 进入建模项目，启动
mkdir -p my-modeling-project
cd my-modeling-project
claude
```

进入 Claude Code 后输入：

```text
开始建模
```

或：

```text
使用 cumcm-skill 打国赛
```

首次启动时，Agent 会先确认竞赛、题目、队伍能力、截止时间和题面位置，然后创建共享状态并进入 Stage 0。工作区已经存在状态时，则从最近的检查点继续。

### 可选：完整数值环境

核心工作流和 `scripts/doctor.py` 不依赖完整的科学计算栈。只有在需要运行仓库中的建模起步代码时，才需要安装额外依赖：

```bash
python -m pip install -r \
  ~/.claude/skills/cumcm-skill/templates/shared/requirements.txt
```

本 skill 交付 Markdown；如需 DOCX/PDF，请自行转换（例如在 Word 中打开 `paper.md`）。

## 工作区产物

```text
my-modeling-project/
├── state/
│   └── decision_log.json       # 决策、评分、回退、规则与 AI 使用台账
├── results/                    # 结构化结果与可复现实验输出
├── figures/                    # 最终图表（PNG ≥300 DPI + SVG）
├── paper_workspace/            # 01_abstract.md … 11_ai_use_report.md
├── paper_output/               # 用户自行转换 DOCX/PDF 的输出目录（可选）
└── support_materials/          # 代码、数据清单与竞赛要求的披露材料
```

`decision_log.json` 负责保存流程状态，但不会自动同步工作区之外的文件。

## 辅助工具

| 工具 | 用途 | 典型调用 |
|-----------------------------------|-----------------------------------------------------|-------------------------------------------------------------------|
| `scripts/doctor.py` | 检查 skill 结构、竞赛包与工作区 | `python <skill>/scripts/doctor.py --competition cumcm` |
| `scripts/score_artifact.py` | 校验 critic JSON、重算加权分数与 verdict、聚合 per-Qi | `python <skill>/scripts/score_artifact.py --stage 5 --critique ...` |
| `scripts/extract_diff.py` | 生成并应用 section-level patch | `python <skill>/scripts/extract_diff.py --apply ...` |
| `scripts/render_ai_usage.py` | 根据台账生成 CUMCM AI 使用披露材料 | `python <skill>/scripts/render_ai_usage.py --competition cumcm ...` |
| `scripts/generate_concept_image.py` | 通过 PackyAPI 生成学术概念图 | `python <skill>/scripts/generate_concept_image.py --prompt ...` |

完整 CLI 参数与依赖边界见 [`scripts/README.md`](./scripts/README.md)。

## 仓库结构

```text
SKILL.md                         # 工作流主入口与调度协议
AGENTS.md                        # 仓库维护约定
competitions/
  cumcm/                         # 规则、59 份样本统计、写作启发、评分覆盖与模板骨架
references/
  stage_00_* ... stage_09_*      # 按阶段加载的执行细则
  feedback_layer1_* ... layer4_* # 阶段评分、回检、Panel 与校准
  model_catalog.md               # 模型候选目录
  sciverse_guide.md              # Sciverse MCP 接入指南
  algorithms/                    # 7 类 58 算法详解
  writing/                       # 写作规范、章节模板、自审框架
  visualization/                 # 图表规范、审计与复现脚本
templates/
  shared/                        # 状态、AI 台账、表格与 Python 起步代码
config/dim_weights.json          # 题型 × 阶段的评分权重
scripts/                         # 环境检查、评分、差分、披露、概念图与维护工具
tests/                           # 回归测试与 fixture
```

## v1.0

v1.0 是 cumcm-skill 作为独立 skill 的第一个版本。它基于 [mathmodel-skill](https://github.com/handsomeZR-netizen/mathmodel-skill) (v6.1.0, 作者: 徐子锐) 深度定制，并移除了上游的 MCM/电工杯支持、Codex 兼容层、LaTeX 与 Pandoc 依赖。

- 专精 CUMCM 国赛，Claude Code 独占，Markdown 交付（DOCX/PDF 由用户自行转换）
- 集成 Sciverse MCP 真实文献检索，全阶段可溯源引用
- 支持多 Agent 并行求解/写作/文献查阅
- PackyAPI gpt-image-2 概念图 + Python 数据图双轨图表系统
- 10 阶段 + L1/L2/L3/L4 四层反馈，题型 dim 加权，经验分位锚定评分
- 5 个运行时脚本 + doctor 赛前预检 + 自动测试套件

## 边界与可信度

cumcm-skill 是协作与质量控制工具，不是自动获奖系统。

使用它并不会消除建模本身的不确定性，也不能替代团队对公式、代码、数据、事实、引用和最终署名的责任。

需要特别说明的是：

- CUMCM 统计来自公开样本中成功提取文本的 59 份论文，可能受到年份、题型、来源和 PDF 可提取性的影响。
- `winning_patterns.md`、经验分位和反模式清单属于维护者总结，不是官方 rubric。
- 竞赛规则会变化。仓库保存的是最近一次核对的基线，正式提交前必须以当届官方通知和题目要求为准。
- AI 生成的公式、代码、事实和引用必须由团队复核。台账和披露生成器帮助完整记录，但不代替合规判断。

## 开发与验证

```bash
python -m compileall -q scripts templates/shared/code_starter
python -m unittest discover -s tests -p 'test_*.py' -v
python scripts/doctor.py --competition cumcm
```

当工作流、模板或竞赛包发生变化时，请同步更新测试、版本号和规则核对日期。

参与贡献前请先阅读 [`AGENTS.md`](./AGENTS.md)。Bug、规则更新与改进建议可以通过 Issue 提交。

## License

仓库原创代码与文档采用 [MIT License](./LICENSE)。运行时依赖和外部资料链接仍遵循各自的许可条款，详细边界见 [`THIRD_PARTY_NOTICES.md`](./THIRD_PARTY_NOTICES.md)。

上游项目：[mathmodel-skill](https://github.com/handsomeZR-netizen/mathmodel-skill) v6.1.0 by 徐子锐 (handsomeZR-netizen)。

---

cumcm-skill 不替团队完成思考。

它做的是让每一次判断都留下依据，让每一次修改都知道影响范围，也让一场 72 小时的建模协作最终能够被完整地交付。
