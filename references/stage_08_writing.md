---
stage: 8
name: writing
duration_h: 12-20
inputs:
  - "decision_log.stages.0-7"
  - "decision_log.task_type"
outputs:
  - "stage.8.{section_word_counts, figures_per_subproblem, tables_per_subproblem, abstract_drafts, ai_use_log, compliance}"
  - "paper_workspace/*.md"
  - "paper_workspace/figures/*.png"
  - "paper.md"
loads_reference:
  - "competitions/cumcm/current_rules.md"
  - "competitions/cumcm/winning_patterns.md"
  - "competitions/cumcm/phrase_bank.md"
  - "competitions/cumcm/empirical.json"
  - "references/writing/写作规范.md"
  - "references/writing/章节模板.md"
  - "references/writing/自审框架.md"
  - "references/visualization/可视化规范.md"
  - "references/visualization/图表选择与避坑.md"
  - "references/sciverse_guide.md"
loads_template:
  - "competitions/cumcm/paper_skeleton.md"
  - "competitions/cumcm/abstract_template.md"
feedback: ["L1", "L2_at_end"]
next: stage_09_review
---

# Stage 8 — 论文写作 (Markdown + DOCX, 多 Agent 并行)

把 Stage 0–7 的验证产出装配成一篇连贯论文。**不重新建模，不重新求解。** 若写作过程中暴露建模矛盾，记录并触发定向 L2 回退。

**输出格式**: Markdown (`paper.md`) → pandoc → DOCX (`paper.docx`)。不再依赖 LaTeX。

---

## 0. 写作前准备 (15 min)

### 0.1 锁定当前规则

1. 读 `competitions/cumcm/current_rules.md`
2. 打开其中官方链接，确认当届规则未变
3. 将核验日期、来源 URL、页数/字体/文件大小限制、匿名规则、AI 披露要求写入 `decision_log.compliance.ruleset`
4. 若仓库基线与官方冲突，以官方为准，标记仓库不一致

### 0.2 加载写作资源

从 `competitions/cumcm/` 加载:
- `paper_skeleton.md` — 论文骨架 (Markdown 版)
- `abstract_template.md` — 摘要模板 (5 段式)
- `winning_patterns.md` — 获奖论文模式
- `phrase_bank.md` — 句式库
- `empirical.json` — 59 份样本观察分位 (写作参考，非官方阈值)

从 `references/` 加载:
- `writing/写作规范.md` — 通用写作标准
- `writing/章节模板.md` — 各章节模板
- `writing/自审框架.md` — 提交前自审
- `visualization/可视化规范.md` — 图表标准
- `visualization/图表选择与避坑.md` — 图型选择
- `sciverse_guide.md` §Stage_8 — 文献检索

---

## 1. 多 Agent 并行写作架构

本阶段启用 5 个子 Agent 并行工作，通过 Claude Code `Agent` 工具派发。

### Agent 分工

```
主 Agent (本 Agent — 协调 + 装配 + 一致性)
  │
  ├── 写作 Agent 1 → §1-4 (问题重述、分析、假设、符号)
  │     输入: decision_log stages.0-4, paper_skeleton.md §1-4
  │     输出: 01_abstract.md(初稿), 02-05_*.md
  │
  ├── 写作 Agent 2 → §5 (模型建立与求解，论文主体)
  │     输入: decision_log stages.2-5, model_catalog.md, algorithms/
  │     输出: 06_models.md
  │
  ├── 写作 Agent 3 → §6-7 (灵敏度、评价、推广)
  │     输入: decision_log stages.5-7, sensitivity_table.md
  │     输出: 07_sensitivity.md, 08_evaluation.md
  │
  ├── 文献 Agent → §8 (参考文献核验)
  │     输入: 各 Agent 的引用需求, sciverse_guide.md
  │     输出: 09_references.md (Sciverse 溯源验证)
  │
  └── 图表 Agent → 全部图表
        输入: 各 Agent 的图表需求, 可视化规范.md
        输出: figures/*.png + figures/*.svg
```

### 分派协议

