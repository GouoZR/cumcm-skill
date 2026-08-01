# CUMCM 论文骨架 (Markdown)

> 本文件给出内容占位符与写作指令，不替代当年格式要求。开始写作前先检查同目录 `current_rules.md`；详细工作流见 `../../references/stage_08_writing.md`。

## 输出管线

```
Markdown 写作 (paper_workspace/*.md)
    → 装配为 paper.md (交付物)
        → 用户自行转 DOCX/PDF 并调格式
            → 提交
```

所有公式使用 MathJax/LaTeX 数学模式（`$...$` / `$$...$$`），在 Markdown 与主流编辑器中可读。

## 提交边界

当前规则基线: 电子论文第一页为摘要页、不放目录、不包含承诺书或编号页、不暴露身份，正文不超过 30 页。页数、文件大小、附录和 AI 使用材料以当年官方通知为准。

59 份可提取样本的观察值见同目录 `empirical.json` 与 `empirical_notes.md`。

## 多 Agent 写作分工

Stage 8 启用 5 个 Agent 并行写作:

| Agent | 负责文件 | 内容 |
|------------|----------------------------------------|------------------------------------------|
| 写作 Agent 1 | `01_abstract.md` ~ `05_notation.md` | 摘要、问题重述、分析、假设、符号 |
| 写作 Agent 2 | `06_models.md` | 模型建立与求解（论文主体） |
| 写作 Agent 3 | `07_sensitivity.md` ~ `08_evaluation.md` | 灵敏度、评价、推广 |
| 文献 Agent | `09_references.md` | 参考文献核验（Sciverse 溯源） |
| 图表 Agent | `figures/` | 数据图 (matplotlib) + 概念图 (gpt-image-2) |

主 Agent 负责装配、交叉引用检查、格式统一。

## 工作区文件

| 文件 | 内容 | 负责 Agent |
|-----------------------|------------------------|----------|
| `01_abstract.md` | 摘要与关键词 | Agent 1 |
| `02_problem_restate.md` | 问题重述 | Agent 1 |
| `03_analysis.md` | 问题分析与技术路线 | Agent 1 |
| `04_assumptions.md` | 假设及依据 | Agent 1 |
| `05_notation.md` | 符号、单位与索引 | Agent 1 |
| `06_models.md` | 各子问题建模、求解与结果 | Agent 2 |
| `07_sensitivity.md` | 验证、敏感性与稳健性 | Agent 3 |
| `08_evaluation.md` | 模型评价、边界与推广 | Agent 3 |
| `09_references.md` | 参考文献 | 文献 Agent |
| `10_appendix.md` | 代码与补充材料索引 | Agent 2 |
| `figures/` | 全部图表 (PNG + SVG) | 图表 Agent |
| `paper.md` | 装配后的完整论文 | 主 Agent |

拆分写作时，`01_abstract.md` 只写摘要正文与关键词，不保留 `# 摘要` 标题；`02`–`10` 各保留一个顶层标题。装配时主 Agent 合并为 `paper.md`。

## 内容骨架

