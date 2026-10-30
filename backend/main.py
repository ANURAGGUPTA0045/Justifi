import logging
import os
import sqlite3
import time
from contextlib import asynccontextmanager
from collections import defaultdict, deque
from datetime import date, datetime
from pathlib import PurePath
from typing import Literal
from urllib.parse import urlparse
from uuid import UUID, uuid4

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.concurrency import run_in_threadpool

try:
    from . import ai_services, database, retrieval
    from .document_processing import (
        MAX_DOCUMENT_BYTES,
        DocumentExtractionError,
        extract_document,
        extract_explicit_dates,
    )
    from .privacy import redact_personal_information, redact_with_count
except ImportError:
    import ai_services
    import database
    import retrieval
    from document_processing import (
        MAX_DOCUMENT_BYTES,
        DocumentExtractionError,
        extract_document,
        extract_explicit_dates,
    )
    from privacy import redact_personal_information, redact_with_count


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))
logger = logging.getLogger("justifi.api")

MAX_REQUEST_BYTES = 32_768
MAX_UPLOAD_REQUEST_BYTES = MAX_DOCUMENT_BYTES + 64 * 1024
MAX_PENDING_DOCUMENTS = 5
PENDING_DOCUMENT_TTL_SECONDS = int(
    os.getenv("JUSTIFI_PENDING_DOCUMENT_TTL_SECONDS", "900")
)
if not 60 <= PENDING_DOCUMENT_TTL_SECONDS <= 3600:
    raise ValueError(
        "JUSTIFI_PENDING_DOCUMENT_TTL_SECONDS must be between 60 and 3600."
    )
RATE_LIMIT_REQUESTS = 20
RATE_LIMIT_WINDOW_SECONDS = 60
_request_times: dict[str, deque[float]] = defaultdict(deque)
_last_rate_limit_cleanup = 0.0
_pending_documents: dict[str, dict] = {}

Language = Literal["English", "Hindi", "Marathi"]


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=3000)


class LegalQueryRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    question: str = Field(min_length=1, max_length=4000)
    language: Language = "English"
    jurisdiction: str | None = Field(default=None, max_length=120)
    legal_timeframe: str | None = Field(default=None, max_length=120)
    conversation_context: list[ConversationMessage] = Field(
        default_factory=list,
        max_length=6,
    )

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Question must not be blank.")
        return value


class Citation(BaseModel):
    source_id: str
    title: str
    source: str
    page: int | None = None
    section: str | None = None
    source_url: str | None = None
    source_type: str | None = None
    jurisdiction: str | None = None
    act_name: str | None = None
    publication_date: str | None = None
    effective_date: str | None = None
    amendment_information: str | None = None
    verification_status: str


class LegalQueryResponse(BaseModel):
    answer: str
    language: Language
    retrieval_status: Literal["sources_found", "no_sources"]
    citations: list[Citation]
    limitations: list[str]


class DateReview(BaseModel):
    source_text: str = Field(min_length=1, max_length=80)
    date: str = Field(min_length=1, max_length=40)
    confirmed: bool
    page: int | None = Field(default=None, ge=1)


class DocumentAnalysisRequest(BaseModel):
    document_id: str = Field(min_length=36, max_length=36)
    language: Language = "English"
    confirm_external_ai: bool
    date_reviews: list[DateReview] = Field(default_factory=list, max_length=100)


class LegalSourceListResponse(BaseModel):
    items: list[dict]
    total: int
    limit: int
    offset: int


@asynccontextmanager
async def lifespan(_: FastAPI):
    database.initialize_database()
    yield


