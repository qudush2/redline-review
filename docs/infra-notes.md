# Infra notes (for Part II)

Running notes on what would change to take this from a local prototype to production. Each item names the shortcut taken in Part I and what replaces it.

## Storage

- **Now:** a Python dictionary in `store.py`; data lasts until the server restarts.
- **Production:** Postgres for document metadata, versions, and the audit log; object storage (S3) for large document bodies.
- **Versions:** store diffs, not full snapshots. Ten edits to a 10MB contract currently hold ~100MB in memory.
- **Keep:** all access already goes through `store.py`, so the swap is contained to one module.

## Concurrency

- **Now:** one `threading.Lock` around "check version → apply → save," plus `expected_version` → 409. The lock only works inside one server process.
- **Production:** optimistic locking in the database: `UPDATE documents SET … WHERE id = $1 AND version = $2`, and treat zero rows updated as a 409. This works across many servers with no shared lock. Row locks are the alternative for long transactions.

## Search

- **Now:** a linear scan per query, about 0.1 seconds on 10MB, and always consistent with the latest edit.
- **Production:** Postgres full-text search to start, or OpenSearch once there are many documents per tenant. Re-index from a queue after each save, so writes stay fast and search is eventually consistent (seconds behind).
- Keep a final exact-match check against the stored text for phrase searches. Index hits are candidates, not proof.

## Uploads

- **Now:** converted in the request, 20MB limit, .docx/.md/.txt only.
- **Production:** virus scanning before conversion; async conversion workers for large .docx files (return 202 plus a status endpoint); store the original file next to the Markdown so "export to Word with tracked changes" can preserve formatting.
- **Lesson from Part I:** the Next.js dev proxy timed out on a 15MB upload that FastAPI handled in 0.07s. In production, uploads should go straight to storage via pre-signed URLs, not through an app-server proxy.

## AI

- **Zero data retention** agreement with the model provider; contracts are confidential.
- **Per-tenant playbooks** stored in the database, versioned like documents, so a suggestion can cite which playbook version it used.
- **Chunking** for contracts over the current 150k-character cap: review by section, then merge and re-validate the suggestions.
- **Rate limits and cost caps** per tenant; log tokens per request.
- **Audit:** log the prompt, model, and raw output with each suggestion, alongside whether it was kept or dropped and who accepted it.
- **Keep:** the deterministic guardrail (apply every suggestion to the real text before showing it) and the server-side refusal fallback.

## Security and compliance

- **SSO** (SAML/OIDC) and role-based permissions per matter (who can view, edit, approve).
- Encryption in transit (TLS) and at rest (KMS-managed keys; customer-managed keys for enterprise).
- **Immutable audit log:** append-only, and exportable for review.
- SOC 2 controls (access reviews, change management, incident response); GDPR (data residency options, deletion requests that respect legal holds).
- Today's "Editing as" is a free-text name. It becomes the authenticated user.

## Observability

- Request latency and error rates **by error `type`** (`ambiguous_match`, `version_conflict`, …). The consistent error shape makes this a simple group-by.
- **AI suggestion drop rate**, as a hallucination signal. If it rises after a model or prompt change, something regressed.
- **Accept/reject rates per suggestion source**, as a product signal for whether AI suggestions are useful.
- Conflict (409) rate, to show how often lawyers collide on the same document.

## Cost

- The main variable cost is AI tokens. Cache the playbook and system prompt (stable prefix), and only send changed sections on repeat reviews.
- Search and storage are cheap at contract-library scale. The snapshot-vs-diff change matters more for memory than for dollars.

## CI/CD

- On every PR: backend tests (including the 10MB performance tests with generous limits), frontend type-check and lint.
- Preview environments per PR, with seeded fictional contracts.
- Deploy the API and web app separately; run database migrations before rolling out the API.
