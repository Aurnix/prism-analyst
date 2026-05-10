# PRISM Analyst Agent Mode

Agent Mode defines how PRISM Analyst should behave when operated by Perplexity Computer. The goal is to let an AE run account intelligence workflows conversationally without managing infrastructure, APIs, databases, workers, or deployment.

## Purpose

PRISM Analyst should feel like an AE-facing analyst, not a developer tool. A user should be able to say:

> Analyze these 15 target accounts, tell me which are worth acting on this week, and generate full dossiers only for the best ones.

Computer should then run the appropriate PRISM Analyst workflow, cache evidence, create scorecards, generate dossiers, and return the usable files.

## Agent responsibilities

When operating PRISM Analyst, Computer is responsible for:

- Choosing the lowest-cost mode that satisfies the request.
- Running batch screening before full dossier generation.
- Inspecting cached evidence before fetching new content.
- Asking for clarification only when the missing detail materially affects the work.
- Explaining confidence and collection gaps honestly.
- Sharing generated files with the user.
- Scheduling monitoring only after explicit user approval.

## Default behavior

Unless the user asks for a full dossier, Agent Mode should default to:

1. No-LLM collection and scoring.
2. Quick LLM brief only for accounts above the quick threshold.
3. Full dossier only for accounts above the full threshold or specifically requested accounts.
4. Gift document only when explicitly requested.

## Recommended command mapping

### Single account analysis

User says:

> Analyze Acme Corp.

Computer should run:

```bash
prism-analyst analyze "Acme Corp" --mode quick
```

Expected outputs:

- `account_snapshot.md`
- `scorecard.json`
- `quick_brief.md`
- source cache

### Batch account screening

User uploads or pastes a list of accounts.

Computer should run:

```bash
prism-analyst batch accounts.csv --mode gated
```

Expected outputs:

- `batch_scorecard.csv`
- short markdown summary
- full dossiers only for accounts above threshold

### Full dossier

User says:

> Generate the full dossier for VelocityPay.

Computer should run:

```bash
prism-analyst analyze velocitypay --mode full
```

Expected outputs:

- `dossier.md`
- `scorecard.json`
- `signals.json`
- source appendix

### Prospect-safe gift document

User says:

> Turn this into a gift doc for the prospect.

Computer should run:

```bash
prism-analyst gift velocitypay
```

Expected outputs:

- `gift.md`
- `redaction_report.json`

Computer should preview or summarize what was removed before suggesting that the user send or share it externally.

### Weekly monitoring

User says:

> Monitor these accounts weekly.

Computer should explain that recurring tasks use credits, then request confirmation before scheduling. After approval, Computer should run the batch workflow weekly and notify the user only when material changes occur.

## Tool surface

The repo should expose functions that are easy for Computer to call directly or through the CLI:

```python
resolve_company(input: str) -> AccountProfile
collect_sources(account: AccountProfile, mode: str) -> SourceBundle
extract_signals(source_bundle: SourceBundle) -> SignalSet
score_account(account: AccountProfile, signals: SignalSet) -> Scorecard
build_evidence_pack(account: AccountProfile, signals: SignalSet, max_items: int) -> EvidencePack
run_quick_brief(evidence_pack: EvidencePack) -> Brief
run_full_dossier(evidence_pack: EvidencePack) -> Dossier
generate_gift(dossier: Dossier) -> GiftDocument
compare_runs(account_slug: str) -> Digest
```

The CLI should be a thin wrapper around these functions.

## Cost-aware execution ladder

Agent Mode should follow this ladder:

### Step one: cache check

Before fetching anything, inspect the workspace cache.

If the cached content is fresh enough, reuse it.

### Step two: deterministic scan

Collect and score without LLM calls:

- Website metadata
- Existing cached pages
- Recent news RSS
- Job titles and job descriptions
- Basic funding/stage/headcount if provided
- Keyword and pattern signals
- Recency and confidence

### Step three: evidence pack

Build a compact evidence pack from the strongest available signals. The evidence pack should be intentionally small:

- 5 to 10 items by default
- source title
- URL
- date
- excerpt
- detected signal types (specific PRISM-v2 types, e.g. `funding_round`, `migration_signal`, `linkedin_post_pain`)
- per-signal confidence label (`extracted | interpolated | generated`)
- relevance reason

### Step four: quick brief

Run one compact LLM call to generate:

- Account read
- Why-now hypothesis
- Buying-readiness stage
- Recommended next action
- Confidence
- Discovery questions

### Step five: full dossier

Generate a full dossier only if:

- User requested it.
- Account score exceeds threshold.
- Material monitoring delta is detected.
- AE marks the account as strategic.

## Caching rules

Every expensive operation should write a cache artifact:

- Raw fetched HTML or text.
- Extracted clean text.
- Signal extraction output.
- Evidence pack.
- LLM response.
- Rendered markdown.

Cache keys should include:

- account slug
- source URL or input hash
- mode
- prompt version
- model name
- timestamp

## Output rules

Agent Mode should favor practical GTM outputs:

- Markdown for human-readable briefs.
- CSV for account rankings.
- JSON for machine-readable state.
- PDF or DOCX only when the user explicitly asks.

All reports should include:

- Confidence level (`high | medium | low` at the account level; `extracted | interpolated | generated` per signal)
- Source list
- Collection gaps
- Counter-signals
- Recommended next action

The full dossier additionally includes a score-tree showing the composite breakdown with weights, ICP/readiness/timing subcomponents, and a decay-weighted signal timeline — same shape as PRISM-v2.

## Human-in-the-loop rules

Computer should ask before:

- Scheduling recurring monitoring.
- Sending or posting any outreach.
- Updating CRM records.
- Generating large batches when the account count is high.
- Running full dossier mode across many accounts.

Computer should not ask before:

- Running a quick single-account scan.
- Reading cached files.
- Generating local markdown outputs.
- Creating a scorecard from a small CSV.

## Confidence model

Every output should include a confidence label:

- High: multiple recent, consistent signals from credible sources.
- Medium: some relevant signals, but gaps remain.
- Low: sparse corpus, stale sources, weak evidence, or inferred conclusions.

The system should avoid pretending sparse data is decisive. Low-confidence accounts can still be worth outreach, but the recommended play should shift toward discovery rather than assertive point-of-view messaging.

## AE-friendly language

Reports should avoid academic or model-centric phrasing. The AE should see:

- What changed
- Why it matters
- Who to contact
- What to say
- What not to say
- What to ask first

## Anti-goals

Agent Mode should not become:

- A production CRM replacement.
- A multi-tenant SaaS backend.
- A web scraping platform.
- A black-box lead score.
- A report generator that ignores cost.
- A workflow that requires an engineer to operate.

## Definition of done

Agent Mode is working when an AE can:

1. Provide a company or CSV.
2. Receive a ranked account scorecard.
3. Open a useful brief or dossier.
4. See sources and confidence.
5. Generate a prospect-safe gift doc.
6. Re-run later and understand what changed.

