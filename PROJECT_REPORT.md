# JustiFi Project Report

**Report date:** 30 October 2026  
**Project folder:** `backend/` (containing the `backend` and `frontend` directories)  
**Review scope:** First-party source, configuration, and document files. Dependency folders (`backend/.venv` and `frontend/node_modules`) were excluded. The values in `backend/.env` were not copied into this report.

## 1. Executive summary

This folder contains an early-stage Indian legal-information assistant named **JustiFi**. It has a FastAPI query API and a React interface connected to it. Backend persistence and source retrieval now use a persistent local SQLite database; local legal references can be extracted into searchable chunks. Gemini and OpenAI are optional external AI services.

The project is **not fully functional end to end and is not a legal-advice system**. SQLite initialization, CRUD, ingestion, retrieval, and automated tests pass. The existing local legal files are stored as 1,322 chunks, all marked `needs_review` and not independently verified. The latest backend API test used the actual SQLite corpus and live Gemini: `GET /api/health` and `POST /api/legal/query` returned HTTP 200, and returned citation IDs/metadata mapped to retrieved BNS chunks. This verifies the backend query path, not the browser UI path, legal accuracy, or authoritative provenance. The most recent recorded OpenAI generation attempt returned HTTP 429 `credit_balance_exhausted`.

## 2. Folder structure

```text
backend/
├── .gitignore
├── PROJECT_REPORT.md
├── JustiFi An Intelligent Web-Based Legal Companion for
│   Simplifying Indian Laws and Legal Procedures.pdf
├── backend/
│   ├── .env                              # Local settings/secrets; values omitted
│   ├── .env.example                      # Safe setup template
│   ├── README.md                         # Backend setup and API
│   ├── main.py                           # FastAPI query/document/source APIs
│   ├── ai_services.py                    # Source-grounded Gemini/OpenAI explanations
│   ├── database.py                       # SQLite persistence and schema
│   ├── check_database.py                 # Safe local database health check
│   ├── fetch_legal_sources.py             # Local PDF/TXT/HTML importer
│   ├── privacy.py                        # Pattern-based identifier redaction
│   ├── document_processing.py             # PDF/DOCX/TXT extraction and dates
│   ├── requirements.txt                  # Runtime Python dependencies
│   ├── requirements-dev.txt              # Runtime and test dependencies
│   ├── retrieval.py                      # SQLite text retrieval
│   ├── secure_storage.py                 # Unwired temporary-file cleanup
│   └── legal_documents/
│       ├── BNS2023.pdf
│       ├── Bharatiya_Nagarik_Suraksha_Sanhita,_2023.pdf
│       └── ncrb_bns_ipc_section_table.html
│   ├── evaluation/
│   │   └── legal_queries.json             # Evaluation cases and checks
│   └── tests/                            # API, privacy, and ingestion tests
└── frontend/
    ├── README.md
    ├── package.json
    ├── package-lock.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── App.jsx
        ├── App.css
        ├── index.css
        └── main.jsx
```

## 3. Component overview

### Backend

| File | Responsibility | Current observations |
|---|---|---|
| [`backend/database.py`](./backend/database.py) | Loads the backend `.env` settings, creates a persistent SQLite database, and initializes `users`, `chats`, `feedback`, and `legal_sources` tables with indexes. | Default file is `backend/data/justifi.db`; `JUSTIFI_DB_PATH` can configure another location. Connections are short-lived and transactional. |
| [`backend/fetch_legal_sources.py`](./backend/fetch_legal_sources.py) | Reads local PDF/TXT/HTML files, extracts text, splits it into overlapping chunks, and upserts records into SQLite. | Marks imported passages `needs_review`; scanned PDFs without extractable text are skipped (OCR is not implemented). Import is explicit, not performed during application startup. |
| [`backend/retrieval.py`](./backend/retrieval.py) | Searches the local `legal_sources` table and returns ranked passages plus source metadata. | Parameterized lexical matching, source filters, pagination, and detail lookup. Search remains lexical; multilingual retrieval quality is not verified. |
| [`backend/ai_services.py`](./backend/ai_services.py) | Sends redacted questions and retrieved passages to the selected Gemini or OpenAI model for a plain-language explanation in English, Hindi, or Marathi. Also handles document analysis. | Uses the official Google Gen AI SDK or existing OpenAI SDK; provider requests have timeouts and sanitized errors. The prompt discourages unsupported claims and treats passages as untrusted reference material. Select using `AI_PROVIDER`; Gemini reads `GEMINI_API_KEY`, OpenAI reads `OPENAI_API_KEY`. |
| [`backend/privacy.py`](./backend/privacy.py) | Redacts common emails, Indian mobile numbers, PAN-like strings, and 12-digit ID-number patterns. | Integrated before retrieval and before external AI processing, including retrieved passage text. Names and addresses are not detected reliably. |
| [`backend/secure_storage.py`](./backend/secure_storage.py) | Deletes temporary consultation files for a UUID-validated session ID. | The function is defined, but no integration/call site was found. |
| [`backend/main.py`](./backend/main.py) | FastAPI health, legal-query, source search/detail, document preview/analysis/clear endpoints; validation, CORS, request limits, in-process rate limiting, PII handling, source citation mapping, and explicit dependency errors. | Does not persist query history. Document previews and rate limits are process-local. |
| [`backend/document_processing.py`](./backend/document_processing.py) | Validates and extracts PDF, DOCX, UTF-8 TXT, and identifies supported explicit dates. | Scanned PDF OCR is not configured; date parsing is deliberately conservative and asks the user to review. |
| [`backend/requirements.txt`](./backend/requirements.txt) | Lists FastAPI, Uvicorn, Google Gen AI SDK, OpenAI, PDF, and related libraries. | No MongoDB driver or cloud database dependency remains; SQLite comes with Python. Versions remain unpinned; tests use [`backend/requirements-dev.txt`](./backend/requirements-dev.txt). |

