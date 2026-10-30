import json

import pytest

import ai_services


class FakeGeminiResponse:
    def __init__(self, text):
        self.text = text


class FakeGeminiModels:
    def __init__(self, text):
        self.text = text
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        return FakeGeminiResponse(self.text)


class FakeGeminiClient:
    def __init__(self, text):
        self.models = FakeGeminiModels(text)


def test_configured_gemini_model_is_flash_lite():
    assert ai_services.GEMINI_MODEL == "gemini-3.5-flash-lite"


def test_gemini_legal_explanation_uses_grounded_prompt_and_config(monkeypatch):
    fake_client = FakeGeminiClient("A source-grounded explanation.")
    monkeypatch.setattr(ai_services, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(ai_services, "GEMINI_MODEL", "test-gemini-model")
    monkeypatch.setattr(ai_services, "client", fake_client)

    answer = ai_services.simplify_legal_language(
        "What does this provision mean?",
        [
            {
                "id": "source-1",
                "title": "Bharatiya Nyaya Sanhita, 2023",
                "content": "The provided legal passage.",
                "act_name": "Bharatiya Nyaya Sanhita, 2023",
                "section": "100. Culpable homicide",
                "page": 121,
                "verification_status": "needs_review",
            }
        ],
    )

    request = fake_client.models.calls[0]
    assert answer == "A source-grounded explanation."
    assert request["model"] == "test-gemini-model"
    assert "The provided legal passage." in request["contents"]
    assert "Source ID: source-1" in request["contents"]
    assert "Section: 100. Culpable homicide" in request["contents"]
    assert 'needs_review" as not yet independently verified' in request["contents"]
    assert "Do not use BNSS procedural provisions" in request["config"].system_instruction
    assert "Do not invent section numbers" in request["contents"]
    assert request["config"].system_instruction == ai_services.SYSTEM_PROMPT
    assert request["config"].max_output_tokens == 900


def test_gemini_document_analysis_parses_json(monkeypatch):
    analysis = {
        "overview": "Summary",
        "important_clauses": [],
        "legal_terms": [],
        "obligations": [],
        "rights_or_remedies": [],
        "questions_to_clarify": [],
        "limitations": ["Not legal advice."],
    }
    fake_client = FakeGeminiClient(json.dumps(analysis))
    monkeypatch.setattr(ai_services, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(ai_services, "client", fake_client)

    result = ai_services.analyze_document("A redacted agreement.", [])

    assert result == analysis
    request = fake_client.models.calls[0]
    assert request["config"].response_mime_type == "application/json"
    assert "A redacted agreement." in request["contents"]
    assert request["config"].max_output_tokens == 1400


@pytest.mark.parametrize(
    ("code", "message", "error_type"),
    [
        (401, "API key not valid", ai_services.AIServiceAuthenticationError),
        (403, "permission denied", ai_services.AIServiceAuthenticationError),
        (429, "quota exhausted", ai_services.AIServiceQuotaError),
        (429, "request rate limited", ai_services.AIServiceRateLimitError),
    ],
)
def test_gemini_provider_errors_are_sanitized(
    monkeypatch, code, message, error_type
):
    class FakeGeminiAPIError(Exception):
        def __init__(self):
            super().__init__(message)
            self.code = code

    class FailingModels:
        def generate_content(self, **kwargs):
            raise FakeGeminiAPIError()

    class FailingClient:
        models = FailingModels()

    monkeypatch.setattr(ai_services, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(ai_services, "GeminiAPIError", FakeGeminiAPIError)
    monkeypatch.setattr(ai_services, "client", FailingClient())

    with pytest.raises(error_type) as caught:
        ai_services._generate_text(
            system_instruction="system",
            prompt="prompt",
            max_output_tokens=10,
        )

    assert message not in str(caught.value)
    assert "internal transport" not in str(caught.value)


def test_gemini_timeout_is_reported_as_timeout(monkeypatch):
    class FakeTimeout(Exception):
        pass

    class FailingModels:
        def generate_content(self, **kwargs):
            raise FakeTimeout("internal transport details")

    class FailingClient:
        models = FailingModels()

    monkeypatch.setattr(ai_services, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(ai_services, "TimeoutException", FakeTimeout)
    monkeypatch.setattr(ai_services, "client", FailingClient())

    with pytest.raises(ai_services.AIServiceTimeoutError) as caught:
        ai_services._generate_text(
            system_instruction="system",
            prompt="prompt",
            max_output_tokens=10,
        )

    assert "internal transport details" not in str(caught.value)


def test_openai_remains_supported(monkeypatch):
    class FakeResponse:
        output_text = "OpenAI response"

    class FakeResponses:
        def __init__(self):
            self.request = None

        def create(self, **kwargs):
            self.request = kwargs
            return FakeResponse()

    class FakeOpenAIClient:
        def __init__(self):
            self.responses = FakeResponses()

    fake_client = FakeOpenAIClient()
    monkeypatch.setattr(ai_services, "AI_PROVIDER", "openai")
    monkeypatch.setattr(ai_services, "OPENAI_MODEL", "test-openai-model")
    monkeypatch.setattr(ai_services, "client", fake_client)

    result = ai_services._generate_text(
        system_instruction="Instructions",
        prompt="Prompt",
        max_output_tokens=20,
    )

    assert result == "OpenAI response"
    assert fake_client.responses.request == {
        "model": "test-openai-model",
        "instructions": "Instructions",
        "input": "Prompt",
        "max_output_tokens": 20,
    }


def test_invalid_provider_is_not_silently_routed_to_openai(monkeypatch):
    monkeypatch.setattr(ai_services, "AI_PROVIDER", "unknown")
    monkeypatch.setattr(ai_services, "client", None)

    with pytest.raises(ai_services.AIServiceConfigurationError) as caught:
        ai_services._generate_text(
            system_instruction="system",
            prompt="prompt",
            max_output_tokens=10,
        )

    assert "AI_PROVIDER" in str(caught.value)
