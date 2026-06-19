from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import weaviate
from weaviate.classes.config import (
    Configure,
    DataType,
    Property,
    VectorDistances,
)
from weaviate.classes.query import MetadataQuery

from app.core.logger import get_logger
from app.schemas.RawDocument import RawDocument
from app.services.embedding_service import EmbeddingService

log = get_logger(__name__)

@dataclass
class RetrievedChunk:
    """검색 결과 단일 청크"""
    chunk_id: str
    source: str
    text: str
    chunk_index: int
    score: float        # certainty (코사인 유사도, 0~1)
    parent_content: str = ""

class VectorStoreService:
    """
    Weaviate v4 클라이언트 래퍼.

    - 컬렉션 자동 생성 (없을 경우)
    - 배치 삽입 (insert_chunks)
    -  near_vector 유사도 검색 (search)
    """

    def __init__(
        self,
        client: weaviate.WeaviateClient,
        embedding_service: EmbeddingService | None,
        collection_name: str = "Documents",
        vector_dim: int = 768,
    ):
        self.client = client
        self.embedding_service = embedding_service
        self.collection_name = collection_name
        self.vector_dim = vector_dim
        self.ensure_collection()

    def ensure_collection(self) -> None:
        """컬렉션이 없으면 KR-SBERT 스펙에 맞게 자동 생성"""
        if self.client.collections.exists(self.collection_name):
            log.info(f"[VectorStore] 기존 컬렉션 사용: '{self.collection_name}'")
            return

        self.client.collections.create(
            name=self.collection_name,
            # 프로퍼티 정의 (Weaviate 스키마)
            properties=[
                Property(name="chunk_id",    data_type=DataType.TEXT),
                Property(name="source",      data_type=DataType.TEXT),
                Property(name="text",        data_type=DataType.TEXT),
                Property(name="chunk_index", data_type=DataType.INT),
                Property(name="keywords",    data_type=DataType.TEXT_ARRAY),
                Property(name="parent_content", data_type=DataType.TEXT, index_searchable=False, index_filterable=False),
            ],
            vector_config=Configure.Vectors.text2vec_huggingface(
                name="default",
                source_properties=["title", "body"],
                vector_index_config=Configure.VectorIndex.hnsw(
                    # HNSW 인덱스 + 코사인 거리 (KR-SBERT L2 정규화와 일치)
                    distance_metric=VectorDistances.COSINE,
                    ef_construction=300
                ),
                vectorize_collection_name=True
            )
        )
        log.info(f"[VectorStore] 컬렉션 생성 완료: '{self.collection_name}' (dim={self.vector_dim})")


    def list_collections(self) -> List[str]:
        """존재하는 컬렉션 이름 목록 반환"""
        return list(self.client.collections.list_all().keys())

    def delete_collection(self, collection_name: str) -> bool:
        """
        컬렉션 삭제
        Args:
            collection_name: 컬렉션 이름
        Returns:
            성공 시 True, 없으면 False
        """
        if not self.client.collections.exists(collection_name):
            return False
        self.client.collections.delete(collection_name)
        log.info(f"[VectorStore] 컬렉션 삭제: '{collection_name}'")
        return True

    def get_count(self, collection_name: Optional[str] = None) -> int:
        """
        컬렉션 내 오브젝트(청크) 수 반환
        Args:
            collection_name: 컬렉션 이름
        Returns:
            오브젝트(청크) 수
        """
        col_name = collection_name or self.collection_name
        col = self.client.collections.get(col_name)
        agg = col.aggregate.over_all(total_count=True)
        return agg.total_count or 0


    def insert_chunks(self, chunks: List[RawDocument]) -> int:
        """
        청크 삽입 (insert_chunks)
        TextChunk 리스트를 KR-SBERT로 임베딩 후 Weaviate에 배치 삽입.

        Args:
            chunks: app.data.preprocessor.TextChunk 리스트

        Returns:
            삽입된 청크 수
        """
        if not chunks:
            return 0

        collection = self.client.collections.get(self.collection_name)

        # 배치 임베딩 (GPU/CPU 자동)
        texts = [c.content for c in chunks]
        log.info(f"[VectorStore] {len(texts)}개 청크 임베딩 중...")
        vectors = self.embedding_service.encode_batch(texts, show_progress=True)

        # Weaviate 배치 삽입
        inserted = 0
        with collection.batch.dynamic() as batch:
            for chunk, vector in zip(chunks, vectors):
                batch.add_object(
                    properties={
                        "chunk_id":    chunk.chunk_id,
                        "source_type": chunk.source_type,
                        "source":      chunk.source_id,
                        "text":        chunk.content,
                        "chunk_index": chunk.metadata.get('chunk_index', 0),
                        "keywords":    chunk.keywords,
                        "parent_content": chunk.parent_content,
                    },
                    vector=vector,
                )
                inserted += 1

        log.info(f"[VectorStore] 삽입 완료: {inserted}개")
        return inserted

    def search(
        self,
        query: str,
        top_k: int = 4,
        score_threshold: float = 0.6,
        collection_name: Optional[str] = None,
        alpha: float = 0.5,
    ) -> List[RetrievedChunk]:
        """
        쿼리 텍스트를 KR-SBERT로 임베딩 후 hybrid 검색.

        Args:
            query:                검색 질문 텍스트
            top_k:                반환할 최대 청크 수
            score_threshold:      최소 유사도 (이 값 미만은 필터링)
            collection_name:      검색할 컬렉션명 (기본값: 설정값)
            alpha:                하이브리드 가중치 (0: 순수키워드, 1: 순수벡터)

        Returns:
            유사도 내림차순 RetrievedChunk 리스트
        """
        col_name = collection_name or self.collection_name

        # 쿼리 임베딩 (단일 인코딩)
        query_vector = self.embedding_service.encode(query)

        collection = self.client.collections.get(col_name)
        response = collection.query.hybrid(
            query=query,
            vector=query_vector,
            alpha=alpha,
            limit=top_k,
            query_properties=["text", "keywords^2"],
            return_metadata=MetadataQuery(score=True, distance=True),
        )

        results: List[RetrievedChunk] = []
        for obj in response.objects:
            score = obj.metadata.score or 0.0

            # 임계값 미만 필터링
            if score < score_threshold:
                continue

            props = obj.properties
            results.append(RetrievedChunk(
                chunk_id=str(props.get("chunk_id", "")),
                source=str(props.get("source", "")),
                text=str(props.get("text", "")),
                chunk_index=int(props.get("chunk_index", 0)),
                score=round(score, 4),
                parent_content=str(props.get("parent_content", "")),
            ))

        log.info(f"[VectorStore] 검색 완료: {len(results)}/{top_k}개 반환 (임계값={score_threshold})")
        return results
