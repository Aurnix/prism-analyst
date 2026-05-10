# PRISM Analyst MVP Plan

This plan defines the first build of PRISM Analyst as a separate repo optimized to run entirely inside Perplexity Computer. The MVP should prioritize AE usability, low operating cost, transparent evidence, and markdown/CSV outputs.

## Product thesis

Most GTM intelligence tools over-collect and over-report. PRISM Analyst should do the opposite: collect enough public evidence to decide whether an account deserves action, then spend deeper LLM analysis only on accounts with credible buying-readiness signals.

## MVP scope

The MVP should support:

- Single-account analysis by name, domain, or URL.
- Batch analysis from CSV.
- Deterministic no-LLM scoring.
- Low-cost quick LLM brief.
- Gated full dossier generation.
- Markdown and CSV outputs.
- Filesystem caching.
- Manual/paste ingestion.
- Weekly monitoring design, even if scheduling is operated by Computer rather than the repo itself.

The MVP should not include:

- FastAPI backend.
- Database.
- Redis/task queue.
- Multi-user auth.
- Required Apollo or Proxycurl dependency.
- Required CRM integration.
- Web UI.

## Milestone one: Local AE analyst

### Goal

Create the smallest useful CLI that can analyze one company or a CSV of companies and produce no-LLM account snapshots and scorecards.

### Features

- `prism-analyst analyze <company_or_domain> --mode no-llm`
- `prism-analyst batch <accounts.csv> --mode no-llm`
- Domain normalization.
- Basic website fetch.
- News RSS lookup.
- Job page discovery where obvious.
- Manual notes ingestion.
- Raw source cache.
- Deterministic signal extraction.
- ICP and timing score.
- Markdown snapshot.
- CSV scorecard.

### Outputs

```text
output/
  accounts/
    <slug>/
      account_snapshot.md
      scorecard.json
      signals.json
      sources.json
  batch_scorecard.csv
```

### Acceptance criteria

- A non-engineer can run analysis on one company from the CLI.
- A CSV of 10 accounts produces a ranked scorecard.
- The workflow can complete without an LLM API key.
- Every score includes confidence and source references.
- Re-running an account uses cached content when fresh.

## Milestone two: Quick brief and evidence pack

### Goal

Add the first LLM-powered layer while keeping costs controlled.

### Features

- Evidence pack builder.
- Prompt for quick account brief.
- Configurable max evidence items.
- Configurable model name.
- LLM response caching.
- `--mode quick`
- `--quick-threshold`
- Batch gated mode.

### Quick brief sections

1. Account read
2. Most important signals
3. Buying-readiness stage
4. Why-now hypothesis
5. Recommended next action
6. Suggested outreach angle
7. Collection gaps
8. Confidence

### Acceptance criteria

- Quick mode uses a compact evidence pack, not the entire corpus.
- Batch mode only runs quick briefs for accounts above threshold.
- LLM outputs are cached by account, prompt version, model, and evidence hash.
- The brief is useful to an AE in under five minutes of reading.

## Milestone three: Full dossier mode

### Goal

Generate the full 9-section PRISM-style intelligence dossier for accounts worth deeper analysis.

### Features

- `--mode full`
- Full dossier prompt or staged prompt chain.
- Signal timeline renderer.
- Counter-signal section.
- Discovery questions.
- Source appendix.
- Full-mode gating in batch runs.

### Dossier sections (titles match PRISM-v2 verbatim)

1. Executive Summary
2. Subject Profile
3. Organizational Intelligence Assessment
4. Key Personnel — Buying Committee Map
5. Signal Timeline
6. Why Now — Hypothesis
7. Recommended Play
8. Collection Gaps & Discovery Questions
9. Appendix — Raw Signals & Sources

### Acceptance criteria

- Full dossiers are generated only when requested or threshold-qualified.
- Dossiers contain source links and confidence labels.
- Sparse accounts produce lower-confidence dossiers rather than hallucinated certainty.
- The renderer works from structured intermediate outputs, not raw freeform text only.

## Milestone four: Gift document mode

### Goal

Convert internal account intelligence into a prospect-safe artifact.

### Features

- `prism-analyst gift <account_slug>`
- Redaction rules.
- Reframing rules.
- Redaction report.
- Prospect-safe markdown output.

### Remove from gift docs

- Internal scores.
- Sales tactics.
- Competitive references.
- Unverified claims.
- Sensitive assumptions about individuals.
- Anything that sounds like surveillance.

### Preserve in gift docs

- Market context.
- Operational patterns.
- Publicly observable trends.
- Useful questions.
- Educational framing.

### Acceptance criteria

- Gift docs do not reveal internal scoring or sales strategy.
- Gift docs are framed as helpful market insight.
- A redaction report explains what was removed.

## Milestone five: Monitoring and deltas

### Goal

Support weekly account monitoring through Computer scheduling and local run snapshots.

### Features