app = FastAPI(
    title="JustiFi Legal Information API",
    version="1.0.0",
    description=(
        "Source-grounded legal information explanations. "
        "This API does not provide legal advice."
    ),
    lifespan=lifespan,
)

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class RequestSizeLimitMiddleware:
    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        content_length = headers.get(b"content-length")
        content_type = headers.get(b"content-type", b"").lower()
        max_bytes = (
            MAX_UPLOAD_REQUEST_BYTES
            if content_type.startswith(b"multipart/form-data")
            else self.max_bytes
        )
        if content_length:
            try:
                declared_size = int(content_length)
            except ValueError:
                await JSONResponse(
                    status_code=400,
                    content={
                        "detail": {
                            "code": "INVALID_CONTENT_LENGTH",
                            "message": "Invalid request size.",
                        }
                    },
                )(scope, receive, send)
                return
            if declared_size > max_bytes:
                await JSONResponse(
                    status_code=413,
                    content={
                        "detail": {
                            "code": "REQUEST_TOO_LARGE",
                            "message": "Request exceeds the allowed size.",
                        }
                    },
                )(scope, receive, send)
                return

        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            if message["type"] == "http.request":
                body.extend(message.get("body", b""))
                if len(body) > max_bytes:
                    await JSONResponse(
                        status_code=413,
                        content={
                            "detail": {
                                "code": "REQUEST_TOO_LARGE",
                                "message": "Request exceeds the allowed size.",
                            }
                        },
                    )(scope, receive, send)
                    return
                if not message.get("more_body", False):
                    break

        body_sent = False

        async def replay_body():
            nonlocal body_sent
            if body_sent:
                return await receive()
            body_sent = True
            return {
                "type": "http.request",
                "body": bytes(body),
                "more_body": False,
            }

        await self.app(scope, replay_body, send)


app.add_middleware(
    RequestSizeLimitMiddleware,
    max_bytes=MAX_REQUEST_BYTES,
)


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    fields = [
        ".".join(str(part) for part in error["loc"] if part != "body")
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "detail": {
                "code": "VALIDATION_ERROR",
                "message": "Please check the question and selected options.",
                "fields": fields,
            }
        },
    )


def enforce_query_rate_limit(request: Request) -> None:
    global _last_rate_limit_cleanup
    client_host = request.client.host if request.client else "unknown"
    now = time.monotonic()
    if now - _last_rate_limit_cleanup >= RATE_LIMIT_WINDOW_SECONDS:
        expired_clients = [
            host
            for host, requests in _request_times.items()
            if not requests
            or now - requests[-1] >= RATE_LIMIT_WINDOW_SECONDS
        ]
        for host in expired_clients:
            _request_times.pop(host, None)
        _last_rate_limit_cleanup = now
    requests = _request_times[client_host]
    while requests and now - requests[0] >= RATE_LIMIT_WINDOW_SECONDS:
        requests.popleft()
    if len(requests) >= RATE_LIMIT_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "RATE_LIMITED",
                "message": "Too many questions. Please try again shortly.",
            },
            headers={"Retry-After": str(RATE_LIMIT_WINDOW_SECONDS)},
        )
    requests.append(now)


