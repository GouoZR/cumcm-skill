---
stage: 1
name: problem_selection
duration_h: 2-3
inputs:
  - "stage.0.problem_scan"
  - "problem_pdfs[<topic_letters>]"
  - "decision_log.competition"
outputs:
  - "stage.1.{selected, rationale, rejected_alternatives, candidates_assessed, risks_identified}"
  - "root.task_type"
loads_reference:
  - "references/rubrics.md§Stage_1"
  - "references/model_catalog.md§0"
  - "competitions/cumcm/topic_specs.json"
  - "references/sciverse_guide.md§Stage_1"
feedback: ["L1"]
next: stage_02_analysis
---

# Stage 1 — 选题 (多题对比 → 1)

**时长**: 2-3h | **反馈层**: L1 | **关键决策点**: 选题依据写入状态；出现新证据时可审计地重开决策

---

## 目标

在 CUMCM 题号体系内 (A-F, 以当届题面公布为准), 选出**最契合团队优势 + 时间预算 + 数据可获取性**的一题，并让选择、否决与后续变更都有据可查。

**第一步必做**: 加载 `competitions/cumcm/topic_specs.json` 获取题号清单与每题 `task_type_key`; 选定后写 `decision_log.task_type` (供 stage 3+ 的 dim_weights 加权)。

---

## 输入

- stage 0 元信息 + 题目预扫
- `topic_specs.json` 所列候选题的官方 PDF (用户提供路径)

## 产出

- `decision_log.stages.1.selected`: 选定题号
- `decision_log.stages.1.rationale`: 选择理由与证据
- `decision_log.stages.1.rejected_alternatives`: 其余已评估候选及不选理由
- `decision_log.stages.1.candidates_assessed`: 全部可选题的对比矩阵

---

## 操作流程

### Step 0: 加载竞赛题号体系 (5 min, 必做)

```bash
# 路径: <skill>/competitions/cumcm/topic_specs.json
# 加载后得到 CUMCM 题号清单 (A-F, 以当届题面公布为准) 与每题的 task_type_key
```

题号体系总览 (引用 `topic_specs.json`; 以当届题面实际公布为准):

| 题号 | 默认子问数 | 主要类型 |
|------|-----------|-------------------------------------|
| A | 3-5 | 优化类 |
| B | 3-5 | 统计决策类 (历年含概率/抽样/期望成本, 偶为评价类) |
| C | 3-5 | 数据类 |
| D | 3-5 | 工业/工程类 |
| E | 3-5 | 创新/开放类 |
| F | 3-5 | 评价类 (历史题号, 是否出现以当届为准) |

> **提示**: `topic_specs.json` 中 `primary_type`/`typical_problems` 只是维护者对历年真题的启发式概括，**同一题号不同年份题型可能不同**。例如 B 题 2024 是统计决策题（抽样检验 + 期望成本），早年是评价题。Step 1 必须从当届官方题面重新判定实际题型，不得只依赖本表预设——本表只用于候选题导航与评分权重 fallback。

### Step 1: 候选题信息提取 (45 min,可并行)

为 `topic_specs.json` 中每道当前可选题提取；不要截取固定数量的候选，也不要为凑数量加入未发布或不适用的题:
- **核心任务** (1 句话)
- **子问题数与各自难点**
- **附件数据** (大小、格式、是否需清洗)
- **预估问题类型** (model_catalog.md 1-11 类)
- **历年类似题** (若知道)

每题输出一张同构卡片 (markdown):

```
## A 题: <标题>
- 核心: ...
- 子问题: `<按官方题面逐项列出>`
- 数据: `<附件路径、实际格式与扫描大小>`
- 类型: 优化类 + 预测类
- 类似题: `<有已核验来源时填写，否则写未检索到>`
```

### Step 1.5: Sciverse 文献辅助选题 (20 min, 可选)

> 详见 `references/sciverse_guide.md` §Stage 1

为每道候选题目搜 3-5 篇相关文献辅助判断:

```
对每题:
  semantic_search: "<题核心问题> mathematical model solution"
  semantic_search: "<题核心问题> dataset benchmark"
  search_papers: 该领域近年论文数量趋势 (按年份排序/过滤)
```

输出: 每题附 3-5 条文献摘要 (标题 + 方法 + 关键发现), 辅助 Step 2 评分。

**离线预案**: 若 Sciverse 不可用, 跳过本步, 不影响后续流程。

