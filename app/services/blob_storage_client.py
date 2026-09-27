from azure.storage.blob import BlobServiceClient, ContentSettings

from app.core.config import settings
from app.core.exceptions import BlobStorageNotConfiguredError


class AzureBlobStorageClient:
    def __init__(self, connection_string: str, container_name: str) -> None:
        self._connection_string = connection_string
        self._container_name = container_name

    def upload_bytes(self, blob_path: str, content: bytes, content_type: str) -> str:
        self._ensure_configured()
        container = self._container_client()
        container.upload_blob(
            name=blob_path,
            data=content,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type),
        )
        return container.get_blob_client(blob_path).url

    def download_bytes(self, blob_path: str) -> bytes:
        self._ensure_configured()
        return self._container_client().download_blob(blob_path).readall()

    def delete_blob(self, blob_path: str) -> None:
        self._ensure_configured()
        self._container_client().delete_blob(blob_path)

    def ensure_container(self) -> None:
        self._ensure_configured()
        self._container_client()

    def _ensure_configured(self) -> None:
        if not self._connection_string.strip():
            raise BlobStorageNotConfiguredError()

    def _container_client(self):
        container = self._container_reference()
        if not container.exists():
            container.create_container()
        return container

    def _container_reference(self):
        service = BlobServiceClient.from_connection_string(self._connection_string)
        return service.get_container_client(self._container_name)


def build_blob_storage_client() -> AzureBlobStorageClient:
    return AzureBlobStorageClient(
        connection_string=settings.azure_storage_connection_string,
        container_name=settings.azure_storage_container,
    )