def _safe_source_url(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return value


def _metadata_text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def _citations_from_sources(sources: list[dict]) -> list[Citation]:
    citations = []
    for source in sources:
        citations.append(
            Citation(
                source_id=str(source.get("id") or ""),
                title=str(source.get("title") or "Legal document"),
                source=str(source.get("source") or "Unknown source"),
                page=source.get("page"),
                section=source.get("section"),
                source_url=_safe_source_url(source.get("source_url")),
                source_type=source.get("source_type"),
                jurisdiction=source.get("jurisdiction"),
                act_name=source.get("act_name"),
                publication_date=_metadata_text(source.get("publication_date")),
                effective_date=_metadata_text(source.get("effective_date")),
                amendment_information=_metadata_text(
                    source.get("amendment_information")
                ),
                verification_status=str(
                    source.get("verification_status", "needs_review")
                ),
            )
        )
    return citations


def _no_sources_message(language: Language) -> str:
    messages = {
        "English": (
            "The available corpus does not contain a matching statutory "
            "passage. I cannot provide a source-grounded explanation for "
            "this question until the necessary legal text is available."
        ),
        "Hindi": (
            "उपलब्ध संग्रह में इस प्रश्न से मेल खाता वैधानिक पाठ नहीं मिला। "
            "आवश्यक कानूनी पाठ उपलब्ध होने तक स्रोत-आधारित जानकारी देना "
            "संभव नहीं है।"
        ),
        "Marathi": (
            "उपलब्ध संग्रहात या प्रश्नाशी जुळणारा वैधानिक मजकूर मिळाला "
            "नाही. आवश्यक कायदेशीर मजकूर उपलब्ध होईपर्यंत स्रोतांवर "
            "आधारित माहिती देता येणार नाही."
        ),
    }
    return messages[language]


@app.get("/api/health")
def health_check() -> dict:
    services = {
        "sqlite": "unavailable",
        "ai": "configured" if ai_services.client is not None else "unconfigured",
    }
    try:
        database.check_database()
        services["sqlite"] = "available"
    except (sqlite3.Error, OSError, RuntimeError, ValueError) as exc:
        logger.warning(
            "SQLite health check failed (%s).",
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=503,
            detail={
                "code": "DEPENDENCY_UNAVAILABLE",
                "message": "The local database is not ready.",
                "services": services,
                "database_diagnostic": {
                    "code": "SQLITE_UNAVAILABLE",
                    "message": (
                        "Check JUSTIFI_DB_PATH permissions and available "
                        "disk space."
                    ),
                },
                "limits": {"max_upload_bytes": MAX_DOCUMENT_BYTES},
            },
        ) from exc

    return {
        "status": "ok" if services["ai"] == "configured" else "degraded",
        "services": services,
        "limits": {"max_upload_bytes": MAX_DOCUMENT_BYTES},
    }


@app.post(
    "/api/legal/query",
    response_model=LegalQueryResponse,
    dependencies=[Depends(enforce_query_rate_limit)],
)
def query_legal_information(payload: LegalQueryRequest) -> LegalQueryResponse:
    safe_question = redact_personal_information(payload.question)
    safe_jurisdiction = (
        redact_personal_information(payload.jurisdiction)
        if payload.jurisdiction
        else None
    )
    context_parts = []
    if safe_jurisdiction:
        context_parts.append(f"Jurisdiction: {safe_jurisdiction}")
    if payload.legal_timeframe:
        context_parts.append(
            "Requested legal timeframe: "
            + redact_personal_information(payload.legal_timeframe)
        )
    legal_context = "; ".join(context_parts) or None
    safe_conversation_context = [
        {
            "role": message.role,
            "content": redact_personal_information(message.content),
        }
        for message in payload.conversation_context
    ]

    try:
        sources = retrieval.search_legal_sources(safe_question, limit=10)
    except retrieval.RetrievalUnavailable as exc:
        logger.warning("Legal-source retrieval is unavailable.")
        raise HTTPException(
            status_code=503,
            detail={
                "code": "RETRIEVAL_UNAVAILABLE",
                "message": "Legal sources are temporarily unavailable.",
            },
        ) from exc

    citations = _citations_from_sources(sources)
    limitations = [
        "This is general legal information, not legal advice.",
        "Retrieved documents are not treated as verified unless explicitly "
        "marked verified in their source metadata.",
    ]

    if not sources:
        return LegalQueryResponse(
            answer=_no_sources_message(payload.language),
            language=payload.language,
            retrieval_status="no_sources",
            citations=[],
            limitations=limitations,
        )

    safe_sources = [
        {
            key: redact_personal_information(value)
            if isinstance(value, str)
            else value
            for key, value in source.items()
        }
        for source in sources
    ]

    try:
        answer = ai_services.simplify_legal_language(
            question=safe_question,
            sources=safe_sources,
            language=payload.language,
            legal_context=legal_context,
            conversation_context=safe_conversation_context,
        )
    except ai_services.AIServiceConfigurationError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "AI_NOT_CONFIGURED",
                "message": "The explanation service is not configured.",
            },
        ) from exc
    except ai_services.AIServiceAuthenticationError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "AI_PROVIDER_AUTH_FAILED",
                "message": "The explanation provider rejected its credentials.",
            },
        ) from exc
    except ai_services.AIServiceQuotaError as exc:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "AI_QUOTA_EXHAUSTED",
                "message": "The explanation provider quota is exhausted.",
            },
        ) from exc
    except ai_services.AIServiceRateLimitError as exc:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "AI_RATE_LIMITED",
                "message": "The explanation provider is rate-limiting requests.",
            },
        ) from exc
    except ai_services.AIServiceTimeoutError as exc:
        raise HTTPException(
            status_code=504,
            detail={
                "code": "AI_TIMEOUT",
                "message": "The explanation service timed out. Please try again.",
            },
        ) from exc
    except ai_services.AIServiceError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "AI_UNAVAILABLE",
                "message": "The explanation service could not answer right now.",
            },
        ) from exc

    if any(source.get("verification_status") != "verified" for source in sources):
        limitations.append(
            "One or more retrieved sources are unverified or need review."
        )
    if payload.legal_timeframe:
        limitations.append(
            "The available source records do not establish which version of "
            "the law applies to the requested timeframe."
        )

    return LegalQueryResponse(
        answer=answer,
        language=payload.language,
        retrieval_status="sources_found",
        citations=citations,
        limitations=limitations,
    )


