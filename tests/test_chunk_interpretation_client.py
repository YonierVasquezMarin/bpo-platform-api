import json
from decimal import Decimal

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


def test_interpretation_client_requires_configuration() -> None:
    client = AzureChunkInterpretationClient(
        endpoint="",
        api_key="",
        api_version="2024-10-21",
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
        api_version="2024-10-21",
        deployment="gpt-conocimiento",
        prompt_version="v1",
    )