```python
# 伪代码 — 主 Agent 执行流程

# Step 1: 并行启动 5 个子 Agent
results = parallel([
    # Agent 1: 前半部分
    lambda: agent(
        prompt=f"写 CUMCM 论文 §1-4...",
        context_files=[
            "paper_skeleton.md",
            "abstract_template.md",
            "winning_patterns.md §1-4",
            "写作规范.md",
            "章节模板.md §1-4",
            "decision_log (stages.0-4)"
        ],
        output_files=["01_abstract.md", "02-05_*.md"]
    ),
    
    # Agent 2: 论文主体
    lambda: agent(
        prompt=f"写 CUMCM 论文 §5 模型建立与求解...",
        context_files=[
            "paper_skeleton.md §5",
            "winning_patterns.md §5",
            "decision_log (stages.2-5)",
            "model_catalog.md",
            "algorithms/ (对应 task_type)"
        ],
        output_files=["06_models.md"]
    ),
    
    # Agent 3: 后半部分
    lambda: agent(
        prompt=f"写 CUMCM 论文 §6-7...",
        context_files=[
            "paper_skeleton.md §6-7",
            "winning_patterns.md §6-7",
            "decision_log (stages.5-7)",
            "sensitivity_table.md"
        ],
        output_files=["07_sensitivity.md", "08_evaluation.md"]
    ),
    
    # 文献 Agent: 核验引用
    lambda: agent(
        prompt=f"核验并补充论文参考文献...",
        context_files=[
            "sciverse_guide.md §Stage_8",
            "all agents' draft references"
        ],
        output_files=["09_references.md"],
        tools=["Sciverse MCP"]
    ),
    
    # 图表 Agent: 生成全部图表
    lambda: agent(
        prompt=f"生成论文全部图表...",
        context_files=[
            "可视化规范.md",
            "图表选择与避坑.md",
            "all agents' figure requirements"
        ],
        output_files=["figures/*.png", "figures/*.svg"],
        tools=["matplotlib/plotly", "gpt-image-2 (PackyAPI)"]
    )
])

# Step 2: 主 Agent 装配
assemble_paper(results)

# Step 3: 主 Agent 交叉引用检查 + 一致性验证
cross_check(results)
```

### 子 Agent 派发要点

- 每个子 Agent 独立上下文，不共享聊天历史
- 子 Agent 只写指定章节，不越界
- 子 Agent 产出的引用需求 → 文献 Agent 统一核验
- 子 Agent 产出的图表需求 → 图表 Agent 统一生成
- 主 Agent 负责最终装配、编号统一、交叉引用、格式一致性

---

## 2. 工作区结构

在 `<cwd>/paper_workspace/` 下创建:

```
paper_workspace/
  ├── 01_abstract.md          # 摘要 + 关键词 (最后写)
  ├── 02_problem_restate.md   # 问题重述
  ├── 03_analysis.md          # 问题分析 + 技术路线
  ├── 04_assumptions.md       # 假设及依据
  ├── 05_notation.md          # 符号说明
  ├── 06_models.md            # 模型建立与求解 (主体)
  ├── 07_sensitivity.md       # 灵敏度分析
  ├── 08_evaluation.md        # 模型评价与推广
  ├── 09_references.md        # 参考文献 (Sciverse 核验)
  ├── 10_appendix.md          # 代码 + 补充材料
  ├── 11_ai_use_report.md     # AI 使用说明
  ├── figures/
  │   ├── *.png               # PNG ≥300 DPI
  │   └── *.svg               # SVG 可编辑源文件
  └── tables/
      └── *.csv               # 表格源数据
```

### 文件规范

- `01_abstract.md`: 只写摘要正文与关键词，不保留 `# 摘要` 标题
- `02`–`10`: 每个文件一个顶层 Markdown 标题
- 公式: LaTeX 数学模式 `$...$` (行内) / `$$...$$` (块级)，pandoc 自动处理
- 图片引用: `![图X: 标题](figures/filename.png)`
- 表格: Markdown table 格式，复杂表格用 CSV 源数据

---

## 3. 写作顺序

### 先写主体 (Agent 1-3 并行)

1. **§2-4** (Agent 1): 问题分析 → 假设 → 符号
2. **§5** (Agent 2): 模型建立与求解 — 论文最核心部分
3. **§6-7** (Agent 3): 灵敏度 → 评价推广

### 再写外围 (Agent 1 + 文献 Agent)

4. **§1** (Agent 1): 问题重述 — 基于已写好的 §5 倒推
5. **§8** (文献 Agent): 参考文献 — 收集各 Agent 引用，Sciverse 核验

### 图表并行 (图表 Agent)

6. 图表 Agent 全程并行: 收到各 Agent 需求即生成，不等写作完成

### 摘要最后 (主 Agent)

7. **摘要** (主 Agent): 基于全篇写好的内容提炼。摘要中每个数字必须指向正文中已有结果。

### 装配 + 自审 (主 Agent)

8. 合并所有 `0*.md` → `paper.md`
9. 逐项对照 `自审框架.md` 检查

---

## 4. 证据链完整

每个子问题保持完整链路:

```
问题 → 假设 → 建模 → 求解 → 结果 → 验证 → 物理意义解释
```

交叉检查:
- 符号与 Stage 4 一致
- 模型选择与 Stage 3 一致
- 数值结果与 decision_log 存储值一致（不复述编造）
- 图表标签可读、有单位、有标题、有来源路径
- 声明和引用可验证
- 局限性说出具体失效模式与缓解措施

