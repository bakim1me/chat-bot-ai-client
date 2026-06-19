"""

"""
from __future__ import annotations

import time
from typing import Dict, List, Optional

from app.core.config import settings
from app.core.logger import get_logger
from app.services.gemini_service import GeminiService
from app.services.vector_store_service import RetrievedChunk, VectorStoreService

log = get_logger(__name__)

class RAGService:
    """
    RAG 파이프라인
    RAGService가 검색(Retrieval) -> 생성(Generation) 실행
    """

    def __init__(
        self,
        vector_store: VectorStoreService,
        gemini_service: GeminiService | None,
        top_k: int = settings.RAG_TOP_K,
        score_threshold: float = settings.RAG_SCORE_THRESHOLD,
    ):
        self.vector_store = vector_store
        self.gemini_service = gemini_service
        self.top_k = top_k
        self.score_threshold = score_threshold

    async def query(
        self,
        question: str,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
        alpha: float = 0.5,
    ) -> Dict:
        """
        질문 → 검색 → 생성 전체 실행.

        Args:
            question:            사용자 질문 텍스트
            top_k:               검색할 최대 청크 수 (None이면 기본값 사용)
            score_threshold:     유사도 임계값 (None이면 기본값 사용)
            alpha:               하이브리드 검색 가중치

        Returns:
            {
                "answer":           str,                  # 생성된 답변
                "retrieved_chunks": List[RetrievedChunk], # 검색된 청크
                "model":            str,                  # LLM 모델명
                "chunks_found":     int,                  # 검색된 청크 수
            }
        """
        rag_start_time = time.perf_counter()
        
        k = top_k if top_k is not None else self.top_k
        threshold = score_threshold if score_threshold is not None else self.score_threshold

        # ── Retrieval ────────────────────────────────────
        log.info(f"\n검색 시작 | 질문: '{question[:50]}...' | top_k={k}")
        retrieved: List[RetrievedChunk] = self.vector_store.search(
            query=question,
            top_k=k,
            score_threshold=threshold,
            alpha=alpha,
        )
        
        # 검색 결과에 전체 텍스트(parent_text) 항목 사용 예쩡. chunk의 중복 source 제거 및 부모 문서 치환
        seen_sources = set()
        dedup_retrieved: List[RetrievedChunk] = []

        for chunk in retrieved:
            if chunk.source not in seen_sources:
                seen_sources.add(chunk.source)
                if chunk.parent_content:
                    chunk.text = chunk.parent_content
                dedup_retrieved.append(chunk)

        log.info(f"{len(retrieved)}개 중 {len(dedup_retrieved)}개(중복제거) 청크 검색됨")

        # ── Generation ───────────────────────────────────
        answer = ""
        if self.gemini_service:
            log.info(f"Gemini 답변 생성 중 ({settings.GEMINI_MODEL})...")
            answer = await self.gemini_service.generate_with_context(
                question=question,
                chunks=dedup_retrieved,
                rag_start_time=rag_start_time,
            )
            log.info(f"생성 완료 ({len(answer)}자)")

        return {
            "question": question,
            "answer": answer,
            "retrieved_chunks": dedup_retrieved,
            "model": settings.GEMINI_MODEL,
            "chunks_found": len(dedup_retrieved),
        }
