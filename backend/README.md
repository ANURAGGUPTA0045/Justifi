# JustiFi backend

## Requirements and local storage

- Python 3.10 or newer (tested with Python 3.13).
- SQLite is included with Python; no cloud database, credentials, Docker, or
  separate database installation is required.
- An AI key is optional for the application to start. AI explanations require
  either the Google Gemini API or OpenAI key and an available provider account.

The backend creates a persistent SQLite database automatically at
`backend/data/justifi.db`. Set `JUSTIFI_DB_PATH` in `backend/.env` to choose a
different absolute path or a path relative to the backend directory. The old
MongoDB settings, if present in an existing `.env`, are ignored. The project
does not overwrite or migrate the old cloud database. SQLite application data
is kept separate from temporary document previews and uploaded-file handling.

## Install and start (Windows PowerShell)

Run these commands from the project directory:

```powershell
Set-Location 'C:\Users\DELL\Downloads\backend\backend'
python -m venv .venv-sqlite
.\.venv-sqlite\Scripts\python.exe -m pip install -r requirements-dev.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
.\.venv-sqlite\Scripts\python.exe -m uvicorn main:app --reload
```

The `.env` copy runs only if the file does not exist; it will not overwrite an
existing `.env`. To use Gemini, put `GEMINI_API_KEY=your-key` in
`backend\.env` and set `AI_PROVIDER=gemini`. The default model is
`gemini-3.5-flash-lite`; override it with `GEMINI_MODEL` if needed. To use OpenAI instead, set
`AI_PROVIDER=openai` and `OPENAI_API_KEY=your-key`. If `AI_PROVIDER` is
omitted, the backend selects Gemini when `GEMINI_API_KEY` is present and
otherwise selects OpenAI. The keys are read only by backend code; never place
them in frontend files, browser storage, API responses, logs, or Git commits.

In another PowerShell terminal, verify the local database directly:

```powershell
Set-Location 'C:\Users\DELL\Downloads\backend\backend'
.\.venv-sqlite\Scripts\python.exe check_database.py
```

Verify the running API health endpoint:

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/health'
```

Interactive API documentation is at `http://127.0.0.1:8000/docs`.

## Database behavior

SQLite tables and indexes are created idempotently at application startup.
Connections are short-lived, use parameterized SQL, transactions, rollback on
failure, and deterministic cleanup. Legal source records persist in the
`legal_sources` table. Basic `users`, `chats`, and `feedback` tables are
initialized for the existing project structure; no account or conversation
API has been added. Database errors are reported without exposing filesystem
paths or raw exception messages.

`GET /api/health` performs a real SQLite query and reports `sqlite: available`
only when that check succeeds. It reports whether an AI key is configured,
not whether the provider is reachable or has quota. If SQLite is ready but AI
is not configured, health returns HTTP 200 with `status: degraded`; AI
endpoints return their existing clear service errors when called.

Initialize and inspect the database without importing documents:

```powershell
.\.venv-sqlite\Scripts\python.exe check_database.py
```

## Import local legal source files

The importer is explicit; application startup never imports documents. From
the backend directory:

```powershell
.\.venv-sqlite\Scripts\python.exe fetch_legal_sources.py
```

It reads PDF, TXT, and HTML files under `legal_documents/`, extracts text, and
upserts content-addressed chunks into SQLite. Existing chunks are updated by
stable ID; unrelated records are not deleted. Imported passages are marked
`needs_review`, not legally verified. Scanned PDFs have no OCR. HTML scripts,
styles, head content, navigation, and footer are excluded. The importer does
not download any files.

The retrieval implementation performs parameterized local text matching and
returns stored source IDs, title, source file, page, and verification metadata.
No demo legal records are inserted automatically. Empty storage produces an
explicit no-sources response; it does not fabricate statutes, citations, or AI
answers.

## API compatibility and behavior

The existing endpoint paths and legal query, document preview/analysis/clear,
source list, and source detail response shapes are retained. The health
response now reports the local `sqlite` service rather than MongoDB. Source
list filters and pagination remain available. Retrieval failures return
explicit service errors rather than appearing as empty search results.

The query endpoint calls the configured Gemini or OpenAI service only when
real source passages are retrieved. If no sources match, it returns the
existing localized no-source response without calling AI. AI configuration,
credential rejection, quota exhaustion, rate limiting, timeouts, and provider
errors are handled explicitly; health reports key configuration only and does
not claim that provider generation works.

Document preview accepts PDF, DOCX, and UTF-8 TXT in memory; analysis requires
explicit consent, redacts supported PII, and requires review of detected
dates. Uploaded content is not persistently stored. There is no OCR or
statutory deadline calculation.

Questions and chat history are not persisted by the API. Pattern-based
redaction covers common email addresses, Indian mobile numbers, PAN-like
identifiers, and 12-digit ID-number patterns, but may miss names, addresses,
and other PII. Review redacted content before consenting to external AI
processing.

English, Hindi, and Marathi answer selection is supported by the configured
LLM. The UI is not fully translated and multilingual retrieval quality has not
been measured. This application provides general legal information, not legal
advice; verify important matters with an authoritative source or qualified
legal professional.

## Tests

From `backend/`:

```powershell
.\.venv-sqlite\Scripts\python.exe -m pytest tests
```

Tests use temporary SQLite files and do not modify the persistent application
database. They verify initialization, persistence, transaction rollback,
source CRUD/upsert and retrieval, API behavior, ingestion, privacy, document
processing, and mocked AI provider request/error handling. They do not prove
that the external AI provider is available or that legal answers are accurate.
