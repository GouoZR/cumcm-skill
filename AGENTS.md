# Repository instructions

This repository contains the `cumcm-skill` product. When working inside this repository, act as a maintainer: do not start the ten-stage contest workflow merely because modeling-related files are present.

## Sources of truth

- `SKILL.md` defines runtime behavior and trigger boundaries.
- `references/stage_00_kickoff.md` through `references/stage_09_review.md` contain stage details and must be loaded lazily at runtime.
- `competitions/cumcm/` contains competition-specific rules, heuristics, overlays, and paper structures.
- `references/algorithms/` contains 7-category, 58 algorithm references organized by category.
- `references/writing/` contains writing standards, chapter templates, and self-review frameworks.
- `references/visualization/` contains visualization standards and figure selection guides.
- `references/sciverse_guide.md` contains Sciverse MCP integration documentation.
- `templates/shared/decision_log.json` is the canonical persistent-state template.

## Maintenance rules

- Preserve the trigger boundary: this skill is for CUMCM (国赛) contest work only, not generic data analysis or ordinary paper review.
- Treat official contest rules as time-sensitive. Keep a verification date and primary source in `competitions/cumcm/current_rules.md`; official current-year material always overrides repository guidance.
- Treat empirical distributions and `winning_patterns.md` as observations or maintainer heuristics, never official thresholds or award predictors.
- Keep user artifacts relative to the user's working directory (`state/`, `results/`, `figures/`, `paper_workspace/`). Resolve repository resources relative to the installed skill root.
- Keep `SKILL.md` concise and dispatch stage-specific detail into `references/`.
- Do not add runtime claims about awards, token savings, or elapsed time without a reproducible benchmark.
- When changing behavior, update the README, tests, state schema, and relevant competition docs together.
- Do not vendor or reintroduce templates, examples, papers, or binary assets without a clear redistribution license.
- Output format is Markdown + DOCX via pandoc. Do not introduce LaTeX dependencies.

## Verification

Run the checks proportionate to the change. Before a release, run all of them:

```bash
python -m compileall -q scripts templates/shared/code_starter
python -m unittest discover -s tests -p 'test_*.py' -v
python scripts/doctor.py --competition cumcm --skip-tools
git diff --check
```

Runtime evaluation prompts should explicitly invoke `$cumcm-skill`. Negative-trigger tests should confirm that generic model-selection and non-CUMCM writing requests do not invoke it.
