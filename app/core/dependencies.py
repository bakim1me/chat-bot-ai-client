from functools import lru_cache
from typing import Annotated, Generator

import weaviate
from fastapi import Depends
from sqlalchemy.orm import Session
from google import generativeai as genai

from app.core.config import settings
from app.core.weaviate_client import create_client
from app.services.embedding_service import EmbeddingService
from app.services.vector_store_service import VectorStoreService
from app.services.history_service import HistoryService
from app.services.db_service import DBService
from app.db.mariadb import SessionLocal


# ── Gemini ────────────────────────────────────────────────────────────────────

def get_gemini_client() -> genai.GenerativeModel:
    """Gemini GenerativeModel 인스턴스를 반환하는 DI 함수"""
    genai.configure(api_key=settings.GEMINI_API_KEY)
    return genai.GenerativeModel(model_name=settings.GEMINI_MODEL)


GeminiClient = Annotated[genai.GenerativeModel, Depends(get_gemini_client)]


# ── Embedding (싱글턴: 모델 로드 비용이 크므로 캐싱) ─────────────────────────

@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    """
    KR-SBERT 임베딩 서비스 싱글턴
    앱 생애주기 동안 1번만 로드
    """
    return EmbeddingService(model_name=settings.EMBEDDING_MODEL)


EmbeddingDep = Annotated[EmbeddingService, Depends(get_embedding_service)]


# ── Weaviate Client ───────────────────────────────────────────────────────────

def get_weaviate_client() -> Generator[weaviate.WeaviateClient, None, None]:
    """
    Weaviate 클라이언트 연결 관리
    """
    client = create_client()
    try:
        yield client
    finally:
        client.close()


WeaviateClientDep = Annotated[weaviate.WeaviateClient, Depends(get_weaviate_client)]


# ── VectorStore (Weaviate + Embedding 합성 DI) ───────────────────────────────

def get_vector_store(
    client: WeaviateClientDep,
    embedding_service: EmbeddingDep,
) -> VectorStoreService:
    return VectorStoreService(
        client=client,
        embedding_service=embedding_service,
        collection_name=settings.WEAVIATE_COLLECTION,
        vector_dim=settings.EMBEDDING_DIMENSION,
    )


VectorStoreDep = Annotated[VectorStoreService, Depends(get_vector_store)]


# ── History Service ────────────────────────────────────────────────────────────

def get_history_service() -> HistoryService:
    return HistoryService()


HistoryDep = Annotated[HistoryService, Depends(get_history_service)]


# ── RDB Service ───────────────────────────────────────────────────────────────

def get_db() -> Generator[Session, None, None]:
    """RDB 세션(Session) 라이프사이클 관리용 제너레이터"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DBDep = Annotated[Session, Depends(get_db)]


def get_db_service(db: DBDep) -> DBService:
    """DBService 의존성 주입 (싱글턴이 아닌 Request 스코프)"""
    return DBService(db=db)


DBServiceDep = Annotated[DBService, Depends(get_db_service)]
