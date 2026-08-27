import os
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()

def _env_int(name: str, default: int = 0) -> int:
    value = os.getenv(name, str(default)).strip()
    try:
        return int(value)
    except ValueError:
        return default

@dataclass
class Settings:
    # Base paths
    base_dir: str = str(Path(__file__).parent.parent)
    data_dir: str = field(init=False)
    log_dir: str = field(init=False)
    log_file: str = field(init=False)
    
    # DB
    chroma_db_path: str = field(init=False)
    vector_db_collection: str = "zero_budget_memory"
    
    # LLM APIs
    groq_api_key: str = os.getenv("GROQ_API_KEY_1", "")
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY_1", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY_1", "")
    
    # APIs
    notion_api_token: str = os.getenv("NOTION_API_TOKEN", "")
    gmail_credentials_path: str = os.getenv("GMAIL_CREDENTIALS_PATH", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    telegram_token: str = os.getenv("TELEGRAM_TOKEN", "")
    telegram_chat_id: int = _env_int("TELEGRAM_CHAT_ID")
    discord_bot_token: str = os.getenv("DISCORD_BOT_TOKEN", "")
    google_client_id: str = os.getenv("GOOGLE_CLIENT_ID", "")
    approval_timeout: int = _env_int("APPROVAL_TIMEOUT", 300)
    live_view_token: str = os.getenv("LIVE_VIEW_TOKEN", "")
    live_view_bind: str = os.getenv("LIVE_VIEW_BIND", "127.0.0.1")
    
    def __post_init__(self):
        self.data_dir = os.path.join(self.base_dir, "data")
        self.log_dir = os.path.join(self.base_dir, "logs")
        self.log_file = os.path.join(self.log_dir, "agent.log")
        self.chroma_db_path = os.path.join(self.data_dir, "chroma")
        
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)

    def validate_required_services(self) -> dict:
        return {
            "Groq": bool(self.groq_api_key),
            "OpenRouter": bool(self.openrouter_api_key),
            "Gemini": bool(self.gemini_api_key),
            "Notion": bool(self.notion_api_token),
            "Gmail": bool(self.gmail_credentials_path),
            "Telegram": bool(self.telegram_token and self.telegram_chat_id)
        }
settings = Settings()
