from __future__ import annotations

from pathlib import Path
from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .config import SETTINGS


def load_document_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_enterprise_documents(docs_dir: Path | None = None) -> List[Document]:
    docs_dir = docs_dir or SETTINGS.docs_dir
    documents: List[Document] = []
    for path in sorted(docs_dir.glob("*.txt")):
        text = load_document_text(path)
        documents.append(Document(page_content=text, metadata={"source": str(path.name), "namespace": infer_namespace(path.name)}))
    return documents


def infer_namespace(filename: str) -> str:
    lower = filename.lower()
    if "hr" in lower or "policy" in lower:
        return "hr"
    if "tech" in lower or "technical" in lower:
        return "technical"
    if "compliance" in lower or "security" in lower:
        return "compliance"
    return "general"


def chunk_documents(documents: List[Document], chunk_size: int = 700, chunk_overlap: int = 150) -> List[Document]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap, separators=["\n\n", "\n", ". ", " "])
    chunks: List[Document] = []
    for doc in documents:
        split_chunks = splitter.split_documents([doc])
        for chunk in split_chunks:
            chunk.metadata["namespace"] = doc.metadata.get("namespace", "general")
            chunks.append(chunk)
    return chunks
