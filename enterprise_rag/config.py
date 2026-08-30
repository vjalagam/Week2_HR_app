import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


@dataclass(frozen=True)
class Settings:
    project_root: Path = Path(__file__).resolve().parents[1]
    docs_dir: Path = project_root / "Docs"
    pinecone_api_key: Optional[str] = os.getenv("PINECONE_API_KEY")
    pinecone_environment: Optional[str] = os.getenv("PINECONE_ENVIRONMENT")
    pinecone_index_name: str = os.getenv("PINECONE_INDEX_NAME", "acme-enterprise-rag")
    nebius_api_key: Optional[str] = os.getenv("NEBIUS_API_KEY")
    nebius_base_url: str = os.getenv("NEBIUS_BASE_URL", "https://api.studio.nebius.ai/v1")
    nebius_model: str = os.getenv("NEBIUS_MODEL", "Qwen/Qwen2.5-72B-Instruct")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

    @property
    def has_nebius(self) -> bool:
        return bool(self.nebius_api_key)

    @property
    def has_pinecone(self) -> bool:
        return bool(self.pinecone_api_key and self.pinecone_environment)


SETTINGS = Settings()
