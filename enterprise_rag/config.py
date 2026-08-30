import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def secret(name: str) -> Optional[str]:
    """Load a secret from a mounted file first, then the environment."""
    file_path = os.getenv(f"{name}_FILE")
    if file_path:
        path = Path(file_path)
        if not path.is_file():
            raise RuntimeError(f"Configured secret file does not exist: {path}")
        return path.read_text(encoding="utf-8").strip()
    return os.getenv(name)


@dataclass(frozen=True)
class Settings:
    project_root: Path = Path(__file__).resolve().parents[1]
    docs_dir: Path = project_root / "Docs"
    pinecone_api_key: Optional[str] = secret("PINECONE_API_KEY")
    pinecone_environment: Optional[str] = os.getenv("PINECONE_ENVIRONMENT")
    pinecone_index_name: str = os.getenv("PINECONE_INDEX_NAME", "abc-enterprise-rag")
    nebius_api_key: Optional[str] = secret("NEBIUS_API_KEY")
    nebius_base_url: str = os.getenv("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/")
    nebius_model: str = os.getenv("NEBIUS_MODEL", "meta-llama/Llama-3.3-70B-Instruct")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    database_path: Path = Path(os.getenv("RAG_DATABASE_PATH", str(project_root / "data" / "rag.db")))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))
    max_question_length: int = int(os.getenv("MAX_QUESTION_LENGTH", "2000"))

    @property
    def has_nebius(self) -> bool:
        return bool(self.nebius_api_key)

    @property
    def has_pinecone(self) -> bool:
        return bool(self.pinecone_api_key)

SETTINGS = Settings()
