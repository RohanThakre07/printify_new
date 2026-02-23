from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Printify Product Automation"
    database_path: str = "./data/app.db"
    storage_dir: str = "./data"
    printify_api_key: str = ""
    printify_shop_id: str = ""
    ollama_model: str = "llama3.1:8b"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def database_url(self) -> str:
        path = Path(self.database_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{path.resolve()}"


settings = Settings()
Path(settings.storage_dir).mkdir(parents=True, exist_ok=True)
