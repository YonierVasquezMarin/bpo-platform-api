from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "bpo-platform-api"
    app_version: str = "0.1.0"
    environment: str = "development"
    sqlserver_server: str = "localhost"
    sqlserver_database: str = "bpo_platform"
    sqlserver_user: str = "sa"
    sqlserver_password: str = "password"
    encryption_key: str = ""
    encryption_salt: str = ""
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    azure_storage_connection_string: str = ""
    azure_storage_container: str = "documents"
    document_max_size_bytes: int = 20_971_520
    chunk_max_tokens: int = 800
    chunk_overlap_tokens: int = 80
    confidence_threshold: float = 0.80
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2024-10-21"
    azure_openai_chat_deployment: str = ""
    azure_openai_embedding_deployment: str = ""
    azure_openai_embedding_dimensions: int = 1536
    interpretation_prompt_version: str = "v1"
    azure_search_endpoint: str = ""
    azure_search_api_key: str = ""
    azure_search_index_name: str = "knowledge-chunks"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