### Frontend

[`frontend/src/App.jsx`](./frontend/src/App.jsx) provides dashboard navigation, the AI Legal Assistant with in-memory session history, Document Explainer and consent flow, source explorer/details, Privacy Center, and local Settings. It calls the backend API; the Vite development server proxies `/api` requests to the local backend. Conversation history disappears when the app is reloaded and is visible to anyone sharing an unlocked browser.

### Legal source files

The `backend/legal_documents/` folder contains two PDF references and one HTML IPC/BNS section table. The importer extracts PDF, TXT, and HTML sources; HTML scripts, styles, head content, navigation, and footer are excluded. These local files were imported into SQLite as 1,322 records. Every imported record is marked `needs_review`; this does not establish that the documents are current, complete, or legally verified.

## 4. Configuration and expected setup

The backend reads these variable names from `backend/.env`:

- `JUSTIFI_DB_PATH` — optional persistent SQLite file path; defaults to `backend/data/justifi.db`.
- `AI_PROVIDER` — optional provider selection (`gemini` or `openai`). If omitted, Gemini is selected when `GEMINI_API_KEY` is configured; otherwise OpenAI is selected.
- `GEMINI_API_KEY` — optional secret for backend-only Gemini API access.
- `GEMINI_MODEL` — optional Gemini model; defaults to `gemini-3.5-flash-lite`.
- `OPENAI_API_KEY` — optional secret for the existing OpenAI integration.
- `OPENAI_MODEL` — optional; defaults to `gpt-4.1-mini`.
- `JUSTIFI_MAX_UPLOAD_BYTES` — optional document upload limit; default 8 MiB.
- `JUSTIFI_PENDING_DOCUMENT_TTL_SECONDS` — optional in-memory preview retention; default 900 seconds.

Keep the local environment file private and out of source control. Existing MongoDB settings, if present in an existing `.env`, are no longer read by the application. No secret values were copied into this report.

The local workflow is documented in [`backend/README.md`](./backend/README.md):

1. Install Python dependencies from `backend/requirements-dev.txt` in the intended Python environment.
2. Set `JUSTIFI_DB_PATH` if the default local database location is not desired. For Gemini, set `AI_PROVIDER=gemini` and `GEMINI_API_KEY` in `backend/.env`; OpenAI remains available with `AI_PROVIDER=openai` and `OPENAI_API_KEY`.
3. The application creates the SQLite tables and indexes on startup.
4. Import supported local documents only when desired by running `python fetch_legal_sources.py` from the `backend/` directory.
5. Start the backend with `python -m uvicorn main:app --reload` from `backend/`.
6. Start the frontend from `frontend/` using `npm run dev`.

The supplied BNSS PDF, BNS PDF, and NCRB IPC/BNS HTML table were extracted into 778, 417, and 127 chunks respectively. The importer successfully upserted **1,322** records into the persistent SQLite file, with zero skipped or failed files. A SQLite backup was created and verified immediately before the metadata re-import; the import upserted existing content-addressed IDs and did not delete records.

The application no longer reads MongoDB URI/authentication configuration and has no runtime MongoDB client. The previous Atlas connection/authentication failures are no longer blockers for backend startup. `GET /api/health` performs an actual SQLite query and reports SQLite availability separately from whether a key for the selected AI provider is configured. A live backend query using the re-imported local corpus and configured `gemini-3.5-flash-lite` returned HTTP 200. Its eight BNS citations each mapped to retrieved source IDs and matching title, source, page, section, Act, source type, and `needs_review` status; the answer's inline source IDs were among those citations. This confirms backend retrieval-to-Gemini-to-citation wiring, not browser UI behavior or legal correctness. The last recorded OpenAI generation failure was HTTP 429 `credit_balance_exhausted` (`insufficient_quota`).

## 5. Main gaps and recommended order

