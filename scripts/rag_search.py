"""
E2E RAG 파이프라인 테스트 스크립트

전체 플로우가 정상적으로 동작하는지 확인합니다.
사전에 문서를 인제스트 해두지 않아도, 이 스크립트가 임시 파일을 생성하여 전체 과정을 테스트합니다.
"""
import argparse
import asyncio
import sys

from app.core.logger import get_logger
log = get_logger(__name__)
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google import generativeai as genai

from app.core.config import settings
from app.core.weaviate_client import create_client
from app.services.embedding_service import EmbeddingService
from app.services.gemini_service import GeminiService
from app.services.rag_service import RAGService
from app.services.vector_store_service import VectorStoreService

async def main():
    # parser = argparse.ArgumentParser(
    #     description="RAG Search CLI",
    #     formatter_class=argparse.RawDescriptionHelpFormatter,
    # )
    # parser.add_argument(
    #     "--q", type=str, required=True,
    #     help="질문",
    # )
    #
    # parser.add_argument(
    #     "--size", type=int, default=settings.RAG_TOP_K,
    #     help=f"최대 검색 결과 수 (기본값: {settings.CHUNK_SIZE})",
    # )
    #
    # parser.add_argument(
    #     "--thresh", type=float, default=settings.RAG_SCORE_THRESHOLD,
    #     help=f"점수 최저점 (기본값: {settings.RAG_SCORE_THRESHOLD})",
    # )

    log.info("=" * 60)
    log.info("  RAG Search 테스트 시작")
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

    # args = parser.parse_args()
    args = None
    try:
        top_k = args.size if args else 5
        thresh = args.thresh if args else 0.5
        # 테스트용 임시 컬렉션 사용
        collection = "Documents"
        
        vector_store = VectorStoreService(
            client=client,
            embedding_service=embedding_service,
            collection_name=collection,
            vector_dim=settings.EMBEDDING_DIMENSION,
        )
        
        rag_service = RAGService(
            vector_store=vector_store,
            gemini_service=gemini_service,
            top_k=top_k,
            # score_threshold=thresh,
        )

        # ── Ingestion ──────────────────────────────────────────
        log.info("[테스트 1] RAG 검색 및 생성")
        question = args.q if args else "Q: 모의고사 4월 문제 오류"
        
        if not settings.GEMINI_API_KEY:
            log.warning("GEMINI_API_KEY가 설정되지 않아 LLM 처리를 생략합니다.")
            log.warning("검색까지만 테스트합니다.")
            retrieved = vector_store.search(question, top_k=top_k)
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
