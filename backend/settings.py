from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    neo4j_uri: str
    neo4j_username: str
    neo4j_password: str
    openai_api_key: str


config = Settings()  # type: ignore
