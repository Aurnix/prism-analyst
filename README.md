# PRISM Analyst

PRISM Analyst is a lightweight, Perplexity Computer-native account intelligence workflow for AEs, founders, and GTM teams. It analyzes target companies from public signals, estimates buying readiness, generates account dossiers, and creates prospect-safe "gift" documents while keeping scraping and LLM costs low.

This project is intentionally not a full SaaS backend. It is designed to run inside Perplexity Computer or a local Python environment with simple filesystem state, cached evidence, markdown outputs, and optional API integrations.

## What it does

Given a company name, domain, URL, or CSV of accounts, PRISM Analyst can:

- Resolve a target account into a normalized company profile.
- Collect low-cost public signals from company pages, blogs, news, jobs, GitHub, and manually pasted content.
- Extract buying-readiness signals from public language and recent activity.
- Score accounts using ICP fit, signal strength, timing, and confidence.
- Generate AE-ready account briefs and full intelligence dossiers.
- Produce prospect-safe gift documents with internal sales logic removed.
- Run weekly monitoring checks and surface only material changes.

## Design goal

PRISM Analyst optimizes for this operating principle:

> Spend intelligence only where there is evidence of actionability.

The workflow scrapes broadly but shallowly, caches everything, uses deterministic scoring first, and only runs deeper LLM analysis when an account crosses a configurable threshold or a user explicitly requests it.

## Intended user

The primary user is an AE or GTM operator who wants to quickly answer:

- Should I spend time on this account?
- Why now?
- Who should I contact?
- What message will likely resonate?
- What do I still need to learn in discovery?
- Has anything changed since last week?

## Example usage

Analyze one company quickly:

```bash
prism-analyst analyze stripe.com --mode quick
```

Analyze a CSV of accounts without LLM calls:

```bash
prism-analyst batch examples/accounts.csv --mode no-llm
```

Generate full dossiers only for accounts above a score threshold:

```bash
prism-analyst batch examples/accounts.csv --mode gated --full-threshold 70
```

Generate a prospect-safe gift document:

```bash
prism-analyst gift velocitypay
```

Compare the latest run against the previous run:

```bash
prism-analyst digest velocitypay
```

## Modes

### No-LLM mode

The cheapest mode. It uses deterministic collection, pattern extraction, signal decay, and rules-based scoring.

Use it to:

- Filter a long account list.
- Generate rough priority scores.
- Avoid wasting LLM calls on weak accounts.

Outputs:

- Account snapshot
- Scorecard CSV
- Raw signal inventory
- Collection gaps

### Quick mode

The default AE workflow. It builds a curated evidence pack and runs a compact LLM pass to summarize buying readiness, likely pain, why-now hypothesis, and recommended next action.

Use it to:

- Qualify an account before outreach.
- Prepare for a call.
- Decide whether a full dossier is worth generating.

Outputs:

- Quick account brief
- Buying-readiness score
- Why-now hypothesis
- Outreach angle
- Confidence assessment

### Full mode

The deeper analysis mode. It generates a complete dossier using a multi-stage Content Intelligence chain.

Use it when:

- The account is high fit.
- There are strong recent signals.
- The AE wants a full pre-call brief.
- A material weekly change was detected.

Outputs:

- 9-section intelligence dossier
- Signal timeline
- Buying committee notes where available
- Per-person messaging recommendations
- Discovery questions
- Appendix of sources and raw signals

### Gift mode

Gift mode converts internal account intelligence into a prospect-safe document. It removes internal scores, tactical sales instructions, competitive positioning, and sensitive assumptions while preserving useful market context and operational observations.

Use it to create:

- Prospect-facing market memos
- Operational benchmark briefs
- Discovery-call leave-behinds
- "We noticed this pattern" documents

## Dossier structure