### Step 2: 5 维对比矩阵 (30 min)

| 维度 | 权重 | `<题号 1>` | `...` | `<题号 N>` |
|---------------|-----|------------|-------|------------|
| 1. 数据可处理性 | 0.20 | `<score>` | `...` | `<score>` |
| 2. 团队工具匹配 | 0.25 | `<score>` | `...` | `<score>` |
| 3. 模型族契合 | 0.20 | `<score>` | `...` | `<score>` |
| 4. 时间可行性 | 0.20 | `<score>` | `...` | `<score>` |
| 5. 创新空间 | 0.15 | `<score>` | `...` | `<score>` |
| **加权总分** | | `<weighted>` | `...` | `<weighted>` |

每维评分必须有**一句话依据** (写在表下方)。

### Step 3: 风险识别 (30 min)

为领先候选列出所有**有题面、数据或团队能力证据的实质风险**及应对策略。没有额外风险时明确写“未发现新的实质风险”，不要换措辞凑数:

```
风险 <ID>: <由题面、附件或团队能力暴露的风险>
  证据: <可追溯来源>
  应对: <可执行缓解措施与触发 fallback 的条件>
```

### Step 4: 决策与锁定 (15 min) — 问答式

**呈现给用户** (AskUserQuestion):

```
【基于 5 维对比矩阵, 推荐选题】

  1) <题号> — <加权结果>, 主要依据: <可核验依据>
  2) <题号> — <加权结果>, 主要依据: <可核验依据>
  ...
  N) 让我决定 (推荐当前证据最充分的题)

回复数字。
```

用户选定后, **agent 自动写入** `decision_log.stages.1` (不要让用户编辑 json):
```json
{
  "selected": "<selected topic>",
  "rationale": "... 可追溯依据 ...",
  "rejected_alternatives": [
    {"题号": "<other>", "reason": "... 有证据的不选理由 ..."}
  ],
  "candidates_assessed": [...],
  "risks_identified": [...]
}
```

**同步写 root 字段**:
- `decision_log.task_type` ← `topic_specs.json[selected].task_type_key` (e.g. `A_optimization` for cumcm-A)
- `decision_log.stages.5.qi_count` ← 优先使用官方题面解析出的实际子问题数；题面未到时才用 `topic_specs.json[selected].expected_subproblem_count` 做 provisional 估计，并在 stage 2 覆盖
- `decision_log.stages.5.qi_weights` ← `[1.0] * qi_count` (默认均匀, 用户后续可在 stage 5 调整)

**决策版本**: 选定题号作为当前有效版本。若附件不可用、官方更正或新增团队约束等新证据足以改变排序，触发 L2 并向用户做一次编号确认；在 `decision_log.events.log` 记录原题号、新题号、证据、时间与受影响阶段，然后从最早受影响阶段恢复。不得因短暂犹豫无证据换题，也不得用固定时间窗阻止有依据的纠错。

### Step 5: 移交 (5 min)

输出给 stage 2 的"问题输入包":
- 选定题号
- 子问题清单
- 附件数据路径
- 预估问题类型
- 风险清单

---

## L1 Rubric (`rubrics.md` Stage 1)

| 维度 | 满分行为 |
|---------------------|---------------------------------------------------------------|
| 1. 候选覆盖与对比深度 | 当前全部可选题均按同一维度评估，依据可追溯 |
| 2. 团队优势匹配 | 选题理由含"我们擅长 X,本题需要 X" |
| 3. 风险识别 | 实质风险均有证据与应对；不重复凑数 |
| 4. 时间可行性 | 已估各阶段所需 h,合计不超过实际截止预算 |
| 5. 决策记录质量 | rationale 与 rejected_alternatives 能回溯到题面、数据或团队约束 |

退出: 全维 ≥7。

---

## 常见坑

- **J2** 选题摇摆: 无新证据不重开；有决定性新证据则按 L2 留痕重开
- 候选题都说不清: 信号是 Step 1 没读透题,回 stage 0 重读题目 PDF
- 选了团队最擅长但题目本身证据空间不足: 回看创新空间的事实依据，而不是用最低分数掩盖问题

---

## 退出条件

1. 已评估当前全部可选题并选定一个当前有效题号
2. decision_log.stages.1 完整 (5 个 key 都有内容)
3. L1 rubric 全维 ≥7
4. 风险清单已有应对

→ 跳转 `stage_02_analysis.md`
