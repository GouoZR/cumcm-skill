# Scripts 工具说明

这里的脚本分为两组：比赛过程中使用的运行时工具，以及维护资料库时才使用的离线工具。下列命令均假设当前目录是 skill 根目录；用户项目中的动态文件统一放在项目工作目录，不写回 skill。

## 运行时工具

### `init_workspace.py` — 初始化 v2 共享工作区

创建目录、`state/workflow.json`、能力状态、artifact manifest 和空文献库；已存在 workflow 时拒绝覆盖。

```bash
python scripts/init_workspace.py /path/to/project
```

### `workflow.py` — 双 Agent 状态流转

所有写操作都必须带刚读取到的 revision：

```bash
python scripts/workflow.py --workspace /path/to/project status
python scripts/workflow.py --workspace /path/to/project start \
  --actor claude --expect-revision 0
python scripts/workflow.py --workspace /path/to/project handoff \
  --actor claude --to codex --next-stage 1 \
  --handoff state/handoffs/H001_claude_to_codex.md \
  --expect-revision 1 --acceptance passed
```

### `validate_handoff.py` — 交接单校验

```bash
python scripts/validate_handoff.py /path/to/handoff.md \
  --from claude --to codex --next-stage 1
```

### `validate_literature.py` — 文献证据链校验

拒绝用 metadata-only 或未核验内容支撑实质 claim：

```bash
python scripts/validate_literature.py \
  --library /path/to/project/literature/library.json \
  --claim-map /path/to/project/literature/claim_map.json
```

### `assemble_paper.py` — Markdown 装配

只生成 `paper.md`，不生成 DOCX/PDF：

```bash
python scripts/assemble_paper.py \
  --source /path/to/project/paper_draft.md \
  --output /path/to/project/paper.md
```

### `doctor.py` — 环境与包结构预检

在启动工作流时运行。检查 skill 结构、竞赛包、JSON 配置。

```bash
python scripts/doctor.py --competition cumcm --workspace /path/to/project
python scripts/doctor.py --competition cumcm --json
```

### `score_artifact.py` — v1 兼容的 L1 Critic 结果处理

校验 critique JSON、计算实际 verdict，并把阶段分数与迭代记录写入项目的 `state/decision_log.json`。

```bash
python scripts/score_artifact.py \
  --stage 5 \
  --critique /path/to/project/state/critique_v0.json \
  --decision-log /path/to/project/state/decision_log.json
```

不传 `--decision-log` 时，脚本按 `CUMCM_STATE_DIR`、兼容变量 `MATHMODEL_STATE_DIR`、最后 `<cwd>/state/decision_log.json` 的顺序解析路径。

所有子问完成后，可聚合 per-Qi 结果并把 `qi_status`、`review_qis`、`refine_qis` 与最终 verdict 原子写回 Stage 5。

**推荐（multi-Agent 并行安全）**: stage 5 冠军模式下各求解 Agent 把 critique 写到独立 `qi_critiques/qi_<id>.json`（每 Qi 唯一文件，无共享文件竞争），主 Agent 统一聚合。写入可用 `score_artifact.write_qi_critique(critique, state_dir)`（Python 函数，每 Qi 唯一文件原子写），主 Agent 聚合：

```bash
python scripts/score_artifact.py \
  --mode aggregate_qi \
  --qi-critiques-dir /path/to/project/state/qi_critiques \
  --decision-log /path/to/project/state/decision_log.json
```

自动读 `qi_critiques/` 下所有 `qi_*.json` → `compute_stage5_verdict` → 一次性写入 `stages.5` 聚合节点。每个 `qi_<id>.json` 须含 `qi_id`/`qi`、`scores`(5维)、`min`、`mean`、`issues`。

**兼容旧流程**: 也可用 `--qi-results` 手工 JSON 文件（`--qi-critiques-dir` 优先，二选一）：

```bash
python scripts/score_artifact.py \
  --mode aggregate_qi \
  --qi-results /path/to/project/state/qi_results.json \
  --decision-log /path/to/project/state/decision_log.json
```

**`aggregate_qi` 输入 schema**（`--qi-results` JSON 文件）:

```json
{
  "qi_results": [
    {
      "qi": "Q1",
      "min": 8,
      "mean": 8.2,
      "scores": {
        "1_problem_fit": {"score": 8},
        "2_math_rigor": {"score": 8},
        "3_solve_correctness": {"score": 8},
        "4_visualization": {"score": 8},
        "5_physical_meaning": {"score": 9}
      },
      "issues": []
    }
  ],
  "qi_weights": [1.0, 1.0, 1.0]
}
```

字段要求：
- `qi_results[i].qi` — 子问 ID，必须形如 `Q1`/`Q2`，不能重复
- `qi_results[i].scores` — 必须是 5 维对象，每维是 `{"score": 1-10}`，缺任一维即失败
- `qi_results[i].min` / `mean` — 必须与 `scores` 实际计算一致（脚本会重算校验，不符报错）
- `qi_results[i].issues` — 数组，每条含 `severity`(high/medium/low) + `where` + `fix`，最多 5 条
- `qi_weights` — 长度必须等于 `qi_results` 数量，默认均匀 `[1.0]*n`

