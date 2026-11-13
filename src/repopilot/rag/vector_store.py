"""Dense vector storage and retrieval powered by Qdrant and FastEmbed."""

from __future__ import annotations

import uuid

from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from repopilot.rag.models import CodeChunk, ScoredChunk


class QdrantVectorStore:
    """Manages dense semantic vector search for AST code chunks."""

    COLLECTION_NAME = "repopilot_code_chunks"
    VECTOR_DIM = 384  # BAAI/bge-small-en-v1.5 dimension

    def __init__(
        self,
        location: str = ":memory:",
        embedding_model_name: str = "BAAI/bge-small-en-v1.5",
    ) -> None:
        self.location = location
        self.client = QdrantClient(location=location)
        self.embedding_model = TextEmbedding(model_name=embedding_model_name)
        self._chunks_by_id: dict[str, CodeChunk] = {}
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """Create the Qdrant collection if it does not already exist."""
        collections = self.client.get_collections().collections
        exists = any(c.name == self.COLLECTION_NAME for c in collections)
        if not exists:
            self.client.create_collection(
                collection_name=self.COLLECTION_NAME,
                vectors_config=VectorParams(size=self.VECTOR_DIM, distance=Distance.COSINE),
            )

    def add_chunks(self, chunks: list[CodeChunk]) -> None:
        """Embed and upsert code chunks into Qdrant."""
        if not chunks:
            return

        texts = [chunk.to_searchable_text() for chunk in chunks]
        embeddings = list(self.embedding_model.embed(texts))

        points: list[PointStruct] = []
        for chunk, emb in zip(chunks, embeddings, strict=True):
            self._chunks_by_id[chunk.chunk_id] = chunk
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk.chunk_id))
            payload = {
                "chunk_id": chunk.chunk_id,
                "file_path": chunk.file_path,
                "symbol_id": chunk.symbol_id,
                "symbol_type": chunk.symbol_type,
            }
            points.append(
                PointStruct(
                    id=point_id,
                    vector=emb.tolist(),
                    payload=payload,
                )
            )

        self.client.upsert(collection_name=self.COLLECTION_NAME, points=points)

    def search(
        self, query: str, limit: int = 10, file_filter: str | None = None
    ) -> list[ScoredChunk]:
        """Perform dense semantic vector search."""
        query_embeddings = list(self.embedding_model.embed([query]))
        if not query_embeddings:
            return []

        query_vector = query_embeddings[0].tolist()
        query_filter: Filter | None = None
        if file_filter:
            query_filter = Filter(
                must=[FieldCondition(key="file_path", match=MatchValue(value=file_filter))]
            )

        search_results = self.client.query_points(
            collection_name=self.COLLECTION_NAME,
            query=query_vector,
            query_filter=query_filter,
            limit=limit,
        ).points

        scored_chunks: list[ScoredChunk] = []
        for scored_point in search_results:
            if scored_point.payload and "chunk_id" in scored_point.payload:
                cid = str(scored_point.payload["chunk_id"])
                if cid in self._chunks_by_id:
                    scored_chunks.append(
                        ScoredChunk(
                            chunk=self._chunks_by_id[cid],
                            score=float(scored_point.score),
                            source="dense",
                        )
                    )

        return scored_chunks

    def count(self) -> int:
        """Return the count of indexed points in the collection."""
        res = self.client.get_collection(self.COLLECTION_NAME)
        return int(res.points_count or 0)

    def clear(self) -> None:
        """Reset and recreate the collection."""
        self.client.delete_collection(self.COLLECTION_NAME)
        self._chunks_by_id.clear()
        self._ensure_collection()
