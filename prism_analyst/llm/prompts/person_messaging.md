You are crafting personalized messaging recommendations for a specific person at **{{ACCOUNT_NAME}}**.

## Person

Name: {{PERSON_NAME}}
Title: {{PERSON_TITLE}}
Role context: {{ROLE_CONTEXT}}

## Evidence

{{EVIDENCE}}

## Instructions

- Base recommendations only on the evidence provided.
- Tailor the message to this person's likely priorities based on their title and role.
- Suggest what to say, what not to say, and what to ask.
- Keep it concise and actionable for an AE.

## Output format

### Messaging Recommendation

**Opening angle:** One sentence the AE could use to open a conversation.

**Key points to raise:** 3-5 bullet points tailored to this person's likely concerns.

**Questions to ask:** 3-5 discovery questions relevant to this person's domain.

**What to avoid:** Bullet list of topics or framings to avoid with this person.

**Confidence:** High, Medium, or Low with one sentence explanation.
