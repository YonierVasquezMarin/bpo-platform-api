from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "bpo-platform-api"
    app_version: str = "0.1.0"
    environment: str = "development"
    sqlserver_server: str = "localhost"
    sqlserver_database: str = "bpo_platform"
    sqlserver_user: str = "sa"
    sqlserver_password: str = "password"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
