class InvalidCredentialsError(Exception):
    def __init__(self) -> None:
        super().__init__("Credenciales inválidas")


class InactiveUserError(Exception):
    def __init__(self) -> None:
        super().__init__("El usuario está inactivo")


class InvalidAccessTokenError(Exception):
    def __init__(self) -> None:
        super().__init__("Token de acceso inválido")


class DocumentPipelineError(Exception):
    pass


class EmptyDocumentError(DocumentPipelineError):
    def __init__(self) -> None:
        super().__init__("El documento está vacío")


class UnsupportedDocumentTypeError(DocumentPipelineError):
    def __init__(self) -> None:
        super().__init__("Tipo de documento no soportado. Use PDF, DOCX o TXT")


class DocumentTooLargeError(DocumentPipelineError):
    def __init__(self) -> None:
        super().__init__("El documento supera el tamaño máximo permitido")


class DocumentMetadataError(DocumentPipelineError):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class BlobStorageNotConfiguredError(DocumentPipelineError):
    def __init__(self) -> None:
        super().__init__("El almacenamiento de documentos no está configurado")


class DocumentTextExtractionError(DocumentPipelineError):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class DocumentVersionNotFoundError(DocumentPipelineError):
    def __init__(self) -> None:
        super().__init__("La versión del documento no existe")


class DocumentVersionNotProcessableError(DocumentPipelineError):
    def __init__(self) -> None:
        super().__init__("La versión del documento no se puede procesar en su estado actual")


class DocumentVersionNotWaitingForReviewError(DocumentPipelineError):
    def __init__(self) -> None:
        super().__init__("La versión del documento no está esperando revisión humana")


class ChunkNotFoundError(DocumentPipelineError):
    def __init__(self) -> None:
        super().__init__("El chunk no existe en esta versión")


class InvalidHumanFeedbackError(DocumentPipelineError):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class ChunkFeedbackNotApplicableError(DocumentPipelineError):
    def __init__(self) -> None:
        super().__init__("El chunk no está pendiente de revisión")


class DocumentIntelligenceNotConfiguredError(DocumentPipelineError):
    def __init__(self, message: str = "El modelo de interpretación no está configurado") -> None:
        super().__init__(message)


class DocumentSearchNotConfiguredError(DocumentPipelineError):
    def __init__(self) -> None:
        super().__init__("Azure AI Search no está configurado")


class DocumentModelCallError(DocumentPipelineError):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class EmbeddingDimensionError(DocumentPipelineError):
    def __init__(self) -> None:
        super().__init__("La dimensión del embedding no coincide con el índice de búsqueda")
