"""
E2E RAG 파이프라인 테스트 스크립트

전체 플로우가 정상적으로 동작하는지 확인합니다.
사전에 문서를 인제스트 해두지 않아도, 이 스크립트가 임시 파일을 생성하여 전체 과정을 테스트합니다.
"""
import asyncio
import sys

from app.core.logger import get_logger
log = get_logger(__name__)
import tempfile
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google import generativeai as genai

from app.core.config import settings
from app.core.weaviate_client import create_client
from app.data.ingestion import IngestionPipeline
from app.services.embedding_service import EmbeddingService
from app.services.gemini_service import GeminiService
from app.services.rag_service import RAGService
from app.services.vector_store_service import VectorStoreService



async def main():
    # ── 테스트용 임시 문서 생성 ────────────────────────────────────────────────
    # test_text = (
    #     "FastAPI는 파이썬 3.8 이상을 위한 현대적이고 빠른 웹 프레임워크입니다. "
    #     "Starlette과 Pydantic을 기반으로 하며 비동기 프로그래밍을 완벽하게 지원합니다.\n\n"
    #     "RAG(Retrieval-Augmented Generation)는 대규모 언어 모델의 출력을 최적화하여 "
    #     "응답을 생성하기 전에 신뢰할 수 있는 지식 베이스를 참조하도록 하는 프로세스입니다.\n\n"
    #     "Weaviate는 머신러닝 모델의 데이터와 임베딩을 매끄럽게 저장하고 검색할 수 있는 "
    #     "오픈소스 벡터 데이터베이스입니다."
    # )
    #
    # with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as tmp:
    #     tmp.write(test_text)
    #     tmp_path = Path(tmp.name)

    tmp_path = "D:/Project/chat_bot_t/data/raw/상품 목록 제품 목록.txt"

    log.info("=" * 60)
    log.info("  RAG 파이프라인 E2E 테스트 시작")
    log.info("=" * 60)

    # ── 서비스 초기화 ────────────────────────────────────────────────────────
    log.info("[초기화] 서비스 객체 생성 중...")

    gemini_service = None

    if settings.GEMINI_API_KEY :
        genai.configure(api_key=settings.GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel(model_name=settings.GEMINI_MODEL)
        gemini_service = GeminiService(model=gemini_model)

    embedding_service = EmbeddingService(
        model_name=settings.EMBEDDING_MODEL,
        token=settings.HF_TOKEN
    )
    
    client = create_client()
    try:
        # 테스트용 임시 컬렉션 사용
        test_collection = "TestDocuments"
        
        vector_store = VectorStoreService(
            client=client,
            embedding_service=embedding_service,
            collection_name=test_collection,
            vector_dim=settings.EMBEDDING_DIMENSION,
        )
        
        # 기존 테스트 컬렉션 비우기
        vector_store.delete_collection(test_collection)
        vector_store.ensure_collection()

        pipeline = IngestionPipeline(
            vector_store=vector_store,
            chunk_size=100,      # 작은 크기로 쪼개어 여러 청크 생성 유도
            chunk_overlap=20,
        )

        rag_service = RAGService(
            vector_store=vector_store,
            gemini_service=gemini_service,
            top_k=2,
            score_threshold=0.5,
        )

        # ── Ingestion ──────────────────────────────────────────
        log.info("[테스트 1] 문서 인제스트")
        result = pipeline.ingest_file(tmp_path, use_cache=False)
        log.info(f"  ✅ 인제스트 완료: {result['chunks_created']}개 청크 생성, {result['chunks_inserted']}개 삽입")

        # ── RAG Query ──────────────────────────────────────────
        log.info("[테스트 2] RAG 검색 및 생성")
        question = "고 3 모의고사 추천해주세요."
        
        if not settings.GEMINI_API_KEY:
            log.warning("GEMINI_API_KEY가 설정되지 않아 LLM 생성을 생략합니다.")
            log.warning("검색까지만 테스트합니다.")
            retrieved = vector_store.search(question, top_k=5, score_threshold=0.25)
            log.info(f"  ✅ 검색 완료: {len(retrieved)}개 청크 찾음")
            for c in retrieved:
                log.info(f"    - [점수: {c.score:.4f}] {c.text}")
        else:
            rag_result = await rag_service.query(question)
            
            log.info(f"  📝 질문: {question}")
            log.info(f"  🔍 검색된 청크 수: {rag_result['chunks_found']}")
            for idx, chunk in enumerate(rag_result['retrieved_chunks'], 1):
                log.info(f"    [컨텍스트 {idx}] (점수: {chunk.score:.4f}) {chunk.text}")
                
            log.info(f"  🤖 Gemini 답변 ({rag_result['model']}):")
            log.info(f"  {rag_result['answer']}")

        log.info("✅ 모든 테스트가 성공적으로 완료되었습니다!")

    finally:
        # 정리
        client.close()
        # tmp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    asyncio.run(main())
