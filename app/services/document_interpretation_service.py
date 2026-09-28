import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from app.core.enum_values import enum_value
from app.core.exceptions import DocumentIntelligenceNotConfiguredError, DocumentModelCallError
from app.models.chunk import Chunk, ChunkStatus
from app.models.chunk_interpretation import ChunkInterpretation
from app.models.document_version import DocumentVersion, DocumentVersionStatus
from app.repositories.document_repository import DocumentRepository
from app.services.chunk_interpretation_client import AzureChunkInterpretationClient, ChunkInterpretationResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class InterpretationSummary:
    chunks_processed: int
    chunks_requiring_review: int
    chunks_approved: int


class DocumentInterpretationService:
    def __init__(
        self,
        document_repository: DocumentRepository,
        interpretation_client: AzureChunkInterpretationClient,
        confidence_threshold: Decimal,
        prompt_version: str,
    ) -> None:
        self._document_repository = document_repository
        self._interpretation_client = interpretation_client
        self._confidence_threshold = self._normalize_confidence(confidence_threshold)
        self._prompt_version = prompt_version
        self._version: DocumentVersion | None = None
        self._chunks: list[Chunk] = []

    def interpret_version(self, version: DocumentVersion, chunks: list[Chunk]) -> InterpretationSummary:
        self._version = version
        self._chunks = chunks
        self._log_interpretation_started()
        self._interpret_all_chunks()
        self._apply_confidence_gate()
        summary = self._build_summary()
        self._log_interpretation_completed(summary)
        return summary

    def _interpret_all_chunks(self) -> None:
        for chunk in self._chunks:
            self._interpret_chunk(chunk)

    def _interpret_chunk(self, chunk: Chunk) -> None:
        try:
            result = self._interpretation_client.interpret_chunk(chunk.content, chunk.section_title)
        except (DocumentIntelligenceNotConfiguredError, DocumentModelCallError) as error:
            self._log_chunk_interpretation_failed(chunk, error)
            raise
        except Exception:
            self._log_chunk_interpretation_unreliable(chunk)
            result = self._unreliable_result()
        self._store_interpretation(chunk, result)
        self._apply_chunk_confidence(chunk, result.confidence)
        self._log_chunk_interpreted(chunk, result)

    def _store_interpretation(self, chunk: Chunk, result: ChunkInterpretationResult) -> None:
        interpretation = ChunkInterpretation(
            chunk_id=chunk.id,
            interpretation_version=self._document_repository.next_interpretation_version(chunk.id),
            interpretation=result.interpretation,
            structured_content=result.structured_content,
            confidence=result.confidence,
            model_name=result.model_name,
            prompt_version=result.prompt_version,
        )
        self._document_repository.add_interpretation(interpretation)
        chunk.current_interpretation_id = interpretation.id
        chunk.confidence = result.confidence

    def _apply_chunk_confidence(self, chunk: Chunk, confidence: Decimal) -> None:
        chunk.status = ChunkStatus.INTERPRETED
        if self._confidence_is_below_threshold(confidence):
            chunk.status = ChunkStatus.NEEDS_REVIEW

    def _apply_confidence_gate(self) -> None:
        self._version.overall_confidence = self._overall_confidence()
        self._version.processed_at = datetime.now(timezone.utc)
        if self._any_chunk_needs_review():
            self._version.status = DocumentVersionStatus.WAITING_HUMAN_REVIEW
            return
        self._approve_interpreted_chunks()
        self._version.status = DocumentVersionStatus.APPROVED
        self._version.approved_at = datetime.now(timezone.utc)

    def _approve_interpreted_chunks(self) -> None:
        for chunk in self._chunks:
            if enum_value(chunk.status) == ChunkStatus.INTERPRETED.value:
                chunk.status = ChunkStatus.APPROVED

    def _any_chunk_needs_review(self) -> bool:
        return any(enum_value(chunk.status) == ChunkStatus.NEEDS_REVIEW.value for chunk in self._chunks)

    def _overall_confidence(self) -> Decimal:
        confidences = [chunk.confidence for chunk in self._chunks if chunk.confidence is not None]
        if not confidences:
            return Decimal("0.00")
        return min(confidences)

    def _confidence_is_below_threshold(self, confidence: Decimal) -> bool:
        return self._normalize_confidence(confidence) < self._confidence_threshold

    def _normalize_confidence(self, confidence: Decimal) -> Decimal:
        value = confidence
        if value > 1:
            value = value / Decimal("100")
        if value < 0:
            value = Decimal("0")
        if value > 1:
            value = Decimal("1")
        return value.quantize(Decimal("0.01"))

    def _build_summary(self) -> InterpretationSummary:
        return InterpretationSummary(
            chunks_processed=len(self._chunks),
            chunks_requiring_review=self._count_status(ChunkStatus.NEEDS_REVIEW),
            chunks_approved=self._count_status(ChunkStatus.APPROVED),
        )

    def _count_status(self, status: ChunkStatus) -> int:
        return sum(1 for chunk in self._chunks if enum_value(chunk.status) == status.value)

    def _log_interpretation_started(self) -> None:
        logger.info("Interpretando %s chunks de la versión %s", len(self._chunks), self._version.id)

    def _log_chunk_interpretation_failed(self, chunk: Chunk, error: Exception) -> None:
        logger.exception(
            "Falló la interpretación del chunk %s de la versión %s: %s",
            chunk.id,
            self._version.id,
            error,
        )

    def _log_chunk_interpretation_unreliable(self, chunk: Chunk) -> None:
        logger.exception(
            "La interpretación del chunk %s de la versión %s no es confiable",
            chunk.id,
            self._version.id,
        )

    def _log_chunk_interpreted(self, chunk: Chunk, result: ChunkInterpretationResult) -> None:
        logger.info(
            "Chunk %s de la versión %s interpretado con confianza %s y estado %s",
            chunk.id,
            self._version.id,
            result.confidence,
            enum_value(chunk.status),
        )

    def _log_interpretation_completed(self, summary: InterpretationSummary) -> None:
        logger.info(
            "Interpretación de la versión %s finalizada en estado %s. Chunks: %s, en revisión: %s, aprobados: %s",
            self._version.id,
            enum_value(self._version.status),
            summary.chunks_processed,
            summary.chunks_requiring_review,
            summary.chunks_approved,
        )

    def _unreliable_result(self) -> ChunkInterpretationResult:
        interpretation = "No fue posible interpretar el fragmento de forma confiable."
        return ChunkInterpretationResult(
            interpretation=interpretation,
            structured_content={"summary": interpretation, "topics": []},
            confidence=Decimal("0.00"),
            model_name="unavailable",
            prompt_version=self._prompt_version,
        )
