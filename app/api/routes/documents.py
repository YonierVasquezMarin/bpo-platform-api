from collections.abc import Callable

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status

from app.api.deps import (
    get_current_document_manager,
    get_document_indexing_task,
    get_document_processing_task,
    get_document_upload_service,
    get_document_version_query_service,
    get_document_version_workflow,
    get_human_feedback_service,
)
from app.core.config import settings
from app.core.enum_values import enum_value
from app.core.exceptions import (
    BlobStorageNotConfiguredError,
    ChunkFeedbackNotApplicableError,
    ChunkNotFoundError,
    DocumentMetadataError,
    DocumentPipelineError,
    DocumentSearchNotConfiguredError,
    DocumentTooLargeError,
    DocumentVersionNotFoundError,
    DocumentVersionNotProcessableError,
    DocumentVersionNotWaitingForReviewError,
    EmptyDocumentError,
    InvalidHumanFeedbackError,
    UnsupportedDocumentTypeError,
)
from app.dtos.document import (
    DocumentCreatedDto,
    DocumentProcessingAcceptedDto,
    DocumentVersionDetailDto,
    HumanFeedbackRequestDto,
    HumanFeedbackResponseDto,
)
from app.models.user import User
from app.services.document_upload_service import DocumentUploadCommand, DocumentUploadService
from app.services.document_version_query_service import DocumentVersionQueryService
from app.services.document_version_workflow import DocumentVersionWorkflow
from app.services.human_feedback_service import HumanFeedbackService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "",
    response_model=DocumentCreatedDto,
    status_code=status.HTTP_201_CREATED,
)
def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
    document_type: str | None = Form(default=None),
    description: str | None = Form(default=None),
    category: str | None = Form(default=None),
    source_system: str | None = Form(default=None),
    current_user: User = Depends(get_current_document_manager),
    upload_service: DocumentUploadService = Depends(get_document_upload_service),
    processing_task: Callable[[int], None] = Depends(get_document_processing_task),
) -> DocumentCreatedDto:
    try:
        created = upload_service.upload_document(
            _build_upload_command(
                file=file,
                name=name,
                document_type=document_type,
                description=description,
                category=category,
                source_system=source_system,
                uploaded_by_user_id=current_user.id,
            )
        )
    except DocumentPipelineError as ex:
        raise _http_error_for_document(ex) from ex
    background_tasks.add_task(processing_task, created.version_id)
    return created


@router.get(
    "/{document_id}/versions/{version_id}",
    response_model=DocumentVersionDetailDto,
)
def get_document_version(
    document_id: int,
    version_id: int,
    _current_user: User = Depends(get_current_document_manager),
    query_service: DocumentVersionQueryService = Depends(get_document_version_query_service),
) -> DocumentVersionDetailDto:
    try:
        return query_service.get_version(document_id, version_id)
    except DocumentPipelineError as ex:
        raise _http_error_for_document(ex) from ex


@router.post(
    "/{document_id}/versions/{version_id}/process",
    response_model=DocumentProcessingAcceptedDto,
    status_code=status.HTTP_202_ACCEPTED,
)
def process_document_version(
    document_id: int,
    version_id: int,
    background_tasks: BackgroundTasks,
    _current_user: User = Depends(get_current_document_manager),
    workflow: DocumentVersionWorkflow = Depends(get_document_version_workflow),
    processing_task: Callable[[int], None] = Depends(get_document_processing_task),
) -> DocumentProcessingAcceptedDto:
    try:
        version = workflow.ensure_can_process(document_id, version_id)
    except DocumentPipelineError as ex:
        raise _http_error_for_document(ex) from ex
    background_tasks.add_task(processing_task, version.id)
    return DocumentProcessingAcceptedDto(
        document_id=document_id,
        version_id=version.id,
        status=enum_value(version.status),
    )


@router.post(
    "/{document_id}/versions/{version_id}/feedback",
    response_model=HumanFeedbackResponseDto,
)
def register_human_feedback(
    document_id: int,
    version_id: int,
    feedback: HumanFeedbackRequestDto,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_document_manager),
    feedback_service: HumanFeedbackService = Depends(get_human_feedback_service),
    indexing_task: Callable[[int], None] = Depends(get_document_indexing_task),
) -> HumanFeedbackResponseDto:
    try:
        result = feedback_service.register_feedback(
            document_id=document_id,
            version_id=version_id,
            user_id=current_user.id,
            feedback=feedback,
        )
    except DocumentPipelineError as ex:
        raise _http_error_for_document(ex) from ex
    if result.indexing_scheduled:
        background_tasks.add_task(indexing_task, result.version_id)
    return result


def _build_upload_command(
    file: UploadFile,
    name: str | None,
    document_type: str | None,
    description: str | None,
    category: str | None,
    source_system: str | None,
    uploaded_by_user_id: int,
) -> DocumentUploadCommand:
    return DocumentUploadCommand(
        file_name=file.filename or "",
        file_content=_read_upload_content(file),
        uploaded_by_user_id=uploaded_by_user_id,
        name=_blank_to_none(name),
        document_type=_blank_to_none(document_type),
        description=_blank_to_none(description),
        category=_blank_to_none(category),
        source_system=_blank_to_none(source_system),
    )


def _read_upload_content(upload: UploadFile) -> bytes:
    upload.file.seek(0)
    content = upload.file.read(settings.document_max_size_bytes + 1)
    if len(content) > settings.document_max_size_bytes:
        raise DocumentTooLargeError()
    return content


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    return stripped


def _http_error_for_document(error: DocumentPipelineError) -> HTTPException:
    return HTTPException(status_code=_status_code_for_document_error(error), detail=str(error))


def _status_code_for_document_error(error: DocumentPipelineError) -> int:
    if isinstance(error, DocumentTooLargeError):
        return status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    if isinstance(error, (EmptyDocumentError, UnsupportedDocumentTypeError, DocumentMetadataError, InvalidHumanFeedbackError)):
        return status.HTTP_422_UNPROCESSABLE_ENTITY
    if isinstance(error, (DocumentVersionNotFoundError, ChunkNotFoundError)):
        return status.HTTP_404_NOT_FOUND
    if isinstance(
        error,
        (
            DocumentVersionNotProcessableError,
            DocumentVersionNotWaitingForReviewError,
            ChunkFeedbackNotApplicableError,
        ),
    ):
        return status.HTTP_409_CONFLICT
    if isinstance(error, (BlobStorageNotConfiguredError, DocumentSearchNotConfiguredError)):
        return status.HTTP_503_SERVICE_UNAVAILABLE
    return status.HTTP_400_BAD_REQUEST
