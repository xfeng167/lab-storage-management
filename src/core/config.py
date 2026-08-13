from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Lab Storage Management API"
    debug: bool = True
    database_url: str = "mysql+pymysql://lab_user:lab_password@localhost:3306/lab_storage_db"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
