# Generic answer-key replies (found during PR-08 hand check, 20 Nov 2026)

Source: ground-truth responses for the 200 answer-key dev tickets (no AI calls, holdout not opened).

- 79 of 200 reference replies (40%) are the SAME word-for-word generic text
  ("Based on what you have described, the relevant guidance in our documentation covers the likely causes...").
  They name no article and no step.
- All 79 have an empty must_mention list (the other 121 tickets: 62 empty).
- Intents: sso_configuration 15, quota_or_overage 13, data_residency 11, compliance_request 10,
  security_incident 9, integration_help 7, performance_degradation 7, database_issue 7.
- Batch 4 (dev200_04): 15 of 50 tickets have the generic reply; 7 of those were auto-answered by our AI
  (DEV-0396, 0403, 0414, 0450, 0451, 0471, 0472).
- Example DEV-0396 (SAML bounce): the reference says "start with the checks listed there"; our AI gave the
  4 Resolution steps of DOC-AUTH-003.

Implication: for these 79 tickets there is nothing in the answer key to compare an answer against except the
expected article. Answers are judged against the cited article and must_mention (PR-08 and hand check), not
against reference wording. A wording-similarity score would understate the AI. Discovery gap: not spotted at
Stage 1; caught during testing.
