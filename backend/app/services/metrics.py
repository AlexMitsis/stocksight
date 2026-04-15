"""
Prometheus metrics for RAG performance monitoring.

This module defines metrics for tracking pgvector RAG retrieval and storage performance.
"""

from prometheus_client import Counter, Histogram, Gauge

# ============================================================
# RAG / pgvector Metrics
# ============================================================

# pgvector retrieval performance
rag_retrieval_duration = Histogram(
    'rag_pgvector_retrieval_duration_seconds',
    'Time spent retrieving context from pgvector',
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

rag_chunks_retrieved = Histogram(
    'rag_chunks_retrieved',
    'Number of context chunks retrieved from pgvector',
    buckets=[0, 1, 3, 5, 10, 20]
)

rag_relevance_score = Histogram(
    'rag_relevance_score',
    'Average cosine similarity score of retrieved chunks',
    buckets=[0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0]
)

rag_token_savings = Gauge(
    'rag_token_savings_ratio',
    'Token savings ratio (0-1) compared to full history'
)

rag_storage_duration = Histogram(
    'rag_storage_duration_seconds',
    'Time spent storing embeddings in PostgreSQL',
    buckets=[0.05, 0.1, 0.2, 0.5, 1.0, 2.0]
)

rag_storage_errors = Counter(
    'rag_storage_errors_total',
    'Total context storage failures'
)

rag_storage_success = Counter(
    'rag_storage_success_total',
    'Total successful context storage operations'
)