---

## 5. 图表双轨制

| 类型 | 工具 | 负责 |
|---|---|---|
| **数据图** (折线/柱状/热力/Tornado/散点) | matplotlib / plotly | 图表 Agent |
| **概念图** (系统架构/算法流程/问题示意) | gpt-image-2 (PackyAPI) | 图表 Agent |

### 数据图规范

- 分辨率: ≥300 DPI
- 格式: PNG (位图) + SVG (可编辑矢量)
- 配色: 遵循 `可视化规范.md` 中的 CUMCM 配色方案
- 字体: 中文宋体/英文 Times New Roman，字号 ≥8pt
- 每张图跑 `scripts/plot_style.py` 统一风格

### 概念图规范

- 调用 `scripts/generate_concept_image.py` 封装 PackyAPI
- Prompt 模板: "学术论文插图，<图表类型>，展示 <内容>。白色背景，简洁线条，中文字体标注，适合黑白印刷。"
- 尺寸: 1536x1024 或 1024x1024
- 风格: 学术简约，可黑白打印

### 图表需求收集

各写作 Agent 在产出中标注图表需求:

```markdown
<!-- @figure
  type: data | concept
  description: <图表描述>
  section: §X.Y
  data_source: <数据来源路径>
-->
```

图表 Agent 扫描所有 `0*.md` 文件中的 `@figure` 标记，批量生成。

---

## 6. 文献引用与 Sciverse 核验

### 引用来源

1. Stage 0-7 中 Sciverse 检索到的文献（已在 decision_log 中记录）
2. 各写作 Agent 标注的引用需求
3. 文献 Agent 补充检索

### 核验流程 (文献 Agent)

```
对每条引用:
  1. Sciverse agentic-search 验证文献存在
  2. 获取完整元数据 (作者/标题/期刊/卷期/页码/DOI)
  3. 格式化为 GB/T 7714
  4. 记录 doc_id 到 decision_log.sciverse_queries (可溯源)
```

### 引用格式

GB/T 7714-2015:
```
[1] 作者. 标题 [J]. 期刊名, 年份, 卷(期): 起止页码.
[2] 作者. 标题 [M]. 出版地: 出版社, 年份.
[3] 作者. 标题 [C]// 会议论文集. 出版地: 出版社, 年份: 起止页码.
```

### 引用要求

- 只列正文实际引用的来源，与正文一一对应
- 中英文混合 (4+ 中文 / 3+ 英文 / 1+ 教材)
- 所有引用可溯源 (Sciverse `doc_id` 或等效标识)
- **禁止虚构文献**

---

## 7. AI 使用披露

本 skill 自身使用 AI Agent，需维护披露记录。

在 `decision_log.compliance.ai_usage` 中记录:
- 工具、供应商、模型/版本
- 使用日期、阶段、用途
- 关键 prompt 和回复 (或路径)
- 采纳内容
- 人工修改和验证

Stage 9 使用 `scripts/render_ai_usage.py` 生成国赛要求的 `AI工具使用详情.pdf`。

---

## 8. 装配与转换

### 装配 (主 Agent)

```bash
cd paper_workspace/
cat 01_abstract.md \
    02_problem_restate.md \
    03_analysis.md \
    04_assumptions.md \
    05_notation.md \
    06_models.md \
    07_sensitivity.md \
    08_evaluation.md \
    09_references.md \
    10_appendix.md > paper.md
```

### Markdown → DOCX (用户执行)

```bash
pandoc paper.md -o paper.docx \
  --from markdown --to docx \
  --number-sections \
  --toc --toc-depth=3 \
  --resource-path=figures/
```

> 用户自行在 Word 中调格式后导出 PDF 提交。

---

## 9. 评分 (L1)

使用 `competitions/cumcm/rubric_overlay.json` 的五维评分:

| 维度 | 权重 | 检查项 |
|---|---|---|
| 完整性 | 0.25 | 所有必需要素齐全 |
| 逻辑性 | 0.25 | 问题→模型→求解→结论 连贯 |
| 规范性 | 0.20 | 格式、引用、图表符合规范 |
| 创新性 | 0.15 | 模型选择/改进有创新点 |
| 可读性 | 0.15 | 语言流畅、图表清晰 |

---

## 退出条件

- [ ] 所有章节文件已产出
- [ ] 论文与 Stage 0–7 decision_log 一致
- [ ] 当届官方规则已重新核验并记录
- [ ] AI 使用和引用已记录
- [ ] 图表全部生成 (数据图 + 概念图)
- [ ] 所有引用经 Sciverse 核验可溯源
- [ ] L1 通过
- [ ] L2 跨阶段一致性检查无未解决的高严重性冲突

全部满足后进入 `stage_09_review.md`。
