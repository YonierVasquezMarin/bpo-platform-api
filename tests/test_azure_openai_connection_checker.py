from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.dtos.connection_status import ConnectionStatus
from app.services.azure_openai_connection_checker import AzureOpenAiConnectionChecker


def test_azure_openai_checker_returns_ok_when_models_are_listed() -> None:
    checker = _checker()
    checker._client = lambda: _models_client(["gpt-4o", "text-embedding-3-small"])

    result = checker.check_connection()

    assert result.name == "azure_openai"
    assert result.status == ConnectionStatus.OK
    assert result.message == "Conexión establecida"
    assert result.latency_ms is not None
    assert result.latency_ms >= 0


def test_azure_openai_checker_returns_error_when_configuration_is_missing() -> None:
    checker = _checker(endpoint="", api_key="", chat_deployment="", embedding_deployment="")

    result = checker.check_connection()

    assert result.name == "azure_openai"
    assert result.status == ConnectionStatus.ERROR
    assert result.message == "No se pudo establecer la conexión"


def test_azure_openai_checker_returns_error_when_a_deployment_is_missing() -> None:
    checker = _checker(embedding_deployment=" ")

    result = checker.check_connection()

    assert result.status == ConnectionStatus.ERROR
    assert result.message == "No se pudo establecer la conexión"


def test_azure_openai_checker_returns_error_when_listing_models_fails() -> None:
    checker = _checker()
    checker._client = _failing_client

    result = checker.check_connection()

    assert result.status == ConnectionStatus.ERROR
    assert result.message == "No se pudo establecer la conexión"


def test_azure_openai_checker_lists_models_on_the_resource_origin() -> None:
    with patch("app.services.azure_openai_connection_checker.AzureOpenAI") as azure_openai:
        azure_openai.return_value.models.list.return_value = [SimpleNamespace(id="gpt-5.4")]
        checker = _checker(endpoint="https://bpo-platform.services.ai.azure.com/openai/v1/responses")

        result = checker.check_connection()

    assert result.status == ConnectionStatus.OK
    assert azure_openai.call_args.kwargs["azure_endpoint"] == "https://bpo-platform.services.ai.azure.com"


def test_azure_openai_checker_returns_error_when_no_models_are_returned() -> None:
    checker = _checker()
    checker._client = lambda: _models_client([])

    result = checker.check_connection()

    assert result.status == ConnectionStatus.ERROR
    assert result.message == "No se pudo establecer la conexión"


def _checker(**overrides: str) -> AzureOpenAiConnectionChecker:
    values = {
        "endpoint": "https://example.openai.azure.com",
        "api_key": "clave",
        "api_version": "2024-10-21",
        "chat_deployment": "gpt-conocimiento",
        "embedding_deployment": "text-embedding",
    }
    values.update(overrides)
    return AzureOpenAiConnectionChecker(**values)


def _models_client(model_ids: list[str]) -> MagicMock:
    client = MagicMock()
    client.models.list.return_value = [SimpleNamespace(id=model_id) for model_id in model_ids]
    return client


def _failing_client() -> MagicMock:
    raise RuntimeError("connection refused")
