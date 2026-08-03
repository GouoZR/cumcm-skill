# Claude Code 开发对接协议

本文件用于 **维护和改进 `cumcm-skill` 本身**。如果当前任务是在数学建模比赛工作区中执行该 Skill，应以 `SKILL.md`、`state/workflow.json`、活动 handoff 和当前阶段说明为准。

## 1. 单一真源与目录边界

- 正式 Skill：`C:\Users\15712\.agents\skills\cumcm-skill`
- Claude Code 全局入口：`C:\Users\15712\.claude\skills\cumcm-skill`
- Claude Code 入口应是指向正式 Skill 的 Junction，不得改成独立复制目录。
- 开发隔离使用 Git worktree 和独立分支，不使用手工复制、双向同步脚本或项目级 Skill 副本。
- `cumcm-skill.backup-*` 仅为历史备份，不得在其中继续开发。

## 2. 两种工作模式

### A. 比赛运行模式

1. 读取 `SKILL.md`。
2. 读取 `references/runtime/claude_code.md`。
3. 定位比赛工作区的 `state/workflow.json`，只在 `current_owner == "claude"` 时修改共享产物。
4. Claude Code 负责 Stage 0、2、4、6；Codex 负责 Stage 1、3、5。
5. 不通过聊天记录交接；状态文件、阶段产物、artifact manifest 和 handoff 才是接口。
6. 不新增第三个工作流 owner。Claude 内部即使使用子 Agent，共享状态的 owner 仍是 `claude`。

### B. Skill 开发模式

开始修改前必须执行：

```powershell
git rev-parse --show-toplevel
git status --short --branch
git log -3 --oneline
```

开发约束：

- 默认在 Claude Code 专用 worktree 和 `claude/cumcm-skill` 分支工作。
- 如果当前位于 `master`，默认只检查和提出建议；除非用户明确要求，否则不要直接修改或提交。
- 先读取 `SKILL.md`，再按任务读取最少量相关文件，不要一次加载全部 references。
- 保持 Claude Code ↔ Codex 双 Agent、单一 owner、文件化交接的总体架构。
- 不把 SubAgent 写入 `state/workflow.json`，不让 SubAgent 独立调用阶段流转命令。
- MCP 只能配置到用户全局作用域；禁止创建项目级 `.mcp.json`。
- 不在仓库中写入 token、API key、Cookie 或其他凭据。
- 只修改任务必需的文件，不顺手重构无关内容。

## 3. 开发任务交接格式

Claude Code 完成一轮修改后，应先验证并创建原子提交，然后在最终回复中严格给出：

```text
Commit: <hash> <message>
Intent: <本轮解决的问题>
Changed:
- <关键文件和行为变化>
Validation:
- <命令>: <结果>
Decisions:
- <重要设计选择及原因>
Open:
- <仍未解决的问题；没有则写 none>
Next owner: codex
```

Git commit 是开发交接的主接口。不要要求用户复制完整聊天记录；Codex 应能根据 commit、diff 和上述摘要继续工作。

## 4. 最低验证门

根据改动范围执行适用检查；涉及工作流、模板或脚本时应执行全套：

```powershell
$env:PYTHONUTF8='1'
python C:\Users\15712\.codex\skills\.system\skill-creator\scripts\quick_validate.py .
python -m compileall -q scripts templates/shared/code_starter
python -m unittest discover -s tests -p "test_*.py"
python scripts/doctor.py
git diff --check
```

提交前还必须确认：

```powershell
git status --short
git diff --stat
git diff --cached --check
```

任何测试失败都必须明确报告，不得用“应该可以”代替验证结果。

## 5. 合并边界

- Claude Code 在专用分支提交后停止，不自行改写 `master` 历史。
- Codex 负责复核 diff、处理冲突并决定 merge 或 cherry-pick。
- 合并进入正式 Skill 后，Claude Code 的 Junction 会自动看到新版本，无需复制或同步。
- “国奖级”是质量目标，不是奖项保证；不得在文档或输出中承诺获奖。
