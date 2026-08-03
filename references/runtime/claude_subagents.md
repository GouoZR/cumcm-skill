# Claude SubAgent 产出协议

## 定位

SubAgent 只服务于 Claude 当前阶段的内部并行产出，不是第三个工作流 owner。`state/workflow.json` 中的 owner 始终仍为 `claude`；Claude 主 Agent 对阶段理解、关键决策、结果核验、正式落盘和 handoff 负最终责任。

与 Codex 的只读审查 SubAgent 不同，Claude 的 SubAgent 会真实产出代码、结果、图表或章节草稿。因此除状态边界外，还必须有**独占路径边界**。

任务提示中必须明确：

- 只写分配给自己的独占路径，不碰其他 SubAgent 或主 Agent 的文件；
- 不修改 `state/workflow.json`、`state/artifact_manifest.json` 或活动交接单；
- 不调用 `workflow.py start`、`handoff` 或 `complete`；
- 不独立宣布阶段通过、回退或完成；
- 不静默偏离 `artifacts/model_spec.md`；发现规格问题只上报，由主 Agent 决定是否写入 `artifacts/model_deviations.md`；
- 不扩大范围，不重做其他子问题或章节。

## 独占路径分区

并行的前提是写入互不重叠。分区规则：

| Stage | 分区维度 | SubAgent 独占路径 | 只有主 Agent 可写 |
|---|---|---|---|
| 2 | 按子问题 | `code/q<i>_*`、`results/q<i>_*`、`figures/q<i>_*` | `artifacts/run_manifest.json`、`artifacts/model_deviations.md`、公共模块、`state/` |
| 4 | 按章节文件 | `paper_workspace/<NN>_<name>.md` 各一份 | `paper_draft.md`、`support_materials_manifest.md`、`state/` |

公共数据清洗模块、绘图样式和共享工具由主 Agent 先固定，再供 SubAgent 只读复用；不允许多个 SubAgent 并行修改同一公共模块。

## 动态 fan-out

主 Agent 先亲自完成关键路径和公共基座，再把互不依赖的产出并行委派。不要把下一步立即依赖的阻塞任务交出去。

规格充分且以高质量竞赛结果为目标时，建议：

| Stage | 建议数量 | 分区方式 |
|---|---:|---|
| 2 | 按子问题数，通常 2–4 | 每个 SubAgent 负责一问的实现、求解、结果表与证据图 |
| 4 | 3–5 | 摘要与前置章节 / 模型主体 / 验证与评价 / 参考文献 / 图表核验 |

Stage 0 和 Stage 6 默认由主 Agent 串行完成：Stage 0 输入量小且需要整体判断，Stage 6 是逐项装配与一致性核验，并行只增加冲突风险。

数量不是质量指标。子问题耦合紧密、规格未冻结或工作量很小时减少角色甚至串行完成；子问题相互独立且实现量大时增加。SubAgent 不可用时，主 Agent 按同样分区串行完成，产物要求不降低。

### Claude 执行节奏

1. 主 Agent 先确认 Codex 已冻结的 `model_spec` 与 `implementation_contract` 版本，再冻结公共数据口径、公共模块接口和绘图样式；随后一次性并行派发互不依赖的分区，并在提示中写明独占路径；
2. 派发后主 Agent 继续做跨问一致性检查、公共模块维护或写作骨架，不为非阻塞产出空等；
3. 产出回收后，主 Agent 亲自核验（见下），核验通过才登记 artifact manifest；
4. 结果已核验或不再需要时关闭 SubAgent，避免遗留并发写入；
5. 不把同一子问题或章节重复委派给多个 SubAgent。

## 任务提示要求

每个任务只包含完成产出所需的最小上下文：

1. Stage、分区标识（子问题号或章节文件名）和单一产出目标；
2. 允许读取的文件与冻结的规格/结果版本；
3. 独占写入路径清单；
4. 必须满足的验证要求（如：断言、量纲检查、结果与规格一致、图表数字与结果表一致）；
5. 禁止事项：修改工作流状态、写其他分区文件、静默偏离规格、代替主 Agent 裁决。

## 委派提示骨架

```text
你是 CUMCM Stage <N> 的 <分区标识> 负责人。只在独占路径内产出，不修改其他文件。
目标：<single objective>
允许读取：<冻结的 model_spec/公共模块/结果版本>
独占写入：<exact paths>
必须满足：<3–6 concrete requirements>
禁止：修改工作流状态、写其他分区文件、静默偏离规格、代替主 Agent 裁决。
完成后列出产出文件清单与自检结果；无法满足某项要求时明确说明原因，不要静默降低标准。
```

## 主 Agent 核验

回收产出后，主 Agent 必须亲自核验，不得直接采信：

- Stage 2：至少复跑或复算一个决定性结果；核对量纲、数量级、随机种子和跨问变量口径一致；确认图表数字与结果表一致；
- Stage 4：逐章核对数字、图号、符号与已验证产物一致；核对章节间衔接和风格统一；用 `anti_patterns.md` 做机械检查。

核验不通过的产出退回对应分区重做，或由主 Agent 直接修正后在交接单说明；不得为赶进度而带病登记。并行只是压缩耗时，不降低验收标准。SubAgent 只能在独占路径写候选产物；是否纳入正式阶段产物，以及 `artifact_manifest.json` 登记、`model_deviations.md`、交接单和 `paper_draft.md` 装配，只能由主 Agent 决定并执行。
