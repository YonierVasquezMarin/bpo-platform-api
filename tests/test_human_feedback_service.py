from decimal import Decimal

import pytest

from app.core.exceptions import (
    ChunkFeedbackNotApplicableError,
    DocumentVersionNotWaitingForReviewError,
    InvalidHumanFeedbackError,
)
from app.dtos.document import HumanFeedbackRequestDto
from app.models.chunk import ChunkStatus
from app.models.document_version import DocumentVersionStatus
from app.models.human_feedback import HumanFeedbackAction
from app.services.document_text import HUMAN_CORRECTION_MODEL
from app.services.human_feedback_service import HumanFeedbackService
from tests.test_document_ingestion_orchestrator import _pipeline


def test_approving_the_pending_chunk_schedules_indexing() -> None:
    repository, version, orchestrator, _search = _pipeline({"ambiguo": Decimal("0.42"), "dias": Decimal("0.91")})
    orchestrator.process_uploaded_version(version.id)
    pending = _pending_chunk(repository, version.id)

    result = HumanFeedbackService(repository).register_feedback(
        document_id=version.document_id,
        version_id=version.id,
        user_id=9,
        feedback=HumanFeedbackRequestDto(action=HumanFeedbackAction.APPROVE, chunk_id=pending.id),
    )

    assert result.indexing_scheduled is True
    assert result.status == DocumentVersionStatus.APPROVED.value
    assert version.approved_by_user_id == 9
    assert all(chunk.status == ChunkStatus.APPROVED for chunk in repository.list_chunks(version.id))


def test_correction_creates_a_new_interpretation_linked_to_the_previous_one() -> None:
    repository, version, orchestrator, _search = _pipeline({"ambiguo": Decimal("0.42")})
    orchestrator.process_uploaded_version(version.id)
    pending = _pending_chunk(repository, version.id)
    previous_interpretation_id = pending.current_interpretation_id

    result = HumanFeedbackService(repository).register_feedback(
        document_id=version.document_id,
        version_id=version.id,
        user_id=9,
        feedback=HumanFeedbackRequestDto(
            action=HumanFeedbackAction.CORRECT,
            chunk_id=pending.id,
            feedback_text="El caso ambiguo se escala al supervisor.",
        ),
    )

    correction = repository.find_interpretation(pending.current_interpretation_id)
    assert result.status == DocumentVersionStatus.APPROVED.value
    assert correction.interpretation_version == 2
    assert correction.based_on_interpretation_id == previous_interpretation_id
    assert correction.model_name == HUMAN_CORRECTION_MODEL
    assert correction.structured_content["source"] == "human_correction"
    assert pending.confidence == Decimal("1.00")
    assert repository.latest_execution(version.id).execution_type.value == "REPROCESSING"


def test_rejecting_a_chunk_blocks_indexing() -> None:
    repository, version, orchestrator, _search = _pipeline({"ambiguo": Decimal("0.42")})
    orchestrator.process_uploaded_version(version.id)
    pending = _pending_chunk(repository, version.id)

    result = HumanFeedbackService(repository).register_feedback(
        document_id=version.document_id,
        version_id=version.id,
        user_id=9,
        feedback=HumanFeedbackRequestDto(action=HumanFeedbackAction.REJECT, chunk_id=pending.id, feedback_text="No aplica"),
    )

    assert result.indexing_scheduled is False
    assert result.status == DocumentVersionStatus.REJECTED.value
    with pytest.raises(DocumentVersionNotWaitingForReviewError):
        HumanFeedbackService(repository).register_feedback(
            document_id=version.document_id,
            version_id=version.id,
            user_id=9,
            feedback=HumanFeedbackRequestDto(action=HumanFeedbackAction.APPROVE, chunk_id=pending.id),
        )


def test_correction_requires_text_and_only_applies_to_pending_chunks() -> None:
    repository, version, orchestrator, _search = _pipeline({"ambiguo": Decimal("0.42"), "dias": Decimal("0.91")})
    orchestrator.process_uploaded_version(version.id)
    pending = _pending_chunk(repository, version.id)
    interpreted = next(chunk for chunk in repository.list_chunks(version.id) if chunk.id != pending.id)
    service = HumanFeedbackService(repository)

    with pytest.raises(InvalidHumanFeedbackError):
        service.register_feedback(
            document_id=version.document_id,
            version_id=version.id,
            user_id=9,
            feedback=HumanFeedbackRequestDto(action=HumanFeedbackAction.CORRECT, chunk_id=pending.id, feedback_text="  "),
        )
    with pytest.raises(ChunkFeedbackNotApplicableError):
        service.register_feedback(
            document_id=version.document_id,
            version_id=version.id,
            user_id=9,
            feedback=HumanFeedbackRequestDto(action=HumanFeedbackAction.APPROVE, chunk_id=interpreted.id),
        )


def _pending_chunk(repository, version_id: int):
    return next(chunk for chunk in repository.list_chunks(version_id) if chunk.status == ChunkStatus.NEEDS_REVIEW)
