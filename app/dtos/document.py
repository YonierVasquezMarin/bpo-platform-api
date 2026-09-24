from datetime import datetime

from pydantic import BaseModel, Field

from app.models.human_feedback import HumanFeedbackAction


class DocumentCreatedDto(BaseModel):
    document_id: int
    version_id: int
    version_number: int
    file_name: str
    status: str


class DocumentProcessingAcceptedDto(BaseModel):
    document_id: int
    version_id: int
    status: str


class DocumentChunkDto(BaseModel):
    id: int
    chunk_number: int
    section_title: str | None
    page_number: int | None
    content_type: str
    content: str
    token_count: int | None
    confidence: float | None
    status: str
    interpretation: str | None


class ProcessingExecutionDto(BaseModel):
    id: int
    execution_type: str
    status: str
    chunks_processed: int
    chunks_requiring_review: int
    chunks_approved: int
    error_message: str | None


class DocumentVersionDetailDto(BaseModel):
    document_id: int
    document_name: str
    document_type: str
    version_id: int
    version_number: int
    file_name: str
    file_type: str
    status: str
    overall_confidence: float | None
    processed_at: datetime | None
    approved_at: datetime | None
    indexed_at: datetime | None
    chunks: list[DocumentChunkDto]
    latest_execution: ProcessingExecutionDto | None


class HumanFeedbackRequestDto(BaseModel):
    action: HumanFeedbackAction
    chunk_id: int | None = None
    feedback_text: str | None = Field(default=None, max_length=8000)


class HumanFeedbackResponseDto(BaseModel):
    document_id: int
    version_id: int
    status: str
    action: str
    chunk_id: int | None
    indexing_scheduled: bool
