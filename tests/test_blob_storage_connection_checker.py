from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import BlobStorageNotConfiguredError
from app.dtos.connection_status import ConnectionStatus
from app.services.blob_storage_client import AzureBlobStorageClient
from app.services.blob_storage_connection_checker import BlobStorageConnectionChecker


def test_blob_storage_checker_returns_ok_when_container_is_available() -> None:
    blob_storage = MagicMock()
    checker = BlobStorageConnectionChecker(blob_storage)

    result = checker.check_connection()

    assert result.name == "blob_storage"
    assert result.status == ConnectionStatus.OK
    assert result.message == "Conexión establecida"
    assert result.latency_ms is not None
    assert result.latency_ms >= 0
    blob_storage.ensure_container.assert_called_once()


def test_blob_storage_checker_returns_error_when_probe_fails() -> None:
    blob_storage = MagicMock()
    blob_storage.ensure_container.side_effect = RuntimeError("network down")
    checker = BlobStorageConnectionChecker(blob_storage)

    result = checker.check_connection()

    assert result.status == ConnectionStatus.ERROR
    assert result.message == "No se pudo establecer la conexión"


def test_blob_storage_checker_returns_error_when_storage_is_not_configured() -> None:
    checker = BlobStorageConnectionChecker(AzureBlobStorageClient("", "documents"))

    result = checker.check_connection()

    assert result.status == ConnectionStatus.ERROR
    assert result.message == "No se pudo establecer la conexión"


def test_ensure_container_creates_the_container_when_it_is_missing() -> None:
    client = AzureBlobStorageClient("UseDevelopmentStorage=true", "bpo-documents")
    container = MagicMock()
    container.exists.return_value = False

    with patch("app.services.blob_storage_client.BlobServiceClient") as blob_service_client:
        blob_service_client.from_connection_string.return_value.get_container_client.return_value = container
        client.ensure_container()

    container.create_container.assert_called_once()


def test_ensure_container_keeps_an_existing_container() -> None:
    client = AzureBlobStorageClient("UseDevelopmentStorage=true", "bpo-documents")
    container = MagicMock()
    container.exists.return_value = True

    with patch("app.services.blob_storage_client.BlobServiceClient") as blob_service_client:
        blob_service_client.from_connection_string.return_value.get_container_client.return_value = container
        client.ensure_container()

    container.create_container.assert_not_called()


def test_ensure_container_requires_configuration() -> None:
    client = AzureBlobStorageClient("  ", "documents")

    with pytest.raises(BlobStorageNotConfiguredError):
        client.ensure_container()
