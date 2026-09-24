from datetime import datetime, timezone
from hashlib import sha256
from unittest.mock import MagicMock

import pytest

from app.core.exceptions import (
    DocumentMetadataError,
    DocumentTooLargeError,
    EmptyDocumentError,
    UnsupportedDocumentTypeError,
)
from app.models.document_version import DocumentVersionStatus
from app.services.document_upload_service import DocumentUploadCommand, DocumentUploadService
from tests.document_fakes import InMemoryBlobStorage
from tests.in_memory_document_repository import InMemoryDocumentRepository


def test_upload_stores_blob_document_and_version() -> None:
    repository = InMemoryDocumentRepository()
    blob_storage = InMemoryBlobStorage()
    service = _service(repository, blob_storage)
    content = "El pago se realiza en cinco dias.".encode("utf-8")

    created = service.upload_document(
        DocumentUploadCommand(
            file_name="política de pagos.txt",
            file_content=content,
            uploaded_by_user_id=7,
            name="Politica de pagos",
            document_type=None,
            description="Manual operativo",
            category="Pagos",
            source_system="BPO",
        )
    )

    version = repository.find_version(created.document_id, created.version_id)
    assert created.status == DocumentVersionStatus.UPLOADED.value
    assert created.version_number == 1
    assert created.file_name == "pol_tica_de_pagos.txt"
    assert version is not None
    assert version.checksum == sha256(content).hexdigest()
    assert version.uploaded_by_user_id == 7
    assert version.blob_path in blob_storage.files
    assert repository.find_document(created.document_id).name == "Politica de pagos"
    assert repository.find_document(created.document_id).document_type == "TXT"
    assert repository.find_document(created.document_id).current_version_id == version.id
    assert repository.audits[0].event_type == "DOCUMENT_UPLOADED"


def test_upload_rejects_empty_unsupported_and_large_files() -> None:
    service = _service(InMemoryDocumentRepository(), InMemoryBlobStorage(), max_size_bytes=10)

    with pytest.raises(EmptyDocumentError):
        service.upload_document(_command(b"", "vacio.txt"))
    with pytest.raises(UnsupportedDocumentTypeError):
        service.upload_document(_command(b"abc", "archivo.exe"))
    with pytest.raises(DocumentTooLargeError):
        service.upload_document(_command(b"a" * 11, "grande.txt"))


def test_upload_rejects_a_document_type_that_does_not_fit_the_column() -> None:
    service = _service(InMemoryDocumentRepository(), InMemoryBlobStorage(), max_size_bytes=100)

    with pytest.raises(DocumentMetadataError):
        service.upload_document(_command(b"abc", "nota.txt", document_type="T" * 51))


def test_upload_deletes_the_blob_when_persistence_fails() -> None:
    repository = MagicMock()
    repository.add_document.side_effect = lambda document: _assign(document, 1)
    repository.add_version.side_effect = lambda version: _assign(version, 2)
    repository.commit.side_effect = RuntimeError("db")
    blob_storage = InMemoryBlobStorage()
    service = _service(repository, blob_storage, max_size_bytes=100)

    with pytest.raises(RuntimeError):
        service.upload_document(_command(b"abc", "nota.txt"))

    assert blob_storage.files == {}
    assert blob_storage.deleted


def _service(repository, blob_storage, max_size_bytes: int = 1_000_000) -> DocumentUploadService:
    return DocumentUploadService(
        document_repository=repository,
        blob_storage=blob_storage,
        container_name="documents",
        max_size_bytes=max_size_bytes,
    )


def _command(content: bytes, file_name: str, document_type: str | None = None) -> DocumentUploadCommand:
    return DocumentUploadCommand(
        file_name=file_name,
        file_content=content,
        uploaded_by_user_id=1,
        name=None,
        document_type=document_type,
        description=None,
        category=None,
        source_system=None,
    )


def _assign(entity, identifier: int):
    entity.id = identifier
    entity.uploaded_at = datetime.now(timezone.utc)
    return entity