def _discard_expired_documents(now: float | None = None) -> None:
    current_time = now if now is not None else time.monotonic()
    expired_ids = [
        document_id
        for document_id, document in _pending_documents.items()
        if current_time - document["created_at"] >= PENDING_DOCUMENT_TTL_SECONDS
    ]
    for document_id in expired_ids:
        _pending_documents.pop(document_id, None)


def _safe_upload_name(filename: str) -> str:
    normalized = filename.replace("\\", "/").rsplit("/", 1)[-1]
    normalized = "".join(
        character for character in normalized
        if character.isprintable() and character not in "\r\n"
    )
    return normalized[:180] or "uploaded-document"


def _validate_upload_mime(extension: str, content_type: str) -> None:
    allowed_types = {
        ".pdf": {"application/pdf", "application/octet-stream"},
        ".docx": {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/octet-stream",
        },
        ".txt": {"text/plain", "application/octet-stream"},
    }
    if content_type not in allowed_types.get(extension, set()):
        raise HTTPException(
            status_code=415,
            detail={
                "code": "UNSUPPORTED_MEDIA_TYPE",
                "message": "The file type does not match the supported document format.",
            },
        )


@app.post(
    "/api/documents/preview",
    dependencies=[Depends(enforce_query_rate_limit)],
)
async def preview_document(file: UploadFile = File(...)) -> dict:
    filename = _safe_upload_name(file.filename or "")
    extension = PurePath(filename).suffix.lower()
    if extension not in {".pdf", ".docx", ".txt"}:
        await file.close()
        raise HTTPException(
            status_code=415,
            detail={
                "code": "UNSUPPORTED_DOCUMENT",
                "message": "Upload a PDF, DOCX, or UTF-8 TXT document.",
            },
        )

    try:
        _validate_upload_mime(extension, (file.content_type or "").lower())
        content = await file.read(MAX_DOCUMENT_BYTES + 1)
        if len(content) > MAX_DOCUMENT_BYTES:
            raise DocumentExtractionError(
                "The document exceeds the 8 MiB upload limit."
            )
        pages = await run_in_threadpool(extract_document, filename, content)
    except DocumentExtractionError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "DOCUMENT_EXTRACTION_FAILED", "message": str(exc)},
        ) from exc
    finally:
        await file.close()

    _discard_expired_documents()
    if len(_pending_documents) >= MAX_PENDING_DOCUMENTS:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "PENDING_DOCUMENT_LIMIT",
                "message": "Please analyze or clear a pending document first.",
            },
        )

    original_text = "\n\n".join(
        (
            f"[Page {page['page']}]\n{page['text']}"
            if page.get("page") is not None
            else page["text"]
        )
        for page in pages
    )
    redacted_pages = []
    redaction_count = 0
    for page in pages:
        redacted_text, count = redact_with_count(page["text"])
        redaction_count += count
        redacted_pages.append({**page, "text": redacted_text})
    redacted_text = "\n\n".join(
        (
            f"[Page {page['page']}]\n{page['text']}"
            if page.get("page") is not None
            else page["text"]
        )
        for page in redacted_pages
    )

    document_id = str(uuid4())
    _pending_documents[document_id] = {
        "created_at": time.monotonic(),
        "filename": filename,
        "pages": pages,
        "text": original_text,
        "redacted_text": redacted_text,
        "redaction_count": redaction_count,
        "dates": extract_explicit_dates(redacted_pages),
    }
    return {
        "document_id": document_id,
        "filename": filename,
        "pages": len(pages),
        "characters": len(original_text),
        "redaction_count": redaction_count,
        "extraction_status": "text_extracted",
        "original_preview": original_text[:12_000],
        "redacted_preview": redacted_text[:12_000],
        "dates": _pending_documents[document_id]["dates"],
        "expires_in_seconds": PENDING_DOCUMENT_TTL_SECONDS,
        "limitations": [
            "Pattern matching does not reliably find names, addresses, or all sensitive information.",
            "Scanned PDFs are not processed with OCR.",
            "The extracted text is temporary and is removed after 15 minutes or when cleared.",
        ],
    }