```markdown
# 摘要

<问题与约束；逐问方法；可追溯的定量结果；验证；边界与推广>

**关键词**：<问题域关键词；模型/算法关键词>

---

# 1. 问题重述

## 1.1 问题背景
<用自己的话概括场景，不复制题面>

## 1.2 任务拆解
<逐问写输入、输出与约束>

---

# 2. 问题分析

## 2.1 总体技术路线
<数据 → 模型 → 求解 → 验证 → 交付的依赖图>

![技术路线图](figures/tech_roadmap.png)
*图 1: 总体技术路线*

## 2.2 各子问题分析
<本质问题、难点、候选方法、上下游依赖>

---

# 3. 模型假设

<每条假设附题意、数据、物理意义或文献依据>

| 编号 | 假设内容 | 依据 | 影响范围 |
|------|---------|------|---------|
| 1 | <假设> | <依据> | §X.Y |
| ... | ... | ... | ... |

---

# 4. 符号说明

<覆盖正文实际使用的符号、含义、单位和索引>

| 符号 | 含义 | 单位 | 类型 |
|------|------|------|------|
| $x_i$ | <含义> | <单位> | 决策变量 |
| ... | ... | ... | ... |

---

# 5. 模型的建立与求解

> 本节为论文主体，占 12-16 页。按实际题目子问数增减小节。

## 5.1 问题一：<与真实设计一致的模型名>

### 5.1.1 变量、目标与约束

$$
\begin{aligned}
\min \quad & <目标函数> \\
\text{s.t.} \quad & <约束条件>
\end{aligned}
$$

### 5.1.2 求解方法与复现入口
<算法选择理由、步骤、复杂度；引用 `references/algorithms/` 中对应算法>

![Q1 求解流程](figures/process_q1_flow.png)
*图 X: 问题一求解流程*

### 5.1.3 结果、图表与现实解释
<数值结果 + 物理意义讨论>

![Q1 结果](figures/result_q1.png)
*图 X: 问题一求解结果*

## 5.2 问题二：<同上；若依赖问题一，标明结果版本、单位和转换>

## 5.3 后续问题：<按实际题目增减，不强行固定为三问>

---

# 6. 验证、敏感性与稳健性

<选择与模型风险匹配的方法 (LHS / Sobol / Morris / 扰动分析)>

![灵敏度分析](figures/sensitivity_tornado.png)
*图 X: 参数灵敏度 Tornado 图*

| 参数 | 扰动范围 | 目标变化 | 敏感度等级 |
|------|---------|---------|-----------|
| <参数> | ±X% | Y% | 高/中/低 |

<报告范围、误差、失稳边界与现实含义>

---

# 7. 模型评价与推广

## 7.1 有证据的优点
<≥3 条，每条带数据支撑>

## 7.2 真实局限及受影响结论
<≥3 条，每条含替代方法 + 改进估算 + 代价>

## 7.3 可执行的改进与代价
<≥2 个可行改进方向>

## 7.4 推广所需的重新标定
<≥2 个推广场景 + 适配方式>

---

# 8. 参考文献

> 所有引用必须可溯源。通过 Sciverse MCP 检索的文献附 `doc_id` 确保真实性。

[1] <作者>. <标题> [J]. <期刊>, <年份>, <卷>(<期>): <页码>.
[2] ...
<只列正文实际引用的来源，与正文一一对应；GB/T 7714 格式>

---

# 附录 A: 程序代码

## A.1 Q1 求解代码 — 对应论文 §5.1.2
```python
# Q1 求解 - <方法>
# 对应论文 §5.1.2
...
```

## A.2 Q2 求解代码 — 对应论文 §5.2.2
```python
...
```

---

# 附录 B: 计算结果详表
<完整结果数据表>
```

## 装配与转换

### Markdown 装配 (主 Agent)

```bash
# 合并所有拆分文件为 paper.md
cat 01_abstract.md 02_problem_restate.md 03_analysis.md \
    04_assumptions.md 05_notation.md 06_models.md \
    07_sensitivity.md 08_evaluation.md 09_references.md \
    10_appendix.md > paper.md
```

### 交付物

装配得到的 `paper.md` 即交付物。如需 DOCX/PDF，由用户自行转换并核对格式与页数。

## 相关资源

| 用途 | 路径 |
|------------|--------------------------------------------------|
| 摘要提示 | `abstract_template.md` |
| 高质量模式 | `winning_patterns.md` |
| 反模式自检 | `anti_patterns.md` |
| 当前规则 | `current_rules.md` |
| 写作工作流 | `../../references/stage_08_writing.md` |
| 写作规范 | `../../references/writing/写作规范.md` |
| 章节模板 | `../../references/writing/章节模板.md` |
| 自审框架 | `../../references/writing/自审框架.md` |
| 可视化规范 | `../../references/visualization/可视化规范.md` |
| 图表选择 | `../../references/visualization/图表选择与避坑.md` |
| 算法详情 | `../../references/algorithms/` (7 类 58 算法) |
| 文献检索 | `../../references/sciverse_guide.md` |
| 共享表格模板 | `../../templates/shared/` |
