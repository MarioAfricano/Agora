from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    igdb_client_id: str
    igdb_client_secret: str
    import_queue_name: str = "import-jobs"


settings = Settings()