@app.post(
    "/api/documents/analyze",
    dependencies=[Depends(enforce_query_rate_limit)],
)
def analyze_document(payload: DocumentAnalysisRequest) -> dict:
    _discard_expired_documents()
    document = _pending_documents.get(payload.document_id)
    if not document:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "DOCUMENT_PREVIEW_EXPIRED",
                "message": "The document preview expired. Upload it again to continue.",
            },
        )
    if not payload.confirm_external_ai:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "AI_PROCESSING_NOT_CONFIRMED",
                "message": "Confirm that the redacted document text may be sent to the AI provider.",
            },
        )

    dates = document["dates"]
    review_by_key = {
        (item.source_text, item.page): item
        for item in payload.date_reviews
    }
    reviewed_dates = []
    for extracted_date in dates:
        review = review_by_key.get(
            (extracted_date["source_text"], extracted_date.get("page"))
        )
        if review is None or not review.confirmed:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "DATE_REVIEW_REQUIRED",
                    "message": "Review and confirm every detected date before analysis.",
                },
            )
        reviewed_dates.append(
            {
                **extracted_date,
                "date": review.date,
                "confirmed_by_user": True,
            }
        )

    safe_text = document["redacted_text"]
    query = safe_text[:1500].strip()
    try:
        sources = retrieval.search_legal_sources(query, limit=5) if query else []
    except retrieval.RetrievalUnavailable as exc:
        logger.warning("Document analysis source retrieval is unavailable.")
        raise HTTPException(
            status_code=503,
            detail={
                "code": "RETRIEVAL_UNAVAILABLE",
                "message": "Legal sources are unavailable; document analysis was not sent to the AI provider.",
            },
        ) from exc

    safe_sources = [
        {
            key: redact_personal_information(value)
            if isinstance(value, str)
            else value
            for key, value in source.items()
        }
        for source in sources
    ]
    try:
        analysis = ai_services.analyze_document(
            safe_text,
            safe_sources,
            payload.language,
            date_reviews=reviewed_dates,
        )
    except ai_services.AIServiceConfigurationError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "AI_NOT_CONFIGURED",
                "message": "The explanation service is not configured.",
            },
        ) from exc
    except ai_services.AIServiceAuthenticationError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "AI_PROVIDER_AUTH_FAILED",
                "message": "The explanation provider rejected its credentials.",
            },
        ) from exc
    except ai_services.AIServiceQuotaError as exc:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "AI_QUOTA_EXHAUSTED",
                "message": "The explanation provider quota is exhausted.",
            },
        ) from exc
    except ai_services.AIServiceRateLimitError as exc:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "AI_RATE_LIMITED",
                "message": "The explanation provider is rate-limiting requests.",
            },
        ) from exc
    except ai_services.AIServiceTimeoutError as exc:
        raise HTTPException(
            status_code=504,
            detail={
                "code": "AI_TIMEOUT",
                "message": "Document analysis timed out. Please try again.",
            },
        ) from exc
    except ai_services.AIServiceError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "AI_UNAVAILABLE",
                "message": "The document could not be analyzed right now.",
            },
        ) from exc

    _pending_documents.pop(payload.document_id, None)
    limitations = list(analysis["limitations"])
    limitations.append(
        "The uploaded text is user-provided evidence, not an authoritative statement of the law."
    )
    limitations.append(
        "Dates are extracted from document text only. No legal deadline is calculated."
    )
    if not sources:
        limitations.append(
            "No matching legal source was retrieved; the interpretation is based on the uploaded text alone."
        )
    if any(source.get("verification_status") != "verified" for source in sources):
        limitations.append(
            "One or more retrieved legal-source records are unverified or need review."
        )

    return {
        "filename": document["filename"],
        "language": payload.language,
        "analysis": analysis,
        "dates": reviewed_dates,
        "citations": [
            citation.model_dump()
            for citation in _citations_from_sources(sources)
        ],
        "limitations": limitations,
    }


