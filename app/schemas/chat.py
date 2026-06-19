from typing import List, Optional

from pydantic import BaseModel, Field


# ── 검색된 청크 (응답에 포함) ─────────────────────────────────────────────────

class RetrievedChunkSchema(BaseModel):
    """검색 결과 청크 스키마"""
    chunk_id: str   = Field(..., description="청크 고유 ID")
    source: str     = Field(..., description="PK 또는 파일명 (추후 업데이트/삭제 시 기준점)")
    text: str       = Field(..., description="청크 텍스트 내용")
    chunk_index: int = Field(..., description="청크 순번 (0-based)")
    score: float    = Field(..., description="코사인 유사도 점수 또는 하이브리드 스코어")


# ── Request ───────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """RAG 채팅 요청"""
    question: str = Field(
        ...,
        min_length=1,
        description="사용자 질문",
    )
    top_k: Optional[int] = Field(
        None,
        ge=1,
        le=10,
        description="검색할 청크 수 (1~10, 기본값: 서버 설정의 RAG_TOP_K)",
    )
    score_threshold: Optional[float] = Field(
        None,
        ge=0.0,
        description="최소 유사도 임계값 (기본값: 서버 설정의 RAG_CERTAINTY_THRESHOLD)",
    )
    alpha: Optional[float] = Field(
        0.5,
        ge=0.0,
        le=1.0,
        description="하이브리드 가중치 (0: 순수키워드, 1: 순수벡터)",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "question": "이 문서에서 설명하는 핵심 개념은 무엇인가요?",
                "top_k": 4,
                "score_threshold": 0.6,
                "alpha": 0.5,
            }
        }
    }


# ── Response ──────────────────────────────────────────────────────────────────

class ChatResponse(BaseModel):
    """RAG 채팅 응답"""
    question: str = Field(
        ...,
        description="사용자의 질문"
    )
    answer: str = Field(
        ...,
        description="Gemini가 생성한 답변 (검색된 컨텍스트 기반)",
    )
    model: str = Field(
        ...,
        description="사용된 LLM 모델명",
    )
    chunks_found: int = Field(
        ...,
        description="검색된 청크 수",
    )
    retrieved_chunks: List[RetrievedChunkSchema] = Field(
        default_factory=list,
        description="검색된 컨텍스트 청크 목록 (유사도 내림차순)",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "answer": "이 문서의 핵심 개념은 ...",
                "model": "gemini-2.0-flash",
                "chunks_found": 3,
                "retrieved_chunks": [
                    {
                        "chunk_id": "sample_doc_0",
                        "source": "sample_doc.txt",
                        "text": "청크 텍스트 내용...",
                        "chunk_index": 0,
                        "score": 0.8921,
                    }
                ],
            }
        }
    }