- Run snapshots.
- `prism-analyst digest <account_slug>`
- Compare current signals to previous run.
- Materiality thresholds.
- Markdown digest.
- Batch digest summary.

### Material changes

Examples:

- New executive hire.
- New finance/accounting job posting.
- Funding announcement.
- Product expansion.
- Pricing or packaging change.
- Hiring spike.
- New integration or migration clue.
- Strong shift in messaging.

### Acceptance criteria

- Re-running an account creates a comparable snapshot.
- Digest identifies new, changed, and decayed signals.
- Computer can schedule weekly batch runs.
- User is notified only when material changes are found.

## Data model

The MVP uses lightweight Pydantic models that mirror PRISM-v2's field names so artifacts can move between systems:

- `AccountProfile` (with optional firmographics: `funding_stage`, `growth_rate`, `tech_stack`)
- `SourceItem`
- `Signal` — fields: `signal_type` (one of 19 PRISM-v2 types), `category`, `description`, `source`, `detected_date`, `decay_weight`, `confidence` (`extracted | interpolated | generated`), `contact_name`
- `Scorecard` — with `icp_breakdown`, `readiness_breakdown`, `timing_breakdown` and stored composite `weights`
- `EvidencePack` / `EvidenceItem`
- `Brief`
- `Dossier` (carries optional structured views: `scorecard`, `signals`, `sources`, `profile`)
- `GiftDocument`
- `RunSnapshot`
- `Digest` — with `score_snapshot`, severity-grouped `entries`, typed `new_signals` / `decayed_signals` / `removed_signals` / `changed_signals` deltas, `action_update`, `llm_narrative`

## Scoring model

Composite score (matches PRISM-v2 so outputs stay interchangeable):

```text
Composite = ICP Fit 25% + Buying Readiness 50% + Timing 25%
```

Buying readiness still scores in no-LLM mode by aggregating deterministic pain, leadership, competitive, and timing signals — the dominant weight is preserved across modes.

### ICP fit subcomponents (matches PRISM-v2)

```text
ICP Fit = funding_stage 25% + growth_rate 20% + tech_stack 20%
        + headcount 15% + industry 10% + geo 10%
```

### Tier thresholds (matches PRISM-v2)

```text
Tier 1: >= 70
Tier 2: >= 45
Tier 3: >= 25
Not qualified: < 25
```

### Confidence adjustment

Confidence should not change the raw score silently. Instead, display it next to the score:

```text
Score: 78
Tier: Tier 1
Confidence: Medium
Reason: Strong job and news signals, but limited first-party blog content.
```

## Prompt design

Prompts should be short, versioned, and evidence-bound.

Rules:

- Never ask the model to browse.
- Never include the full raw corpus by default.
- Include source IDs and excerpts.
- Force counter-signals.
- Force confidence.
- Force discovery questions.
- Prefer concise AE language over analyst jargon.

## Testing plan

### Unit tests

- Domain normalization.
- Source cache keys.
- Signal extraction rules.
- Signal decay.
- Score calculation.
- Evidence pack ranking.
- Gift redaction.

### Golden tests

- Fixed demo accounts should produce stable no-LLM scorecards.
- Prompt outputs should be snapshot-tested where feasible.
- Sparse accounts should produce low-confidence outputs.

### End-to-end smoke tests

- Analyze one account with no LLM.
- Analyze one account in quick mode.
- Batch analyze five demo accounts.
- Generate one full dossier.
- Generate one gift document.
- Compare two snapshots.

## Repo bootstrap checklist

1. Create `prism-analyst` repo.
2. Add Python package scaffold.
3. Add CLI with Click or Typer.
4. Add Pydantic models.
5. Add workspace/cache layer.
6. Add no-LLM collectors.
7. Add deterministic signal extraction.
8. Add scoring and tiering.
9. Add markdown and CSV renderers.
10. Add evidence pack builder.
11. Add LLM backend abstraction.
12. Add quick brief prompt.
13. Add full dossier prompt.
14. Add gift document prompt and redaction rules.
15. Add snapshot/digest workflow.
16. Add example CSV and demo data.
17. Add tests.
18. Add `AGENT_MODE.md`.

## First implementation sequence

Build in this exact order:

1. Models.
2. Workspace/cache.
3. CLI shell.
4. No-LLM single-account analysis.
5. Batch scorecard.
6. Evidence pack builder.
7. Quick LLM brief.
8. Full dossier.
9. Gift doc.
10. Snapshot diff and digest.

This sequence ensures the tool is useful before any expensive LLM functionality is added.

## Definition of MVP done

The MVP is done when an AE can provide a CSV of accounts and receive:

- A ranked scorecard.
- Quick briefs for qualified accounts.
- Full dossiers for top accounts when requested.
- Source links and confidence labels.
- Clear discovery questions.
- A prospect-safe gift document for one account.
- A repeatable workflow Computer can run again next week.

