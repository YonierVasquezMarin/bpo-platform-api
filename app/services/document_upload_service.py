import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from app.core.exceptions import (
    BlobStorageNotConfiguredError,
    DocumentMetadataError,
    DocumentTooLargeError,
    EmptyDocumentError,
    UnsupportedDocumentTypeError,
)
from app.dtos.document import DocumentCreatedDto
from app.models.audit_event import AuditEvent
from app.models.document import Document
from app.models.document_version import DocumentVersion, DocumentVersionStatus
from app.repositories.document_repository import DocumentRepository
from app.services.blob_storage_client import AzureBlobStorageClient

logger = logging.getLogger(__name__)

_EXTENSIONS = {".pdf": "pdf", ".docx": "docx", ".txt": "txt"}
_CONTENT_TYPES = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "txt": "text/plain",
}


@dataclass(frozen=True)
class DocumentUploadCommand:
    file_name: str
    file_content: bytes
    uploaded_by_user_id: int
    name: str | None
    document_type: str | None
    description: str | None
    category: str | None
    source_system: str | None


class DocumentUploadService:
    def __init__(
        self,
        document_repository: DocumentRepository,
        blob_storage: AzureBlobStorageClient,
        container_name: str,
        max_size_bytes: int,
    ) -> None:
        self._document_repository = document_repository
        self._blob_storage = blob_storage
        self._container_name = container_name
        self._max_size_bytes = max_size_bytes
        self._command: DocumentUploadCommand | None = None
        self._blob_path = ""
        self._blob_url: str | None = None
        self._blob_uploaded = False

    def upload_document(self, command: DocumentUploadCommand) -> DocumentCreatedDto:
        self._command = command
        self._blob_uploaded = False
        self._log_upload_started()
        try:
            return self._execute_upload()
        except (
            EmptyDocumentError,
            DocumentTooLargeError,
            UnsupportedDocumentTypeError,
            DocumentMetadataError,
            BlobStorageNotConfiguredError,
        ) as error:
            self._log_upload_rejected(error)
            raise
        except Exception:
            self._log_upload_failed()
            raise

    def _execute_upload(self) -> DocumentCreatedDto:
        self._validate_command()
        self._store_blob()
        try:
            return self._persist_document()
        except Exception:
            self._delete_uploaded_blob()
            raise

    def _validate_command(self) -> None:
        self._ensure_file_is_not_empty()
        self._ensure_file_is_within_size_limit()
        self._ensure_extension_is_supported()
        self._ensure_metadata_fits_columns()

    def _ensure_file_is_not_empty(self) -> None:
        if not self._command.file_content:
            raise EmptyDocumentError()

    def _ensure_file_is_within_size_limit(self) -> None:
        if len(self._command.file_content) > self._max_size_bytes:
            raise DocumentTooLargeError()

    def _ensure_extension_is_supported(self) -> None:
        if self._file_extension() not in _EXTENSIONS:
            raise UnsupportedDocumentTypeError()

    def _ensure_metadata_fits_columns(self) -> None:
        if len(self._safe_file_name()) > 255:
            raise DocumentMetadataError("El nombre del archivo supera 255 caracteres")
        if len(self._display_name()) > 255:
            raise DocumentMetadataError("El nombre del documento supera 255 caracteres")
        if len(self._resolved_document_type()) > 50:
            raise DocumentMetadataError("El tipo de documento supera 50 caracteres")
        if self._optional_text_is_too_long(self._command.category, 100):
            raise DocumentMetadataError("La categoría supera 100 caracteres")
        if self._optional_text_is_too_long(self._command.source_system, 100):
            raise DocumentMetadataError("El sistema de origen supera 100 caracteres")

    def _optional_text_is_too_long(self, value: str | None, limit: int) -> bool:
        if value is None:
            return False
        return len(value.strip()) > limit

    def _store_blob(self) -> None:
        self._blob_path = f"{uuid4().hex}/{self._safe_file_name()}"
        self._blob_url = self._blob_storage.upload_bytes(
            blob_path=self._blob_path,
            content=self._command.file_content,
            content_type=_CONTENT_TYPES[self._file_type()],
        )
        self._blob_uploaded = True
        self._log_blob_stored()

    def _persist_document(self) -> DocumentCreatedDto:
        document = self._build_document()
        self._document_repository.add_document(document)
        version = self._build_version(document)
        self._document_repository.add_version(version)
        document.current_version_id = version.id
        self._document_repository.add_audit_event(self._build_audit_event(version))
        self._document_repository.commit()
        self._log_upload_succeeded(version)
        return self._build_result(document, version)

    def _build_document(self) -> Document:
        return Document(
            name=self._display_name(),
            document_type=self._resolved_document_type(),
            description=self._clean_optional(self._command.description),
            category=self._clean_optional(self._command.category),
            source_system=self._clean_optional(self._command.source_system),
            is_active=True,
        )

    def _build_version(self, document: Document) -> DocumentVersion:
        return DocumentVersion(
            document_id=document.id,
            version_number=1,
            file_name=self._safe_file_name(),
            file_type=self._file_type(),
            file_size_bytes=len(self._command.file_content),
            blob_container=self._container_name,
            blob_path=self._blob_path,
            blob_url=self._blob_url,
            checksum=sha256(self._command.file_content).hexdigest(),
            status=DocumentVersionStatus.UPLOADED,
            uploaded_at=datetime.now(timezone.utc),
            uploaded_by_user_id=self._command.uploaded_by_user_id,
        )

    def _build_audit_event(self, version: DocumentVersion) -> AuditEvent:
        return AuditEvent(
            entity_type="document_version",
            entity_id=version.id,
            event_type="DOCUMENT_UPLOADED",
            actor_type="USER",
            actor_user_id=self._command.uploaded_by_user_id,
            event_data={
                "file_name": version.file_name,
                "checksum": version.checksum,
                "document_id": version.document_id,
            },
        )

    def _build_result(self, document: Document, version: DocumentVersion) -> DocumentCreatedDto:
        return DocumentCreatedDto(
            document_id=document.id,
            version_id=version.id,
            version_number=version.version_number,
            file_name=version.file_name,
            status=DocumentVersionStatus.UPLOADED.value,
        )

    def _delete_uploaded_blob(self) -> None:
        if not self._blob_uploaded:
            return
        try:
            self._blob_storage.delete_blob(self._blob_path)
        except Exception:
            self._log_blob_delete_failed()

    def _file_extension(self) -> str:
        return Path(self._command.file_name).suffix.lower()

    def _file_type(self) -> str:
        return _EXTENSIONS[self._file_extension()]

    def _safe_file_name(self) -> str:
        base_name = Path(self._command.file_name).name
        cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", base_name).lstrip("._")
        if "." not in cleaned:
            return f"{cleaned or 'documento'}{self._file_extension()}"
        return cleaned

    def _display_name(self) -> str:
        provided_name = self._clean_optional(self._command.name)
        if provided_name:
            return provided_name
        original_stem = Path(self._command.file_name).stem.strip()
        if original_stem:
            return original_stem[:255]
        return self._safe_file_name()[:255]

    def _resolved_document_type(self) -> str:
        provided_type = self._clean_optional(self._command.document_type)
        if provided_type:
            return provided_type
        return self._file_type().upper()

    def _clean_optional(self, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            return None
        return stripped

    def _log_upload_started(self) -> None:
        logger.info("Iniciando cargue del documento %s", self._command.file_name)

    def _log_upload_rejected(self, error: Exception) -> None:
        logger.warning("Cargue rechazado para %s: %s", self._command.file_name, error)

    def _log_blob_stored(self) -> None:
        logger.info("Blob del documento %s almacenado en %s", self._command.file_name, self._blob_path)

    def _log_upload_succeeded(self, version: DocumentVersion) -> None:
        logger.info("Documento cargado en la versión %s", version.id)

    def _log_upload_failed(self) -> None:
        logger.exception("Falló el cargue del documento %s", self._command.file_name)

    def _log_blob_delete_failed(self) -> None:
        logger.exception("No se pudo eliminar el blob %s tras un error de persistencia", self._blob_path)
