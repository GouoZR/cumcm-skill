---
stage: 9
name: review
duration_h: 2-6
inputs: ["paper.md", "paper.docx", "decision_log_full"]
outputs:
  - "stage.9.{anti_patterns_check, compliance_checks, panel_scores, weakest_section, redo_log, red_team_record, submission_ready}"
loads_reference:
  - "competitions/cumcm/current_rules.md"
  - "competitions/cumcm/anti_patterns.md"
  - "competitions/cumcm/rubric_overlay.json"
  - "references/feedback_layer3_panel.md"
feedback: ["L1", "L3_panel", "red_team_in_championship"]
next: SUBMIT
---

# Stage 9 — Submission review

The final gate is compliance first, content consistency second, presentation third. A polished paper that violates the current rules is not submission-ready.

## 1. Re-open the official rules

Read `competitions/cumcm/current_rules.md`, open its official links, and compare the final artifacts against the current contest year. Record the check in `decision_log.stages.9.compliance_checks`.

Minimum checklist:

- electronic paper starts with the abstract page;
- no commitment form, numbering page, table of contents, or identity information;
- main text and file size meet the current limits;
- appendix lists the supporting-material files;
- support ZIP/RAR contains runnable code and required evidence, is within the size limit, and excludes secrets;
- AI-assisted content is marked and cited;
- if AI was used, support materials contain `AI工具使用详情.pdf`; otherwise the required no-AI declaration is present.

Any unresolved rule violation sets `submission_ready=false` and yields `block`.

## 2. Run the active anti-pattern checklist

Read `competitions/cumcm/anti_patterns.md` and derive the count from the active file rather than copying a remembered or example count.

These are maintainer heuristics, not official scoring weights. Fix high-severity hits; record accepted medium-risk items with an explicit rationale.

## 3. Verify the evidence chain

Cross-check the final paper against `decision_log.json` and the saved artifacts:

- no abandoned model remains in the abstract or conclusion;
- no symbol changes meaning between sections;
- all headline values reproduce from stored results;
- every figure/table path resolves and its caption matches the content;
- every external claim has a verified source;
- AI-generated citations have been opened and checked manually.

## 4. Review presentation

- labels, units, legends, equations, and captions remain readable at final PDF size;
- fonts and colors are consistent and accessible;
- tables use consistent units and precision;
- there are no unresolved `??` references, missing glyphs, clipped figures, or broken page breaks;
- all required sections are present in the assembled `paper.docx`, not merely on disk as detached `paper_workspace/*.md` files.

## 5. Run the five-view panel

Use `references/feedback_layer3_panel.md` as the single source for panel roles and aggregation. Prefer independent parallel views when the harness supports them; otherwise run the views separately to reduce cross-contamination.

Map every high-severity concern back to one source section and apply a targeted patch. Re-run only the affected checks and panel views. Do not ask the panel to predict an award; use `ready`, `refine`, or `block` against the repository rubric.

## 6. Generate AI disclosure artifacts

Run from the user project root:

```bash
python <skill>/scripts/render_ai_usage.py \
  --competition cumcm \
  --decision-log state/decision_log.json \
  --paper-workspace paper_workspace/ \
  --support-dir support_materials/
```

With AI use, verify `support_materials/AI工具使用详情.pdf` is in the supporting archive and that inline marks and AI-tool references are present. For an explicit empty ledger, the helper instead creates `paper_workspace/AI工具未使用声明.md`; rerender and verify that the declaration appears immediately after the references, with no details PDF.

## 7. Assemble and inspect the final document

Re-run the Stage 8 assembly (`references/stage_08_writing.md` §8) if any section changed since the last pass: concatenate the approved `paper_workspace/*.md` files into `paper.md`, then convert with pandoc into `paper.docx`. Compilation succeeds only when `paper.docx` exists, includes all intended sections in order, and pandoc reports no unresolved reference/image warnings. Visually inspect the first page, dense equations, wide tables, figure-heavy pages, references, appendices, and the AI disclosure after the user applies the current year's formatting in Word and exports the final submission PDF.

## 8. Persist the final gate

Write actual runtime-derived counts and paths. The schema is:

```json
{
  "anti_patterns_check": {
    "total": null,
    "passed": null,
    "fixed": null,
    "deferred": null
  },
  "compliance_checks": {
    "rules_verified": null,
    "anonymity_passed": null,
    "page_limit_passed": null,
    "ai_disclosure_passed": null,
    "supporting_materials_passed": null
  },
  "final_pdf_path": "paper_output/paper.pdf",
  "submission_ready": null
}
```

The `null` values above are schema placeholders only. Replace every one with an observed count or verified boolean before persisting Stage 9; never copy a sample result into the final gate.

## Exit conditions

- current official rules verified with no unresolved violation;
- anti-pattern and consistency checks completed;
- all high-severity panel findings resolved;
- PDF compiled and visually inspected;
- AI disclosure and supporting materials complete when required;
- `decision_log.stages.9.submission_ready == true`.

Only then hand the final submission package back to the team.
