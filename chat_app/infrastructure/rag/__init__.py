"""RAG building blocks: loading, chunking, embeddings, storage and retrieval."""

from chat_app.infrastructure.rag.chunking import (
    DEFAULT_CHUNK_TOKENS,
    DEFAULT_OVERLAP_RATIO,
    chunk_text,
    estimate_tokens,
)
from chat_app.infrastructure.rag.embeddings import EmbeddingError, OpenAIEmbedder
from chat_app.infrastructure.rag.ingestion import ingest_directory
from chat_app.infrastructure.rag.loaders import (
    UnsupportedDocumentError,
    classify_documents,
    discover_documents,
    load_document,
)
from chat_app.infrastructure.rag.retriever import KnowledgeBaseRetriever
from chat_app.infrastructure.rag.vector_store import SupabaseVectorStore, VectorStoreError

__all__ = [
    "DEFAULT_CHUNK_TOKENS",
    "DEFAULT_OVERLAP_RATIO",
    "EmbeddingError",
    "KnowledgeBaseRetriever",
    "OpenAIEmbedder",
    "SupabaseVectorStore",
    "UnsupportedDocumentError",
    "VectorStoreError",
    "chunk_text",
    "classify_documents",
    "discover_documents",
    "estimate_tokens",
    "ingest_directory",
    "load_document",
]
