# Repository instructions

This repository contains the `cumcm-skill` product. When maintaining it, do not start a contest run merely because modeling files are present.

## Sources of truth

- `SKILL.md` defines trigger boundaries and the platform-neutral v2 runtime.
- `references/runtime/` contains host-specific adapters for Codex and Claude Code.
- `references/handoff_protocol.md` defines the single-owner, revision-guarded handoff contract.
- `references/workflow/` contains the seven v2 stages and must be loaded lazily.
- `templates/shared/workflow_state.json` is the canonical v2 state template.
- `references/stage_00_kickoff.md` through `stage_09_review.md` and `templates/shared/decision_log.json` are v1 compatibility assets, not the v2 dispatcher.
- `competitions/cumcm/` contains competition-specific rules, heuristics, overlays, and paper structures.
- `references/algorithms/`, `references/writing/`, and `references/visualization/` are reusable domain references.

## Maintenance rules

- Preserve the trigger boundary: CUMCM contest work only, not generic analysis or ordinary paper review.
- Keep the main `SKILL.md` platform neutral. Put Codex- or Claude-specific behavior in runtime adapters.
- Maintain one physical Skill source. Do not let `.agents/skills` and `.claude/skills` drift as independent copies.
- Preserve the owner map: Claude stages 0/2/4/6; Codex stages 1/3/5. SubAgents on either host are internal helpers, never workflow owners: Codex SubAgents are read-only reviewers (stages 1/3/5); Claude SubAgents produce artifacts under exclusive path partitions (stages 2/4) and their output must be verified by the main agent before it is registered.
- Shared state changes must use revision guards. Non-owners must not write shared artifacts.
- Default to workspace discovery and minimal questions. Team size, member skills, deadline, modes, and already-fixed problem numbers are not startup requirements.
- Sciverse and PackyAPI are optional capabilities. Their absence must not block unrelated stages.
- All MCP servers must be configured in user/global scope. Never create or edit a project-level `.mcp.json`; migrate and remove one if found.
- Never put API keys or tokens in state, logs, handoffs, papers, tests, fixtures, or examples.
- Literature claims require verified content, not title or metadata alone. Preserve Chinese titles in their original language.
- Treat official contest rules as time-sensitive. Keep a verification date and primary source in `competitions/cumcm/current_rules.md`; official current-year material overrides repository guidance.
- Treat empirical distributions and `winning_patterns.md` as observations, never official thresholds or award predictors. “National-award-level” is a quality target, never a guarantee.
- Keep user artifacts relative to the user's project (`state/`, `artifacts/`, `literature/`, `code/`, `results/`, `figures/`, `reviews/`, `paper_workspace/`).
- Output is Markdown `paper.md`. Do not add automatic DOCX/PDF delivery or claim final typesetting compliance.
- Make surgical changes and preserve v1 compatibility unless migration is explicitly requested.

## Verification

Before release, run:

```bash
python -m compileall -q scripts templates/shared/code_starter
python -m unittest discover -s tests -p 'test_*.py' -v
python scripts/doctor.py --competition cumcm
git diff --check
```

Runtime evaluation prompts should explicitly invoke `$cumcm-skill`. Negative-trigger tests should confirm that generic model selection and non-CUMCM writing requests do not invoke it.
