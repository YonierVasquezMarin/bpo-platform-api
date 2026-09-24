class InMemoryBlobStorage:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.deleted: list[str] = []

    def upload_bytes(self, blob_path: str, content: bytes, content_type: str) -> str:
        self.files[blob_path] = content
        return f"https://storage.local/{blob_path}"

    def download_bytes(self, blob_path: str) -> bytes:
        return self.files[blob_path]

    def delete_blob(self, blob_path: str) -> None:
        self.deleted.append(blob_path)
        self.files.pop(blob_path, None)


class RecordingSearchClient:
    def __init__(self) -> None:
        self.documents: list[object] = []

    def upsert_document(self, document: object) -> str:
        self.documents.append(document)
        return document.document_key


class FixedEmbeddingClient:
    def create_embedding(self, content: str) -> list[float]:
        return [0.1, 0.2]
