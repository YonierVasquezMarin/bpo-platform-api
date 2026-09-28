import json
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import DocumentIntelligenceNotConfiguredError, DocumentSearchNotConfiguredError
from app.services.chunk_interpretation_client import AzureChunkInterpretationClient
from app.services.embedding_client import AzureEmbeddingClient
from app.services.knowledge_search_client import AzureKnowledgeSearchClient


def test_interpretation_result_keeps_spanish_text_and_english_keys() -> None:
    client = _client()
    payload = {
        "interpretation": "El pago debe hacerse en cinco días.",
        "structured_content": {"summary": "Pago en cinco días", "topics": ["pagos", "plazos"]},
        "confidence": 0.91,
    }

    result = client._build_result(json.dumps(payload))

    assert result.interpretation == "El pago debe hacerse en cinco días."
    assert result.structured_content == {"summary": "Pago en cinco días", "topics": ["pagos", "plazos"]}
    assert result.confidence == Decimal("0.91")
    assert result.model_name == "gpt-conocimiento"
    assert result.prompt_version == "v1"


def test_percentage_confidence_is_normalized_between_zero_and_one() -> None:
    result = _client()._build_result(
        json.dumps(
            {
                "interpretation": "Texto suficiente.",
                "structured_content": {"summary": "Texto suficiente.", "topics": []},
                "confidence": 86,
            }
        )
    )

    assert result.confidence == Decimal("0.86")


def test_invalid_json_becomes_an_unreliable_interpretation() -> None:
    client = _client()
    client._request_completion = lambda content, section_title: "esto no es json"

    result = client.interpret_chunk("contenido", "Seccion")

    assert result.confidence == Decimal("0.00")
    assert result.structured_content["topics"] == []


def test_interpretation_client_calls_foundry_v1_chat_completions() -> None:
    client = AzureChunkInterpretationClient(
        endpoint="https://bpo-platform.services.ai.azure.com/openai/v1/responses",
        api_key="clave",
        deployment="gpt-5.4",
        prompt_version="v1",
    )
    completion = _completion(_interpretation_payload())

    with patch("app.services.chunk_interpretation_client.OpenAI") as openai:
        openai.return_value.chat.completions.create.return_value = completion
        result = client.interpret_chunk("contenido", "Seccion")

    assert openai.call_args.kwargs["base_url"] == "https://bpo-platform.services.ai.azure.com/openai/v1/"
    create_kwargs = openai.return_value.chat.completions.create.call_args.kwargs
    assert create_kwargs["model"] == "gpt-5.4"
    assert "temperature" not in create_kwargs
    assert result.model_name == "gpt-5.4"


def test_interpretation_client_requires_configuration() -> None:
    client = AzureChunkInterpretationClient(
        endpoint="",
        api_key="",
        deployment="",
        prompt_version="v1",
    )

    with pytest.raises(DocumentIntelligenceNotConfiguredError):
        client.interpret_chunk("contenido", None)


def test_embedding_client_requires_configuration() -> None:
    client = AzureEmbeddingClient(
        endpoint="",
        api_key="",
        api_version="2024-10-21",
        deployment="",
        dimensions=1536,
    )

    with pytest.raises(DocumentIntelligenceNotConfiguredError):
        client.create_embedding("contenido")


def test_search_client_requires_configuration() -> None:
    client = AzureKnowledgeSearchClient(endpoint="", api_key="", index_name="", vector_dimensions=1536)

    with pytest.raises(DocumentSearchNotConfiguredError):
        client.upsert_document(None)


def _client() -> AzureChunkInterpretationClient:
    return AzureChunkInterpretationClient(
        endpoint="https://example.openai.azure.com",
        api_key="clave",
        deployment="gpt-conocimiento",
        prompt_version="v1",
    )


def _interpretation_payload() -> dict:
    return {
        "interpretation": "El pago debe hacerse en cinco días.",
        "structured_content": {"summary": "Pago en cinco días", "topics": ["pagos"]},
        "confidence": 0.91,
    }


def _completion(payload: dict) -> MagicMock:
    message = SimpleNamespace(content=json.dumps(payload))
    choice = SimpleNamespace(message=message)
    completion = MagicMock()
    completion.choices = [choice]
    return completion
