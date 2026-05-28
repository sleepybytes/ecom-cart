from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./cart.db"
    app_name: str = "Cart Management API"

    class Config:
        env_file = ".env"


settings = Settings()
