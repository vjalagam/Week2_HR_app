from __future__ import annotations

from typing import List, Optional

from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec

from .config import SETTINGS


class LocalFallbackIndex:
    def __init__(self, docs: Optional[List[Document]] = None):
        self.docs = docs or []

    def add_documents(self, docs: List[Document]):
        self.docs.extend(docs)

    def similarity_search(self, query: str, k: int = 5, namespace: str = "general") -> List[Document]:
        scored: List[tuple[float, Document]] = []
        q = query.lower().split()
        for doc in self.docs:
            if namespace != "general" and doc.metadata.get("namespace") != namespace:
                continue
            text = doc.page_content.lower()
            score = sum(1 for term in q if term in text)
            if score:
                scored.append((score, doc))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [doc for _, doc in scored[:k]]


def build_embeddings():
    return HuggingFaceEmbeddings(
        model_name=SETTINGS.embedding_model,
        model_kwargs={"trust_remote_code": True},
        encode_kwargs={"normalize_embeddings": True, "clean_up_tokenization_spaces": True}
    )


def init_vector_index(docs: List[Document]):
    if SETTINGS.has_pinecone:
        try:
            pc = Pinecone(api_key=SETTINGS.pinecone_api_key, environment=SETTINGS.pinecone_environment)
            index_name = SETTINGS.pinecone_index_name
            indexes = [entry["name"] for entry in pc.list_indexes().get("indexes", [])]
            if index_name not in indexes:
                pc.create_index(
                    name=index_name,
                    dimension=384,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region=SETTINGS.pinecone_environment),
                )
            vector_store = PineconeVectorStore.from_documents(
                documents=docs,
                embedding=build_embeddings(),
                index_name=index_name,
                namespace="enterprise",
            )
            return vector_store
        except Exception:
            pass
    return LocalFallbackIndex(docs)


def search_documents(query: str, namespace: str, docs: List[Document], k: int = 5):
    if SETTINGS.has_pinecone:
        try:
            vector_store = PineconeVectorStore.from_existing_index(
                index_name=SETTINGS.pinecone_index_name,
                embedding=build_embeddings(),
                namespace=namespace,
            )
            result = vector_store.similarity_search(query, k=k, namespace=namespace)
            if result:
                return result
        except Exception as e:
            # Fall back to local if Pinecone fails
            pass
    
    # Use local fallback
    fallback = LocalFallbackIndex(docs)
    return fallback.similarity_search(query, k=k, namespace=namespace)
