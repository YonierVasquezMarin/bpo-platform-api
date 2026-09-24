import logging
from datetime import datetime, timezone
from decimal import Decimal

from app.core.enum_values import enum_value
from app.core.exceptions import (
    ChunkFeedbackNotApplicableError,
    ChunkNotFoundError,
    DocumentVersionNotFoundError,
    DocumentVersionNotWaitingForReviewError,
    InvalidHumanFeedbackError,
)
from app.dtos.document import HumanFeedbackRequestDto, HumanFeedbackResponseDto
from app.models.audit_event import AuditEvent
from app.models.chunk import Chunk, ChunkStatus
from app.models.chunk_interpretation import ChunkInterpretation
from app.models.document_version import DocumentVersion, DocumentVersionStatus
from app.models.human_feedback import HumanFeedback, HumanFeedbackAction
from app.models.processing_execution import ProcessingExecution, ProcessingExecutionStatus, ProcessingExecutionType
from app.repositories.document_repository import DocumentRepository
from app.services.document_text import HUMAN_CORRECTION_MODEL, HUMAN_PROMPT_VERSION

logger = logging.getLogger(__name__)


class HumanFeedbackService:
    def __init__(self, document_repository: DocumentRepository) -> None:
        self._document_repository = document_repository
        self._document_id = 0
        self._version_id = 0
        self._user_id = 0
        self._feedback: HumanFeedbackRequestDto | None = None
        self._version: DocumentVersion | None = None
        self._chunk: Chunk | None = None
        self._chunks: list[Chunk] = []
        self._indexing_scheduled = False

    def register_feedback(
        self,
        document_id: int,
        version_id: int,
        user_id: int,
        feedback: HumanFeedbackRequestDto,
    ) -> HumanFeedbackResponseDto:
        self._document_id = document_id
        self._version_id = version_id
        self._user_id = user_id
        self._feedback = feedback
        self._chunk = None
        self._indexing_scheduled = False
        self._log_feedback_started()
        try:
            return self._execute_feedback()
        except (
            DocumentVersionNotFoundError,
            DocumentVersionNotWaitingForReviewError,
            ChunkNotFoundError,
            InvalidHumanFeedbackError,
            ChunkFeedbackNotApplicableError,
        ):
            self._document_repository.rollback()
            raise
        except Exception:
            self._document_repository.rollback()
            self._log_feedback_failed()
            raise

    def _execute_feedback(self) -> HumanFeedbackResponseDto:
        self._load_version()
        self._ensure_version_waits_for_review()
        self._load_chunks()
        self._load_chunk_when_required()
        self._apply_action()
        self._resolve_version_status()
        self._register_audit_event()
        self._document_repository.commit()
        self._log_feedback_succeeded()
        return self._build_response()

    def _load_version(self) -> None:
        version = self._document_repository.find_version(self._document_id, self._version_id)
        if version is None:
            raise DocumentVersionNotFoundError()
        self._version = version

    def _ensure_version_waits_for_review(self) -> None:
        if enum_value(self._version.status) != DocumentVersionStatus.WAITING_HUMAN_REVIEW.value:
            raise DocumentVersionNotWaitingForReviewError()

    def _load_chunks(self) -> None:
        self._chunks = self._document_repository.list_chunks(self._version.id)

    def _load_chunk_when_required(self) -> None:
        if self._action_requires_chunk():
            self._chunk = self._require_chunk()
            self._ensure_chunk_is_pending_review()
            return
        if self._feedback.chunk_id is not None:
            self._chunk = self._require_chunk()

    def _action_requires_chunk(self) -> bool:
        return self._feedback.action in {HumanFeedbackAction.APPROVE, HumanFeedbackAction.CORRECT}

    def _require_chunk(self) -> Chunk:
        if self._feedback.chunk_id is None:
            raise InvalidHumanFeedbackError("Debe indicar el chunk que se revisa")
        chunk = self._document_repository.find_chunk(self._version.id, self._feedback.chunk_id)
        if chunk is None:
            raise ChunkNotFoundError()
        return chunk

    def _ensure_chunk_is_pending_review(self) -> None:
        if enum_value(self._chunk.status) != ChunkStatus.NEEDS_REVIEW.value:
            raise ChunkFeedbackNotApplicableError()

    def _apply_action(self) -> None:
        if self._feedback.action == HumanFeedbackAction.APPROVE:
            self._approve_chunk()
            return
        if self._feedback.action == HumanFeedbackAction.REJECT:
            self._reject()
            return
        self._correct_chunk()

    def _approve_chunk(self) -> None:
        self._chunk.status = ChunkStatus.APPROVED
        self._store_feedback(previous_interpretation_id=self._chunk.current_interpretation_id)

    def _reject(self) -> None:
        if self._chunk is not None:
            self._chunk.status = ChunkStatus.REJECTED
        self._version.status = DocumentVersionStatus.REJECTED
        previous_interpretation_id = None
        if self._chunk is not None:
            previous_interpretation_id = self._chunk.current_interpretation_id
        self._store_feedback(previous_interpretation_id)

    def _correct_chunk(self) -> None:
        correction = self._required_feedback_text()
        previous_interpretation_id = self._chunk.current_interpretation_id
        self._version.status = DocumentVersionStatus.REPROCESSING
        interpretation = self._build_human_interpretation(correction)
        self._document_repository.add_interpretation(interpretation)
        self._chunk.current_interpretation_id = interpretation.id
        self._chunk.confidence = interpretation.confidence
        self._chunk.status = ChunkStatus.APPROVED
        self._store_feedback(previous_interpretation_id)
        self._store_reprocessing_execution()

    def _required_feedback_text(self) -> str:
        text = self._feedback.feedback_text
        if text is None or not text.strip():
            raise InvalidHumanFeedbackError("La corrección debe incluir el texto revisado")
        return text.strip()

    def _build_human_interpretation(self, correction: str) -> ChunkInterpretation:
        return ChunkInterpretation(
            chunk_id=self._chunk.id,
            interpretation_version=self._document_repository.next_interpretation_version(self._chunk.id),
            interpretation=correction,
            structured_content={"summary": correction, "topics": [], "source": "human_correction"},
            confidence=Decimal("1.00"),
            model_name=HUMAN_CORRECTION_MODEL,
            prompt_version=HUMAN_PROMPT_VERSION,
            based_on_interpretation_id=self._chunk.current_interpretation_id,
        )

    def _store_feedback(self, previous_interpretation_id: int | None) -> None:
        feedback = HumanFeedback(
            document_version_id=self._version.id,
            chunk_id=self._chunk.id if self._chunk is not None else None,
            action=self._feedback.action,
            feedback_text=self._clean_feedback_text(),
            previous_interpretation_id=previous_interpretation_id,
            created_by_user_id=self._user_id,
        )
        self._document_repository.add_feedback(feedback)

    def _clean_feedback_text(self) -> str | None:
        if self._feedback.feedback_text is None:
            return None
        stripped = self._feedback.feedback_text.strip()
        if not stripped:
            return None
        return stripped

    def _store_reprocessing_execution(self) -> None:
        self._document_repository.add_execution(
            ProcessingExecution(
                document_version_id=self._version.id,
                execution_type=ProcessingExecutionType.REPROCESSING,
                status=ProcessingExecutionStatus.COMPLETED,
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                chunks_processed=1,
                chunks_requiring_review=0,
                chunks_approved=1,
                execution_metadata={"chunk_id": self._chunk.id, "source": "human_correction"},
            )
        )

    def _resolve_version_status(self) -> None:
        self._keep_reviewed_chunk_in_the_list()
        if self._version_is_rejected():
            self._version.status = DocumentVersionStatus.REJECTED
            self._indexing_scheduled = False
            return
        if self._any_chunk_needs_review():
            self._version.status = DocumentVersionStatus.WAITING_HUMAN_REVIEW
            self._indexing_scheduled = False
            return
        self._promote_interpreted_chunks()
        self._version.status = DocumentVersionStatus.APPROVED
        self._version.approved_at = datetime.now(timezone.utc)
        self._version.approved_by_user_id = self._user_id
        self._indexing_scheduled = True

    def _keep_reviewed_chunk_in_the_list(self) -> None:
        if self._chunk is None:
            return
        self._chunks = [self._chunk if chunk.id == self._chunk.id else chunk for chunk in self._chunks]

    def _version_is_rejected(self) -> bool:
        if enum_value(self._version.status) == DocumentVersionStatus.REJECTED.value:
            return True
        return any(enum_value(chunk.status) == ChunkStatus.REJECTED.value for chunk in self._chunks)

    def _any_chunk_needs_review(self) -> bool:
        return any(enum_value(chunk.status) == ChunkStatus.NEEDS_REVIEW.value for chunk in self._chunks)

    def _promote_interpreted_chunks(self) -> None:
        for chunk in self._chunks:
            if enum_value(chunk.status) == ChunkStatus.INTERPRETED.value:
                chunk.status = ChunkStatus.APPROVED

    def _register_audit_event(self) -> None:
        self._document_repository.add_audit_event(
            AuditEvent(
                entity_type="document_version",
                entity_id=self._version.id,
                event_type="HUMAN_FEEDBACK_REGISTERED",
                actor_type="USER",
                actor_user_id=self._user_id,
                event_data={
                    "action": enum_value(self._feedback.action),
                    "chunk_id": self._chunk.id if self._chunk is not None else None,
                },
            )
        )

    def _build_response(self) -> HumanFeedbackResponseDto:
        return HumanFeedbackResponseDto(
            document_id=self._document_id,
            version_id=self._version.id,
            status=enum_value(self._version.status),
            action=enum_value(self._feedback.action),
            chunk_id=self._chunk.id if self._chunk is not None else None,
            indexing_scheduled=self._indexing_scheduled,
        )

    def _log_feedback_started(self) -> None:
        logger.info(
            "Registrando feedback %s para la versión %s",
            self._feedback.action,
            self._version_id,
        )

    def _log_feedback_succeeded(self) -> None:
        logger.info("Feedback registrado para la versión %s", self._version.id)

    def _log_feedback_failed(self) -> None:
        logger.exception("Falló el registro de feedback de la versión %s", self._version_id)
