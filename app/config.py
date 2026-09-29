from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    secret_key: str


settings = Settings()
