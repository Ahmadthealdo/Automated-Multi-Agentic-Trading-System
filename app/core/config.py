import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# Base directory of the repository
BASE_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = BASE_DIR / "front-end"

# Load local .env file
load_dotenv(find_dotenv())

class Settings:
    PROJECT_NAME: str = "Automated-Multi-Agentic-Trading-System"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = (
        "Decoupled Asynchronous Multi-Agent Quantitative Trading Desk "
        "powered by OpenAI Agents SDK, Gemini 2.5 Flash, FastAPI, and Neon PostgreSQL"
    )
    
    # LLM Settings
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    GEMINI_MODEL: str = "models/gemini-2.5-flash"
    GEMINI_MAX_RETRIES: int = 5
    
    # Database Settings
    NEON_DB_URL: str = os.getenv(
        "neon_db", 
        "postgresql+psycopg://mr..ca:PASS@abs-pooler.us-east-2.aws.neon.tech/test-sess?sslmode=require&channel_binding=require"
    )
    
    # Server Settings
    SERVER_HOST: str = "127.0.0.1"
    SERVER_PORT: int = 8000

    # JWT & OAuth2 Security Settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "b3a4c5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours

    @classmethod
    def get_database_url(cls) -> str:
        """Ensure async psycopg driver protocol for SQLAlchemy async engine."""
        url = cls.NEON_DB_URL
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url

settings = Settings()
