"""
RAG 채팅 라우터 —  검색 + 생성

POST /api/v1/chat/   → RAGService.query() 실행
GET  /api/v1/chat/health → 헬스체크
"""
from fastapi import APIRouter

from app.core.dependencies import GeminiClient, VectorStoreDep, HistoryDep
from app.core.logger import get_logger
from app.schemas.chat import ChatRequest, ChatResponse, RetrievedChunkSchema
from app.services.gemini_service import GeminiService
from app.services.rag_service import RAGService

router = APIRouter(prefix="/chat", tags=["Chat — RAG"])
log = get_logger(__name__)
@router.post(
    "/",
    response_model=ChatResponse,
    summary="RAG 채팅",
    description=(
        "질문을 KR-SBERT로 임베딩 후 Weaviate에서 유사 청크를 검색합니다.  \n"
        "검색된 컨텍스트를 Gemini에 전달해 정확한 답변을 생성합니다.  \n\n"
        "문서를 먼저 `/api/v1/documents/ingest`로 업로드해야 합니다."
    ),
)
async def chat(
    body: ChatRequest,
    gemini_client: GeminiClient,
    vector_store: VectorStoreDep,
    history_service: HistoryDep,
    use_llm: bool = False,
) -> ChatResponse:
    gemini_service = GeminiService(model=gemini_client, history_service=history_service) if use_llm else None
    rag = RAGService(
        vector_store=vector_store,
        gemini_service=gemini_service,
        top_k=body.top_k,
        score_threshold=body.score_threshold,
    )

    result = await rag.query(
        question=body.question,
        alpha=body.alpha,
    )

    log.info(f"  📝 질문: {body.question}")
    log.info(f"  🔍 검색된 청크 수: {result['chunks_found']}")

    result['retrieved_chunks'] =  [
            RetrievedChunkSchema(
                chunk_id=c.chunk_id,
                source=c.source,
                text=c.text,
                chunk_index=c.chunk_index,
                score=c.score,
            )
            for c in result["retrieved_chunks"]
        ]

    return ChatResponse(
        **result
    )


@router.get(
    "/health",
    summary="헬스체크",
    description="채팅 라우터 동작 확인용 엔드포인트",
)
async def health():
    return {"status": "ok", "router": "chat"}
