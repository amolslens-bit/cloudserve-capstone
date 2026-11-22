# T11 - data-commitment flag vs labels (all 500 dev tickets)

data_residency tickets: 29 total, 21 labelled auto_respond, 8 labelled escalate. None are must-not-auto-respond.
They come from 3 body templates (wording variants grouped):

| Template | auto | escalate |
|---|---|---|
| "customer asked for written confirmation of where data is physically stored, point me to something I can share" | 9 | 5 (DEV-0061, 0118, 0123, 0275, 0432) |
| "need data to remain within the EU for a contract we are signing, not sure which region" | 6 | 3 (DEV-0110, 0154, 0359) |
| "are backups replicated outside our primary region? compliance review" | 6 | 0 |

Identical bodies are labelled both ways (DEV-0433 auto vs DEV-0061 escalate; DEV-0483 auto vs DEV-0110 escalate).
Tier, channel and region do not separate them; the escalate ones are all answerable_from_docs=false, expected_doc_ids=[].
So no wording rule can get all 29: flag false on all three gives 21/29, flag true (today's "if unsure, true") gives 8/29.
dev200 contains only the auto ones, which is why batch 4 showed 4 misses.

Proposed PR-01 1.3 rule (draft, not applied):
Set "data_commitment_request" to true only if the customer asks CloudServe itself to sign, guarantee or contractually commit to where data is stored (for example a signed letter, a DPA change, or a custom guarantee). Asking for existing documentation to share, asking which region they are in, or asking how backups are replicated is false. If unsure, set it to false.
Plus one example: "customer asked for written confirmation ... point me to something I can share" -> data_residency, false.
