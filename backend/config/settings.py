from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # AI
    gemini_api_key: str = ""

    # News
    newsapi_key: str = ""

    # Gmail
    gmail_oauth_token: str = ""  # JSON string
    gmail_sender: str = ""
    gmail_recipient: str = ""

    # Google Sheets
    google_sheets_id: str = ""
    google_sheets_name: str = "StockBrief_v2"
    google_service_account_json: str = ""  # JSON string

    # Google Drive
    google_drive_folder_id: str = ""

    # GitHub
    github_token: str = ""
    github_owner: str = ""
    github_repo: str = "StockBrief"
    github_branch: str = "main"

    # App
    app_env: str = "development"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Derived paths (not from env)
    root_dir: Path = Field(default=Path(__file__).resolve().parent.parent.parent)

    @property
    def shared_dir(self) -> Path:
        return self.root_dir / "shared"

    @property
    def data_dir(self) -> Path:
        return self.root_dir / "data"

    @property
    def mock_data_dir(self) -> Path:
        return self.shared_dir / "mock-data"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
