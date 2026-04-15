#!/usr/bin/env python3
"""
IVFFlat Index Tuning Script for pgvector

This script helps tune the IVFFlat index parameters based on dataset size.

Rule of thumb: lists = sqrt(rows)
- 1,000 embeddings → lists = 32
- 10,000 embeddings → lists = 100
- 100,000 embeddings → lists = 316
- 1,000,000 embeddings → lists = 1000

Usage:
    python scripts/tune_ivfflat_index.py --analyze
    python scripts/tune_ivfflat_index.py --rebuild --lists 100
"""

import argparse
import asyncio
import math
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


def get_db_url():
    """Get database URL from settings."""
    return settings.DATABASE_URL


async def analyze_index(engine):
    """Analyze current index status and recommend optimal lists parameter."""

    with engine.connect() as conn:
        # Get current row count
        result = conn.execute(text(
            "SELECT COUNT(*) FROM conversation_embeddings"
        ))
        row_count = result.scalar()

        print(f"\n📊 Current Dataset Size: {row_count:,} embeddings\n")

        # Calculate optimal lists parameter
        optimal_lists = int(math.sqrt(row_count)) if row_count > 0 else 1

        # Get current index info
        result = conn.execute(text("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'conversation_embeddings'
            AND indexname LIKE '%embedding%'
        """))

        current_indexes = result.fetchall()

        if current_indexes:
            print("📋 Current Indexes:")
            for idx in current_indexes:
                print(f"  - {idx[0]}")
                print(f"    {idx[1]}\n")
        else:
            print("⚠️  No vector index found!\n")

        # Provide recommendations
        print("💡 Recommendations:")
        print(f"  - Optimal lists parameter: {optimal_lists}")

        if row_count < 1000:
            print(f"  - Current dataset is small ({row_count} rows)")
            print(f"  - Recommended lists: 32")
            print(f"  - Index rebuild not urgent")
        elif row_count < 10000:
            print(f"  - Current dataset is medium ({row_count} rows)")
            print(f"  - Recommended lists: 100")
            if row_count > 1000:
                print(f"  - Consider rebuilding index")
        elif row_count < 100000:
            print(f"  - Current dataset is large ({row_count} rows)")
            print(f"  - Recommended lists: {optimal_lists}")
            print(f"  - Rebuild index for optimal performance")
        else:
            print(f"  - Current dataset is very large ({row_count} rows)")
            print(f"  - Recommended lists: {optimal_lists}")
            print(f"  - Index rebuild strongly recommended")
            print(f"  - Consider migrating to Pinecone for better performance")

        # Check index size
        result = conn.execute(text("""
            SELECT
                pg_size_pretty(pg_relation_size('idx_conversation_embeddings_embedding')) as index_size,
                pg_size_pretty(pg_relation_size('conversation_embeddings')) as table_size
        """))

        sizes = result.fetchone()
        if sizes:
            print(f"\n📦 Storage:")
            print(f"  - Table size: {sizes[1]}")
            print(f"  - Index size: {sizes[0]}")

        print()


async def rebuild_index(engine, lists: int):
    """Rebuild IVFFlat index with new lists parameter."""

    print(f"\n🔧 Rebuilding index with lists={lists}...\n")

    with engine.connect() as conn:
        # Drop existing index
        print("  1. Dropping old index...")
        conn.execute(text(
            "DROP INDEX IF EXISTS idx_conversation_embeddings_embedding;"
        ))
        conn.commit()

        # Create new index
        print(f"  2. Creating new index with lists={lists}...")
        conn.execute(text(f"""
            CREATE INDEX idx_conversation_embeddings_embedding
            ON conversation_embeddings
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = {lists});
        """))
        conn.commit()

        # Analyze the table for query planner
        print("  3. Analyzing table for query planner...")
        conn.execute(text("ANALYZE conversation_embeddings;"))
        conn.commit()

        print("\n✅ Index rebuilt successfully!\n")


async def benchmark_queries(engine, num_queries: int = 10):
    """Benchmark query performance with current index."""

    print(f"\n⚡ Running {num_queries} benchmark queries...\n")

    import time
    from app.services.embedding_service import get_embedding_service

    embedding_service = get_embedding_service()

    # Generate test query
    test_query = "What's Apple's stock price?"
    query_embedding = await embedding_service.generate_embedding(test_query)

    latencies = []

    with engine.connect() as conn:
        for i in range(num_queries):
            start = time.time()

            # Execute similarity search
            result = conn.execute(text("""
                SELECT
                    id,
                    thread_id,
                    content,
                    1 - (embedding <=> :query_embedding::vector) as similarity
                FROM conversation_embeddings
                WHERE thread_id = 'benchmark-thread'
                ORDER BY embedding <=> :query_embedding::vector
                LIMIT 5
            """), {"query_embedding": str(query_embedding)})

            results = result.fetchall()
            duration = time.time() - start
            latencies.append(duration * 1000)  # Convert to ms

    if latencies:
        latencies.sort()
        avg = sum(latencies) / len(latencies)
        p50 = latencies[len(latencies) // 2]
        p95 = latencies[int(len(latencies) * 0.95)]

        print(f"📈 Query Performance:")
        print(f"  - Average: {avg:.1f}ms")
        print(f"  - p50: {p50:.1f}ms")
        print(f"  - p95: {p95:.1f}ms")

        if p95 < 100:
            print(f"  ✅ Performance is excellent (<100ms)")
        elif p95 < 200:
            print(f"  ⚠️  Performance is acceptable (<200ms)")
        else:
            print(f"  ❌ Performance needs improvement (>200ms)")

        print()


def main():
    parser = argparse.ArgumentParser(
        description="Tune IVFFlat index for pgvector RAG"
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Analyze current index and provide recommendations"
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Rebuild index with specified lists parameter"
    )
    parser.add_argument(
        "--lists",
        type=int,
        help="Lists parameter for IVFFlat index (used with --rebuild)"
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Benchmark query performance"
    )

    args = parser.parse_args()

    # Create database engine
    engine = create_engine(get_db_url())

    if args.analyze:
        asyncio.run(analyze_index(engine))

    if args.rebuild:
        if not args.lists:
            print("Error: --lists parameter required with --rebuild")
            return
        asyncio.run(rebuild_index(engine, args.lists))

    if args.benchmark:
        asyncio.run(benchmark_queries(engine))

    if not any([args.analyze, args.rebuild, args.benchmark]):
        parser.print_help()


if __name__ == "__main__":
    main()
