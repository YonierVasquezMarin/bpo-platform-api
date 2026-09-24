from app.core.enum_values import enum_value
from app.core.exceptions import DocumentVersionNotFoundError, DocumentVersionNotProcessableError
from app.models.document_version import DocumentVersion
from app.repositories.document_repository import DocumentRepository
from app.services.document_text import PROCESSABLE_VERSION_STATUSES


class DocumentVersionWorkflow:
    def __init__(self, document_repository: DocumentRepository) -> None:
        self._document_repository = document_repository

    def ensure_can_process(self, document_id: int, version_id: int) -> DocumentVersion:
        version = self._document_repository.find_version(document_id, version_id)
        if version is None:
            raise DocumentVersionNotFoundError()
        if enum_value(version.status) not in PROCESSABLE_VERSION_STATUSES:
            raise DocumentVersionNotProcessableError()
        return version