@app.delete("/api/documents/{document_id}")
def clear_document_preview(document_id: str) -> dict:
    try:
        normalized_id = str(UUID(document_id))
    except (ValueError, TypeError, AttributeError) as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_DOCUMENT_ID",
                "message": "The document identifier is invalid.",
            },
        ) from exc
    was_present = _pending_documents.pop(normalized_id, None) is not None
    return {"deleted": was_present}


@app.get(
    "/api/legal/sources",
    response_model=LegalSourceListResponse,
)
def list_legal_sources(
    query: str = "",
    verification_status: str | None = None,
    jurisdiction: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> LegalSourceListResponse:
    if len(query) > 160:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_QUERY",
                "message": "Source search must be 160 characters or fewer.",
            },
        )
    if verification_status and verification_status not in {
        "verified",
        "needs_review",
        "unverified",
    }:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_VERIFICATION_STATUS",
                "message": "Unsupported verification-status filter.",
            },
        )
    safe_limit = max(1, min(limit, 50))
    safe_offset = max(0, min(offset, 10_000))
    try:
        items, total = retrieval.search_source_records(
            query=redact_personal_information(query.strip()),
            verification_status=verification_status,
            jurisdiction=redact_personal_information(jurisdiction.strip())
            if jurisdiction
            else None,
            limit=safe_limit,
            offset=safe_offset,
        )
    except (retrieval.RetrievalUnavailable, RuntimeError) as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "RETRIEVAL_UNAVAILABLE",
                "message": "Legal sources are temporarily unavailable.",
            },
        ) from exc
    return LegalSourceListResponse(
        items=items,
        total=total,
        limit=safe_limit,
        offset=safe_offset,
    )


@app.get("/api/legal/sources/{source_id}")
def get_legal_source(source_id: str) -> dict:
    if len(source_id) > 128:
        raise HTTPException(
            status_code=404,
            detail={"code": "SOURCE_NOT_FOUND", "message": "Source not found."},
        )
    try:
        source = retrieval.get_source_record(source_id)
    except (retrieval.RetrievalUnavailable, RuntimeError) as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "RETRIEVAL_UNAVAILABLE",
                "message": "Legal sources are temporarily unavailable.",
            },
        ) from exc
    if source is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "SOURCE_NOT_FOUND", "message": "Source not found."},
        )
    return source