1. **Maintain local legal sources.** The current local files are imported as 1,322 `needs_review` chunks. Their Act/source-type and section metadata were refreshed from extracted contents; this does not verify provenance or currentness. Review those before treating the corpus as authoritative.
2. **Validate legal AI behavior.** A live backend legal-query request now exercised SQLite retrieval, Gemini generation, and citation mapping. This is an integration check, not legal review or proof that every answer claim is correct. The last recorded OpenAI generation failed with exhausted quota.
3. **Improve language retrieval.** Evaluate Hindi and Marathi queries against SQLite lexical matching; add a translation/query-normalization component only if measured results justify it.
4. **Add source and legal-time metadata.** Populate official URLs, section identifiers, jurisdiction, commencement/effective dates, amendment data, and independent verification states from authoritative sources. The API exposes fields only when records contain them.
5. **Evaluate citations.** A sample live answer's inline IDs and structured metadata matched the returned retrieved chunks. There is still no automated claim-by-claim verifier to prove that every legal statement is supported by its cited passage.
6. **Expand privacy protection.** Current redaction covers common emails, Indian mobile numbers, PAN-like strings, and 12-digit IDs. Names and addresses are not reliably detected; avoid entering unnecessary personal details.
7. **Improve document analysis.** PDF/DOCX/TXT extraction, PII preview, consent gating, user-confirmed date review, and cleanup are implemented and covered by tests. OCR and statutory deadline calculation are not available.
8. **Harden deployment and validate legal content.** Add tested dependency version constraints and shared gateway-level request limits for public deployments. Qualified reviewers should check source currency/amendments and user-facing explanations; `needs_review` is not legal verification.

## 6. Implemented behavior and check results

- `GET /api/health` initializes/checks the local SQLite database and reports `sqlite: available` only after a real query succeeds. It separately reports AI-key configuration, which does not guarantee provider availability. SQLite failures return a sanitized HTTP 503 response.
- `POST /api/legal/query` accepts English, Hindi, or Marathi answer selection, optional jurisdiction and timeframe, redacts common identifiers, retrieves real indexed text, and sends retrieved passages to the existing LLM only when evidence is returned. A live backend query against the local corpus returned HTTP 200 and BNS citations linked to retrieved source records; the UI/browser route was not exercised in that test.
- Retrieval outages and AI failures return explicit non-success HTTP responses; no-source answers are localized and do not call the LLM.
- The frontend renders returned answer/source/limitation data, loading and error states, and a privacy notice.
- Document preview/analyze/clear endpoints validate PDF/DOCX/TXT uploads, return original/redacted review text, require confirmation of every detected date, include PII-redacted reviewed dates in the AI context, require consent before AI processing, and clear the preview after successful analysis. Uploads remain temporary and previews are process-local.
- Source explorer endpoints support database-backed search, filters, pagination, and source details.
- Dashboard, assistant, document, explore, sources, privacy, and settings views are connected. The service panel now reports SQLite status. Language/theme preferences are local; conversation history is memory-only.
- Source URLs are rendered only for HTTP(S) URLs already present in retrieved record metadata. No live government-source check is performed.
- The complete backend suite after the retrieval changes: `python -m pytest -q` (**65 passed**). It includes SQLite initialization/CRUD/persistence, ingestion classification, statutory routing, BNSS/BNS separation, API health/citations, and mocked AI error handling. Frontend ESLint and production build passed in the previous frontend validation; frontend files were not changed in this retrieval update.
- Gemini model configuration: `GEMINI_MODEL` defaults to `gemini-3.5-flash-lite`, and the backend `.env` selects that model. The official Gemini model list includes this model ID. A live direct generation request through `ai_services._generate_text` succeeded and returned a response; this was not a legal query with retrieved citations.
- Backend tests after the model setting change: `python -m pytest tests -q` (**55 passed**), including the explicit model-default assertion and mocked provider success/error coverage.
- After re-import, the local corpus contains 1,322 unique IDs and zero duplicate IDs: BNSS has 751 statute and 27 index chunks; BNS has 346 statute, 33 index, and 38 comparison chunks; the HTML comparison table has 127 comparison chunks. No row was marked `verified`.
- Real-corpus retrieval checks returned BNS §§100/101 for the murder-versus-culpable-homicide definitions query; BNS §§103/105 appeared for a punishment query; an explicit BNSS §103 query returned only BNSS statute records; and a missing BNS §999 query returned no passages. Returned chunks retained source filename, page, Act, section, source type, and `needs_review` metadata. Some retrieved chunks span adjacent section text and therefore expose multiple adjacent section headings in metadata.
- A live `TestClient` check reported `GET /api/health` HTTP 200 with SQLite available and AI configured, and the legal query returned HTTP 200 with eight citations. Each citation ID and metadata matched a retrieved chunk; inline IDs in the answer were among the returned citation IDs. The query did not establish official-source provenance, statutory currentness, or legal correctness. The supplied India Code PDF could not be fetched in the earlier check (HTTP 403 / invalid URL response).
- OpenAI generation/document analysis and browser-based frontend-to-citation behavior remain unverified in this update; the prior recorded OpenAI provider error was HTTP 429 `credit_balance_exhausted`.
- Localization dictionaries contain all shared keys for English, Hindi, and Marathi. Some static UI captions/status text remains English, and live Hindi/Marathi AI answers could not be tested because the provider quota is exhausted; do not describe the app as fully translated.

## 7. Review limitations

This report is based on reading first-party files, checking the presentation, running automated checks, and smoke-testing the local app. The `.venv` and `node_modules` contents were excluded from the source-code review.
