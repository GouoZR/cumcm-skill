# Codex SubAgent 专家协议

## 定位

SubAgent 只服务于 Codex 当前阶段的内部并行审查，不是第三个工作流 owner。`state/workflow.json` 中的 owner 始终仍为 `codex`；Codex 主 Agent 对阶段理解、关键推理、结论裁决、正式落盘和 handoff 负最终责任。

SubAgent 默认执行只读检查并返回报告。任务提示中必须明确：

- 不修改任何共享文件；
- 不调用 `workflow.py start`、`handoff` 或 `complete`；
- 不修改 `state/workflow.json`、artifact manifest 或活动交接单；
- 不独立宣布阶段通过、回退或完成；
- 只检查指定范围，不扩写论文或重做整个阶段。

若宿主提供隔离 worktree，SubAgent 的文件修改不作为正式产物；主 Agent 只接收其报告并在核验后写入主工作区。

## 动态 fan-out

主 Agent 先亲自处理当前阶段的关键路径，再把互不依赖的侧向审查并行委派。不要把下一步立即依赖的阻塞任务交出去，也不要让多个 SubAgent 重复同一检查。

以高质量竞赛结果为目标且输入充分时，建议：

| Stage | 建议数量 | 核心角色 |
|---|---:|---|
| 1 | 2–4 | 模型备选审查；假设/约束/可辨识性；实现可行性；文献证据规划 |
| 3 | 3–4 | 数学一致性；模型—代码映射；数值与稳健性；反例/魔鬼代言人 |
| 5 | 3–5 | 逐问与结构；数学符号；结果图表；文献证据；竞赛评委视角 |

数量不是质量指标。题目较简单或检查范围高度重叠时减少角色；跨领域、多模型或高风险结论时增加。SubAgent 不可用时，由主 Agent 按同样角色做相互独立的串行复核，并在正式审计中说明。串行降级也必须按 `templates/shared/subagent_report.md` 形成 `serial-<role>.md`，保存到对应 `reviews/subagents/stage_*/` 目录，确保阶段输出和裁决轨迹不缺失。

### Codex 执行节奏

宿主具备 SubAgent 编排工具时，按以下节奏执行：

1. 主 Agent 先确定关键路径和冻结快照，再一次性并行派发互不依赖的角色；
2. 派发后继续完成本地关键推理，不为非阻塞报告反复等待；
3. 需要综合裁决时再收集报告，对证据做独立复核；
4. 结果已回收或不再需要时关闭 SubAgent，避免遗留并发任务；
5. 不把同一问题重复委派给多个角色，也不把某个 SubAgent 的结论泄露给其他评审。

## 任务提示要求

每个任务只包含完成审查所需的最小上下文：

1. Stage、角色和单一审查目标；
2. 允许读取的文件与结果版本；
3. 必须验证的检查项；
4. 禁止写文件和禁止改变工作流状态；
5. `templates/shared/subagent_report.md` 的输出格式；
6. 不提供主 Agent 预设结论，避免评审迎合。

报告必须给出可定位证据，如文件路径、公式/变量名、结果表键、图号、命令或复现实验；只有泛泛建议的报告不得作为阶段裁决依据。

## 委派提示骨架

```text
你是 CUMCM Stage <N> 的 <role>。只做独立审查，不修改任何文件。
目标：<single objective>
允许读取：<scoped paths and frozen result version>
必须检查：<3–6 concrete checks>
禁止：修改工作流状态、写共享产物、生成 handoff、代替主 Agent 裁决。
请按 templates/shared/subagent_report.md 返回；每个问题必须含可定位 Evidence 和 Acceptance Check。
若证据不足，标记 needs_evidence，不要猜测。不要参考其他评审结论。
```

## 报告与裁决

SubAgent 在消息中返回报告。主 Agent 核验证据后，将采用的报告写入：

```text
reviews/subagents/stage_01/
reviews/subagents/stage_03/
reviews/subagents/stage_05/
```

文件名使用 `<role>.md`；重跑时增加短版本后缀，不静默覆盖仍被 handoff 引用的报告。

裁决规则：

- 任一 `confirmed blocker` 必须修复；Stage 3/5 未修复时判 `needs_revision`；
- 影响正确性、可复现性、题目完整性或引用可信度的 `high` 问题，在证据未闭环前不得通过；
- 多份报告冲突时，主 Agent 独立复核证据，不按票数表决；
- `suspected` 或 `needs_evidence` 不自动判错，但必须被复核、降级为已知限制或转成可执行验证；
- 主 Agent 可以驳回证据不足的报告，但必须记录驳回理由；
- 正式 `solution_audit.md`、`final_review.md` 和 handoff 只能由主 Agent 生成。

## 国奖级质量目标

“国奖级”表示按高质量论文的证据链、完整性和可复现性标准执行，不构成获奖保证，也不得把历史经验写成官方评分线或奖项预测。

### Stage 1 建模门

- 每一问都有“目标—输入—模型—输出—指标—验证”闭环；
- 关键模型选择至少有基线或可比较备选，并说明弃选理由；
- 假设可检验，或明确敏感性分析与失效边界；
- 模型规格中的符号、量纲、约束和实现接口一致；
- 核心结论预先绑定结果表、证据图和稳健性检查；
- 创新来自题意适配、机制解释或可靠改进，不以算法堆叠冒充创新。

### Stage 3 求解门

- 关键结果可从 run manifest 和代码复现，至少独立复跑或复算一个决定性输出；
- 公式—变量—代码—结果表/图存在可追溯链；
- 数据泄漏、量纲、约束、随机性、数值稳定性和边界情况已检查；
- 每个主要结论至少有基线/对照与稳健性、敏感性或误差证据；
- 图表和正文候选数字来自同一结果版本；
- 未披露模型偏离、不可复现结果或关键 sanity check 失败时必须退回。

### Stage 5 论文门

- 摘要和正文逐问作答，核心贡献含准确的定量结果与适用边界；
- 符号、公式、数字、图表、结论和模型规格跨文件一致；
- 主要结论至少有直接结果证据和验证证据，适用时补充机理/流程证据；
- 不夸大因果、创新、泛化能力或竞赛成绩；
- 实质性外部 claim 均有已核验来源，metadata-only 不得支撑结论；
- blocker/high 问题清零后才能进入 Stage 6，medium/low 问题需明确处置或列入限制。

高质量模式只作为经验性检查依据；按需加载 `competitions/cumcm/winning_patterns.md`、`anti_patterns.md` 和当前官方规则，官方材料始终优先。
