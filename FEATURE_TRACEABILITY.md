# JustiFi feature traceability

This matrix compares the existing repository with the 18-page research
presentation, `JustiFi An Intelligent Web-Based Legal Companion for
Simplifying Indian Laws and Legal Procedures.pdf`. “Implemented” describes a
code path, not proof of legal correctness or live external-service operation.
The evaluation JSON contains scenario expectations, not measured accuracy.

## Research objectives and proposed framework

| PPT requirement | Implementation status | Evidence and remaining gap |
|---|---|---|
| Plain-language access to complex Indian laws for ordinary citizens | Partial | A live backend legal query through FastAPI, SQLite retrieval, and Gemini returned HTTP 200 with source-ID citations mapped to retrieved BNS chunks. This does not establish legal accuracy or verify the frontend browser path. The last recorded live OpenAI attempt returned HTTP 429 `credit_balance_exhausted`. |
| NLP/LLM-based legal-text understanding and simplification | Partial | Retrieved passages are formatted into a constrained prompt sent to Gemini or OpenAI. The actual corpus-to-Gemini-to-citation backend path was live-tested; no separate legal NLP, normalization, or classification component is implemented, and expert review is still required. |
| Retrieval-Augmented Generation grounded in legal passages | Partial | SQLite lexical retrieval was tested against the re-imported 1,322-chunk corpus. Murder/culpable-homicide requests returned BNS §§100/101; punishment requests returned §§103/105; explicit BNSS §103 requests returned BNSS-only records. All records remain `needs_review`; no semantic embedding index is implemented. |
| Authentic legal sources, including India Code, e-Gazette, and government portals | Not verified / incomplete | Local BNS and BNSS PDFs and the HTML IPC/BNS section table are present and extract locally; imported records are deliberately marked `needs_review`. No source provenance, official-source verification, currentness check, or verified source URLs were established. |
| Legal verification and connection to authentic references | Partial | Responses expose IDs and metadata from returned database records; source browser exposes records and verification labels. Source content is not independently authenticated and no claim-by-claim answer verifier exists. |
| Legal timeframe handling and IPC-to-BNS transition | Partial | User can submit a timeframe and the answer receives a limitation. Document dates are extracted, reviewed, and passed to document analysis. There is no effective-date corpus, provision mapping, law-version filtering, or statutory deadline calculation. |
| English, Hindi, and Marathi accessibility | Partial | UI copy dictionaries provide all shared keys in all three languages; the selected language is sent to question/document endpoints. Some static UI strings remain English. Search quality and live answer language quality have not been evaluated; mocked provider coverage is not evidence of live generation. |
| PII detection and redaction before external processing | Partial | Common emails, Indian mobile numbers, PAN-like strings, and 12-digit identifiers are pattern-redacted before retrieval/AI. Coverage is incomplete; names, addresses, context-specific identifiers, OCR text, and other PII may be missed. |
| Privacy-first document processing | Partial | PDF/DOCX/TXT are extracted in memory, original/redacted previews are shown, consent is required, pending data can be cleared, and previews expire. No OCR, authentication, durable audit controls, or comprehensive PII detection is provided. |
| PPT processing flow: user question/document → privacy → retrieval → LLM → source grounding → multilingual response | Backend live integration verified; frontend path partial | A live backend request exercised privacy redaction, actual SQLite retrieval, Gemini, and citation response mapping. HTTP 200 was returned and citation IDs/metadata matched retrieved chunks. The browser UI path, document-analysis flow, and live Hindi/Marathi behavior were not verified in this test. |
| Explain documents, with source-grounded output | Partial | Document analysis accepts retrieved records and distinguishes uploaded text from legal evidence. Extraction works locally, but no live analysis succeeded; OCR is unavailable. |

## Expected outcomes, practical significance, and future work in the PPT

| PPT item | Status | Evidence / limitation |
|---|---|---|
| Clearer understanding and access to legal information | Intended, not evaluated | UI and explanation workflow exist; no user study or live legal answer evaluation has been completed. |
| Transparency through authentic references | Partial | Citation cards/source explorer show stored metadata and `verification_status`; current imported records are marked `needs_review` and are not independently verified. |
| Access for citizens, educational institutions, NGOs, and legal-aid organizations | Prototype only | No deployment, organization support, or user research has been conducted. |
| Free basic access and potential institutional subscriptions/custom deployments | Not implemented | No billing, subscription, tenant, or institutional deployment model exists. |
| Sustainability, AI/cloud costs, maintenance, and legal-source updates | Not implemented / not assessed | No operating-cost study or automated legal update pipeline exists. |
| Accuracy, retrieval quality, and source-correctness evaluation | Not completed | `backend/evaluation/legal_queries.json` is a checklist only; there are no measured scores or expert assessments. |
| Multilingual quality evaluation | Not completed | All shared UI dictionary keys are translated, but no measured English/Hindi/Marathi retrieval or answer evaluation exists. Some fixed captions remain English. |
| Privacy/security assessment | Partial | Pattern-redaction and upload tests exist; no independent security/privacy assessment or comprehensive PII recall measurement exists. |
| Usability study across education and language backgrounds | Not conducted | Browser smoke checks are engineering checks, not user research. |
| Business feasibility, adoption, partnerships, and subscription validation | Not conducted | These are PPT future-work topics, not implemented product capabilities. |
| Legal professionals remain necessary for advice | Implemented as product disclaimer | UI and API explain that outputs are general legal information, not legal advice. This does not substitute for professional review. |

## Additional scope from the supplied implementation brief