### `extract_diff.py` — v1 兼容/按需复用的定向修补辅助器

根据 Critic 指出的问题生成 section patch prompt，或应用已经生成的 section patch / unified diff。它的价值是缩小修改范围并保留已通过章节；实际节省量取决于论文和修补范围，不设固定比例。

```bash
# 生成定向修补 prompt
python scripts/extract_diff.py \
  --artifact /path/to/project/paper_workspace/06_models.md \
  --critique /path/to/project/state/critique_v0.json \
  --mode section \
  --output /path/to/project/state/refine_prompt.md

# 应用模型返回的 patch；--apply 模式不需要 --critique
python scripts/extract_diff.py \
  --artifact /path/to/project/paper_workspace/06_models.md \
  --apply /path/to/project/state/refine_patch.md \
  --mode section \
  > /path/to/project/paper_workspace/06_models_v1.md
```

### `generate_concept_image.py` — gpt-image-2 学术概念图

通过 PackyAPI 调用 gpt-image-2 生成学术概念图（系统架构图、算法流程图等）。

```bash
# 单张生成
python scripts/generate_concept_image.py \
  --prompt "系统架构图，展示数据流从输入到输出的完整链路" \
  --output figures/system_arch.png

# 批量生成
python scripts/generate_concept_image.py \
  --batch prompts.json \
  --output-dir figures/
```

需设置 `PACKYAPI_TOKEN` 环境变量。

### `render_ai_usage.py` — AI 使用记录导出

从 `decision_log.compliance.ai_usage` 生成竞赛要求的披露材料。使用 AI 时输出到 `support_materials/AI工具使用详情.{md,pdf}`；显式未使用时只输出 `paper_workspace/AI工具未使用声明.md`，接到参考文献后。PDF 生成依赖 ReportLab。

```bash
python scripts/render_ai_usage.py \
  --decision-log /path/to/project/state/decision_log.json \
  --competition cumcm \
  --paper-workspace /path/to/project/paper_workspace \
  --support-dir /path/to/project/support_materials

# 先只检查 Markdown 内容
python scripts/render_ai_usage.py \
  --decision-log /path/to/project/state/decision_log.json \
  --competition cumcm \
  --paper-workspace /path/to/project/paper_workspace \
  --support-dir /path/to/project/support_materials \
  --markdown-only
```

每条 AI 使用记录都必须含 `use_stage`，并完整记录 `query` + `output`，或为代码补全等非对话式工具提供 `disclosure`。`ai_usage: []` 只在团队明确核对“未使用”后填写；缺失或 `null` 会报错。

## 离线维护工具

这两个脚本用于维护样本资料，不应在比赛主流程中自动运行。先安装精简维护依赖：

```bash
python -m pip install -r scripts/requirements-maintenance.txt
python -m playwright install chromium  # 仅下载官方展廊页面时需要
```

### `download_cumcm_papers.py` — 官方展廊下载与 PDF 重建

当前下载器覆盖脚本内登记的 2023、2024 官方展廊页面。页面以图片形式展示论文，因此脚本使用 Playwright 发现详情页，再用 Pillow 重建 PDF。

```bash
python scripts/download_cumcm_papers.py \
  --papers-dir /path/to/cumcm-papers \
  --years 2023 2024
```

下载内容可能受站点结构、网络和来源授权影响；运行前应确认使用范围，并保留脚本生成的下载报告。

### `ingest_papers.py` — 可提取 PDF 的统计蒸馏

扫描指定目录中的 PDF，过滤无法提取足够文字的图片型文件，再生成描述性统计 Markdown。仓库记录了 91 份来源文件，其中 59 份满足当前提取条件；重新运行时以命令输出的“成功解析 / 文本可提取”计数为准。

```bash
python scripts/ingest_papers.py \
  --papers-dir /path/to/cumcm-papers \
  --output /path/to/empirical_distribution.md
```

生成值是样本子集的观察结果，不是官方评分线，也不会自动覆盖 `competitions/cumcm/empirical.json`。采用任何阈值前仍需人工审阅样本构成、提取误差和当年规则。

## 路径协议

| 类型 | 位置 | 覆盖方式 |
|--------------|----------------------------------------------------------|-------------------------------------|
| skill 静态资源 | `<skill>/{references,templates,scripts,competitions}` | 不覆盖 |
| 项目状态 | `<project>/state/decision_log.json` | `--decision-log` 或 `CUMCM_STATE_DIR` |
| 项目产物 | `<project>/{results,figures,paper_workspace,paper_output}` | 通过各脚本参数指定 |

`<cwd>` 只是命令启动时的当前目录，不是一个应当原样创建的文件夹名。

## 测试 fixture

Critic schema 样本位于 `tests/fixtures/`：

- `test_critique_good.json`：有效的 stage-level critique。
- `test_critique_bad_keys.json`：包含不在白名单中的维度键，预期校验失败。

在临时项目目录运行写入型示例，避免修改仓库内的模板状态：

```bash
python scripts/score_artifact.py \
  --stage 1 \
  --critique tests/fixtures/test_critique_good.json \
  --decision-log /tmp/cumcm-test/state/decision_log.json
```
