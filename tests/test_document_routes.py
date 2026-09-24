from collections.abc import Iterator
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.deps import (
    get_current_user,
    get_document_indexing_task,
    get_document_processing_task,
    get_document_upload_service,
    get_document_version_query_service,
    get_document_version_workflow,
    get_human_feedback_service,
)
from app.core.exceptions import DocumentVersionNotFoundError, DocumentVersionNotProcessableError
from app.dtos.document import DocumentCreatedDto, DocumentVersionDetailDto, HumanFeedbackResponseDto
from app.main import app
from app.models.document_version import DocumentVersionStatus
from app.models.user import UserRole

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> Iterator[None]:
    yield
    app.dependency_overrides.clear()


def test_upload_requires_authentication() -> None:
    response = client.post("/api/documents", files={"file": ("nota.txt", b"hola", "text/plain")})

    assert response.status_code == 401
    assert response.json()["detail"] == "No autenticado"


def test_upload_rejects_users_without_document_permission() -> None:
    _override_user(UserRole.USER)
    app.dependency_overrides[get_document_upload_service] = lambda: MagicMock()

    response = client.post("/api/documents", files={"file": ("nota.txt", b"hola", "text/plain")})

    assert response.status_code == 403
    assert response.json()["detail"] == "No tiene permisos para gestionar documentos"


def test_upload_returns_created_version_and_schedules_processing() -> None:
    _override_user(UserRole.KNOWLEDGE_MANAGER)
    upload_service = MagicMock()
    upload_service.upload_document.return_value = DocumentCreatedDto(
        document_id=3,
        version_id=8,
        version_number=1,
        file_name="nota.txt",
        status="UPLOADED",
    )
    scheduled: list[int] = []
    app.dependency_overrides[get_document_upload_service] = lambda: upload_service
    app.dependency_overrides[get_document_processing_task] = lambda: scheduled.append

    response = client.post(
        "/api/documents",
        data={"name": "Nota operativa"},
        files={"file": ("nota.txt", b"hola", "text/plain")},
    )

    assert response.status_code == 201
    assert response.json()["version_id"] == 8
    assert scheduled == [8]
    upload_service.upload_document.assert_called_once()


def test_get_version_returns_404_when_it_does_not_exist() -> None:
    _override_user(UserRole.ADMIN)
    query_service = MagicMock()
    query_service.get_version.side_effect = DocumentVersionNotFoundError()
    app.dependency_overrides[get_document_version_query_service] = lambda: query_service

    response = client.get("/api/documents/1/versions/2")

    assert response.status_code == 404


def test_process_returns_conflict_when_the_version_cannot_be_processed() -> None:
    _override_user(UserRole.ADMIN)
    workflow = MagicMock()
    workflow.ensure_can_process.side_effect = DocumentVersionNotProcessableError()
    app.dependency_overrides[get_document_version_workflow] = lambda: workflow

    response = client.post("/api/documents/1/versions/2/process")

    assert response.status_code == 409


def test_process_accepts_a_version_ready_for_processing() -> None:
    _override_user(UserRole.ADMIN)
    workflow = MagicMock()
    workflow.ensure_can_process.return_value = SimpleNamespace(id=2, status=DocumentVersionStatus.UPLOADED)
    scheduled: list[int] = []
    app.dependency_overrides[get_document_version_workflow] = lambda: workflow
    app.dependency_overrides[get_document_processing_task] = lambda: scheduled.append

    response = client.post("/api/documents/1/versions/2/process")

    assert response.status_code == 202
    assert response.json()["status"] == "UPLOADED"
    assert scheduled == [2]


def test_feedback_schedules_indexing_when_the_version_is_approved() -> None:
    _override_user(UserRole.ADMIN)
    feedback_service = MagicMock()
    feedback_service.register_feedback.return_value = HumanFeedbackResponseDto(
        document_id=1,
        version_id=2,
        status="APPROVED",
        action="APPROVE",
        chunk_id=5,
        indexing_scheduled=True,
    )
    scheduled: list[int] = []
    app.dependency_overrides[get_human_feedback_service] = lambda: feedback_service
    app.dependency_overrides[get_document_indexing_task] = lambda: scheduled.append

    response = client.post(
        "/api/documents/1/versions/2/feedback",
        json={"action": "APPROVE", "chunk_id": 5},
    )

    assert response.status_code == 200
    assert response.json()["indexing_scheduled"] is True
    assert scheduled == [2]


def test_get_version_returns_the_detail_payload() -> None:
    _override_user(UserRole.ADMIN)
    query_service = MagicMock()
    query_service.get_version.return_value = DocumentVersionDetailDto(
        document_id=1,
        document_name="Politica",
        document_type="TXT",
        version_id=2,
        version_number=1,
        file_name="politica.txt",
        file_type="txt",
        status="UPLOADED",
        overall_confidence=None,
        processed_at=None,
        approved_at=None,
        indexed_at=None,
        chunks=[],
        latest_execution=None,
    )
    app.dependency_overrides[get_document_version_query_service] = lambda: query_service

    response = client.get("/api/documents/1/versions/2")

    assert response.status_code == 200
    assert response.json()["document_name"] == "Politica"


def _override_user(role: UserRole) -> None:
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=4, role=role, is_active=True)