| Brief feature | Status | Evidence / limitation |
|---|---|---|
| Dashboard and navigation shortcuts | Implemented | Seven navigation destinations were exercised in the browser. |
| Explore Laws and Legal Sources | Implemented; source records available locally | SQLite-backed search/detail routes and UI exist. The local SQLite database contains 1,322 imported chunks, all marked `needs_review`. |
| Conversation history | Session-only | In-memory browser history supports open/continue/delete/clear; up to six messages may be sent as context. No durable storage or authentication. |
| Document upload, extraction, PII review, consent, analysis, cleanup | Implemented in code; AI analysis depends on configured services | Existing preview/redaction/date confirmation/consent/clear behavior remains. Analysis requires real source retrieval where available and an operational AI provider; the prior recorded OpenAI result was quota exhaustion. |
| Privacy Center | Implemented | Describes actual redaction, external AI, temporary-preview, and retention limitations. |
| Settings | Implemented | Language/theme preferences are local to the browser. |
| OCR, reminders, live legal updates, account management | Not implemented | Scanned PDFs have no OCR; there is no reminder scheduler, official update feed, or authentication. |

## Verification evidence for this review

- The local BNSS PDF, BNS PDF, and HTML table were imported as 778, 417, and
  127 chunks respectively (1,322 total). All are marked `needs_review`; they
  are not presented as verified authorities.
- MongoDB code and runtime dependencies were removed from the backend.
  `JUSTIFI_DB_PATH` configures the SQLite file; the default is
  `backend/data/justifi.db`. The existing `.env` was not overwritten. Any old
  MongoDB variables in it are ignored by runtime code.
- `python fetch_legal_sources.py` successfully imported/upserted all 1,322
  chunks from the existing files, with zero skipped or failed files.
- `python check_database.py` confirmed SQLite health and 1,322 source records.
  Real retrieval returned chunk IDs, source/title/page metadata, and the
  `needs_review` status; source-list and detail APIs returned HTTP 200.
- SQLite initialization is automatic at application startup. The health
  endpoint checks SQLite, reports AI-key configuration separately, and does
  not claim the AI provider can generate responses.
- Gemini support uses the official `google-genai` SDK and `GEMINI_API_KEY`;
  `AI_PROVIDER` selects Gemini or OpenAI, defaulting to Gemini when its key is
  set. The Gemini model defaults to `gemini-3.5-flash-lite` and can be
  overridden using `GEMINI_MODEL`. Credentials remain backend-only. Mocked tests cover answer generation,
  document analysis, auth/quota/rate-limit errors, timeout handling, and
  continued OpenAI support. A live direct request through the backend adapter
  using the configured model returned a response; it did not test legal-source
  retrieval or citation grounding. A later live query did exercise those
  backend integration steps; see the retrieval follow-up below.
- OpenAI model-list authentication succeeded in an earlier session. Live Responses API generation
  and document-analysis requests were rejected with HTTP 429
  `credit_balance_exhausted` in a previous session; AI was not rechecked for
  this migration.
- Backend tests after Gemini model configuration: `python -m pytest tests`
  (**55 passed**), including the explicit Gemini model-default assertion,
  mocked AI provider tests, and
  initialization, CRUD/upsert, persistence after
  reconnect, rollback, parameterized search, retrieval metadata, API health,
  and importer operations against temporary database files.
- Frontend checks after service-status updates: `npm run lint` and
  `npm run build` (both passed).
- No mocked response is presented as proof of legal correctness. The live
  Gemini query validates backend integration and ID mapping, not claim-by-claim
  legal correctness. OpenAI generation remains unverified in this review.

## Retrieval and citation regression follow-up

- Updated the ingestion parser using extracted document text and the section
  headings present in the documents. It now distinguishes operative BNS/BNSS
  text, statutory indexes, and the BNS/IPC comparison tables. BNSS contents
  mentioning older section numbers remain indexes rather than being
  misclassified as comparison material.
- Created and verified a local SQLite backup before re-import. The importer
  upserted 1,322 existing content-addressed records with zero skipped or failed
  files; no records were deleted. Counts remain 1,322 unique IDs and zero
  records marked `verified`.
- Post-import corpus classification: BNSS 751 statute + 27 index chunks; BNS
  346 statute + 33 index + 38 comparison chunks; HTML comparison table 127
  comparison chunks. The BNS PDF contains sections 100–101 on pages 121–125
  and punishment sections 103/105 on pages 125–126. Metadata dates remain
  unset where not reliably supported, and records retain `needs_review`.
- Actual stored-corpus retrieval checks: definitions question retrieved BNS
  §§100/101; punishment query included BNS §§103/105; explicit BNSS §103
  returned only BNSS statutory records; missing BNS §999 returned no chunks.
  Returned results include real source IDs, source filenames, pages, Act and
  section metadata. Chunk boundaries can include adjacent statutory headings.
- Live backend integration: `GET /api/health` returned HTTP 200 with SQLite
  available; `POST /api/legal/query` used actual SQLite sources and live
  `gemini-3.5-flash-lite`, returned HTTP 200 and eight citations. Each
  citation ID and metadata matched its retrieved chunk, and inline answer
  source IDs were among the response citations. This does not prove legal
  accuracy, source provenance/currentness, or frontend/browser behavior.
- `python -m pytest -q`: **65 passed**. Earlier frontend lint and production
  build passed; frontend code was not changed in this follow-up.
- The India Code validation URL remains unverified: the earlier fetch attempt
  returned HTTP 403 / an invalid-URL response. No local record was marked
  verified based on that unsuccessful check.