Full dossiers use the same 9-section format as PRISM-v2 (titles match verbatim so downstream tools can consume either system's output):

1. Executive Summary
2. Subject Profile
3. Organizational Intelligence Assessment
4. Key Personnel — Buying Committee Map
5. Signal Timeline
6. Why Now — Hypothesis
7. Recommended Play
8. Collection Gaps & Discovery Questions
9. Appendix — Raw Signals & Sources

The renderer adds three structural blocks alongside the LLM section content:

- **Score tree** in the Executive Summary — composite, ICP fit, buying readiness, timing, each with its weight and a decay-bar visualization (`█▓▒░`).
- **ICP / Readiness / Timing breakdowns** — each subcomponent with its weight, mirroring PRISM-v2's scoring tables.
- **Decay-weighted Signal Timeline** — chronological signals tagged with their specific PRISM signal type and confidence label.

## PRISM-v2 alignment

PRISM Analyst produces the same artifact types as PRISM-v2 so outputs are interchangeable:

- **19 signal types** match the PRISM-v2 taxonomy verbatim: `funding_round`, `new_executive_finance`, `new_executive_other`, `champion_departed`, `job_posting_finance`, `job_posting_technical`, `job_posting_urgent`, `tech_stack_change`, `migration_signal`, `blog_post_pain`, `linkedin_post_pain`, `earnings_mention`, `press_release_relevant`, `pricing_page_visit`, `content_engagement`, `g2_research_activity`, `competitor_evaluation`, `competitor_contract_renewal`, `glassdoor_trend`.
- **Per-signal decay** uses the same `(peak_days, half_life_days, max_relevance_days)` table as v2.
- **Signal model fields** match: `signal_type`, `description`, `source`, `detected_date`, `decay_weight`, `confidence` (`extracted | interpolated | generated`), `contact_name`.
- **Composite scoring weights** match v2: ICP Fit 25% + Buying Readiness 50% + Timing 25%.
- **ICP fit subcomponents** match v2 weights: funding stage 25%, growth rate 20%, tech stack 20%, headcount 15%, industry 10%, geo 10%.
- **Tier thresholds** match v2: Tier 1 ≥ 70, Tier 2 ≥ 45, Tier 3 ≥ 25.
- **Digest deltas** use the v2 vocabulary (`new`, `decayed`, `removed`, `changed`) and the same severity entries (`critical`, `warning`, `update`).
- **Play matrix** uses the same play identifiers (`educational_urgency`, `direct_solution`, `accelerated_close`, `competitive_wedge`, `competitive_education`, `long_nurture`, `educational_nurture`).
- **Gift documents** apply the same redaction/reframing rules.

PRISM Analyst stays lighter than v2 in scope (no FastAPI, no DB, no required enrichment vendors) but the artifacts it emits — scorecards, snapshots, dossiers, digests, gift documents — are schema-compatible.

## Cost-control strategy

PRISM Analyst is designed to avoid unnecessary LLM and scraping spend:

- Cache every fetched page, extracted text, evidence pack, and LLM output.
- Default to no-LLM scoring for batch account screening.
- Limit quick mode to the strongest 5 to 10 evidence items.
- Gate full dossiers behind score thresholds.
- Use source recency and signal strength to decide whether deeper analysis is worthwhile.
- Reuse prior run snapshots during weekly monitoring.
- Generate digests only when material changes occur.

## Project structure

```text
prism-analyst/
  prism_analyst/
    cli.py
    config.py
    workspace.py
    models.py

    collect/
      website.py
      news.py
      jobs.py
      github.py
      manual.py

    signals/
      extract.py
      score.py
      decay.py
      confidence.py

    llm/
      backend.py
      evidence_pack.py
      prompts/
        quick_brief.md
        full_dossier.md
        person_messaging.md
        gift_doc.md

    render/
      snapshot.py
      dossier.py
      digest.py
      gift.py
      csv.py

    workflows/
      analyze.py
      batch.py
      monitor.py
      gift.py

  examples/
    accounts.csv
    demo_inputs/

  output/
  cache/
  README.md
  AGENT_MODE.md
  MVP_PLAN.md
```

## Workspace state

PRISM Analyst stores state in regular files so Computer can inspect, reuse, and share outputs easily:

```text
.prism/
  accounts/
    velocitypay/
      profile.json
      sources.json
      signals.json
      runs/
        2026-05-10T15-30-00/
          evidence_pack.json
          scorecard.json
          quick_brief.md
          dossier.md
          gift.md
```

## Configuration

Configuration should live in `prism_analyst/config.py` and optionally `.env`:

```text
ANTHROPIC_API_KEY=
PRISM_ANALYST_MODEL=
PRISM_ANALYST_MAX_EVIDENCE_ITEMS=10
PRISM_ANALYST_FULL_THRESHOLD=70
PRISM_ANALYST_QUICK_THRESHOLD=45
PRISM_ANALYST_CACHE_TTL_DAYS=14
```

All weights and thresholds should be centralized and editable without changing workflow logic.

## Optional integrations

The MVP should not require external enrichment vendors. Integrations should be optional and degrade gracefully:

- Apollo for company/contact enrichment.
- Proxycurl or compliant LinkedIn data providers for person-level content.
- GitHub for technical activity.
- HubSpot or Salesforce for CRM context.
- Google Sheets or CSV for account lists.

If an integration is unavailable, PRISM Analyst should still produce a lower-confidence brief.

## Development principles

- Prefer markdown and CSV outputs over complex UI.
- Prefer filesystem state over a database.
- Prefer cached public content over repeated scraping.
- Prefer deterministic filtering before LLM synthesis.
- Prefer confidence labels over false precision.
- Prefer AE usability over architecture purity.
- Keep the repo runnable by a non-engineer inside Perplexity Computer.

## License

All rights reserved unless otherwise specified.

