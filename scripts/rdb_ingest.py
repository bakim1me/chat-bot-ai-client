import argparse

from app.core.config import settings
from app.core.logger import get_logger
from app.core.weaviate_client import create_client
from app.data.ingestion import IngestionPipeline
from app.services.db_service import DBService
from app.services.embedding_service import EmbeddingService
from app.services.vector_store_service import VectorStoreService

log = get_logger(__name__)

def main() -> None:

    log.info("=" * 60)
    log.info(f"  RAG 데이터 생성 파이프라인 \n  소스       : RDB - DSDO")
    log.info("=" * 60)

    embedding_service = EmbeddingService(model_name=settings.EMBEDDING_MODEL)

    # parser = argparse.ArgumentParser(
    #     description="RAG RDB 데이터 인제스트 CLI",
    #     formatter_class=argparse.RawDescriptionHelpFormatter,
    # )
    # parser.add_argument(
    #     "--table", type=str, default="all",
    #     help="추가할 RDB 테이블",
    # )
    # parser.add_argument(
    #     "--chunk-size", type=int, default=settings.CHUNK_SIZE,
    #     help=f"청크 최대 문자 수 (기본값: {settings.CHUNK_SIZE})",
    # )
    # parser.add_argument(
    #     "--chunk-overlap", type=int, default=settings.CHUNK_OVERLAP,
    #     help=f"청크 간 오버랩 문자 수 (기본값: {settings.CHUNK_OVERLAP})",
    # )
    # parser.add_argument(
    #     "--collection", default=settings.WEAVIATE_COLLECTION,
    #     help=f"Weaviate 컬렉션명 (기본값: {settings.WEAVIATE_COLLECTION})",
    # )
    # parser.add_argument(
    #     "--keywords", type=str, default=None,
    #     help="등록 파일별 추가할 키워드 ,로 분리하여 입력",
    # )
    # parser.add_argument(
    #     "--no-cache", action="store_true",
    #     help="청킹 캐시를 무시하고 재처리",
    # )
    # args = parser.parse_args()
    args = None

    client = create_client()
    collection = args.collection if args else settings.WEAVIATE_COLLECTION
    chunk_size = args.chunk_size if args else settings.CHUNK_SIZE
    chunk_overlap = args.chunk_overlap if args else settings.CHUNK_OVERLAP
    table = args.table if args else "ox"
    keywords = args.keywords.split(",") if args and args.keywords else None

    try:
        vector_store = VectorStoreService(
            client=client,
            embedding_service=embedding_service,
            collection_name=collection,
            vector_dim=settings.EMBEDDING_DIMENSION,
        )

        pipeline = IngestionPipeline(
            vector_store=vector_store,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        dbService = DBService()

        if "ox" in table or table == "all":
            result = pipeline.ingest_db_exam_oxs(dbService, keywords)
            log.info(f"  ✅ Target Table [oxs]: {result}개 청크 삽입")

        if "faq" in table or table == "all":
            result = pipeline.ingest_db_faqs(dbService, keywords)
            log.info(f"  ✅ Target Table [faq]: {result}개 청크 삽입")

        if "ipsi" in table or table == "all":
            result = pipeline.ingest_db_ipsis(dbService, keywords)
            log.info(f"  ✅ Target Table [ipsi]: {result}개 청크 삽입")

        if "notice" in table or table == "all" :
            result = pipeline.ingest_db_notices(dbService, keywords)
            log.info(f"  ✅ Target Table [notice]: {result}개 청크 삽입")

    finally:
        client.close()

if __name__ == "__main__" :
    main()
