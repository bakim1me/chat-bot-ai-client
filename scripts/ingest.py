"""
CLI 인제스트 스크립트

사용법:
  # 디렉토리 전체 인제스트
  python scripts/ingest.py --source data/raw/

  # 단일 파일 인제스트
  python scripts/ingest.py --source data/raw/my_doc.txt

  # 청킹 파라미터 조정
  python scripts/ingest.py --source data/raw/ --chunk-size 300 --chunk-overlap 30

  # 캐시 무시하고 재처리
  python scripts/ingest.py --source data/raw/ --no-cache
"""
import argparse
import sys

from app.core.logger import get_logger
log = get_logger(__name__)
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가 (스크립트 위치와 무관하게 임포트 가능)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.core.weaviate_client import create_client
from app.data.ingestion import IngestionPipeline
from app.services.embedding_service import EmbeddingService
from app.services.vector_store_service import VectorStoreService


def main() -> None:
    parser = argparse.ArgumentParser(
        description="RAG 문서 인제스트 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--source", required=True,
        help="인제스트할 파일 또는 디렉토리 경로", default='./raw/상품 목록 제품 목록.txt'
    )
    parser.add_argument(
        "--chunk-size", type=int, default=settings.CHUNK_SIZE,
        help=f"청크 최대 문자 수 (기본값: {settings.CHUNK_SIZE})",
    )
    parser.add_argument(
        "--chunk-overlap", type=int, default=settings.CHUNK_OVERLAP,
        help=f"청크 간 오버랩 문자 수 (기본값: {settings.CHUNK_OVERLAP})",
    )
    parser.add_argument(
        "--collection", default=settings.WEAVIATE_COLLECTION,
        help=f"Weaviate 컬렉션명 (기본값: {settings.WEAVIATE_COLLECTION})",
    )
    parser.add_argument(
        "--keywords", type=str, default=None,
        help="등록 파일별 추가할 키워드 ,로 분리하여 입력",
    )
    parser.add_argument(
        "--no-cache", action="store_true",
        help="청킹 캐시를 무시하고 재처리",
    )
    args = parser.parse_args()

    source_path = Path(args.source)
    if not source_path.exists():
        log.error(f"경로가 존재하지 않습니다: {source_path}")
        sys.exit(1)

    # ── 시작 배너 ──────────────────────────────────────────────────────────────
    log.info("=" * 60)
    log.info("  RAG 인제스트 파이프라인")
    log.info("=" * 60)
    log.info(f"  소스       : {source_path.resolve()}")
    log.info(f"  청크 크기  : {args.chunk_size} / 오버랩: {args.chunk_overlap}")
    log.info(f"  컬렉션     : {args.collection}")
    log.info(f"  키워드     : {args.keywords}")
    log.info(f"  Weaviate   : {settings.WEAVIATE_MODE} 모드")
    log.info(f"  임베딩     : {settings.EMBEDDING_MODEL}")
    log.info("=" * 60)

    embedding_service = EmbeddingService(model_name=settings.EMBEDDING_MODEL)

    client = create_client()
    try:
        vector_store = VectorStoreService(
            client=client,
            embedding_service=embedding_service,
            collection_name=args.collection,
            vector_dim=settings.EMBEDDING_DIMENSION,
        )

        pipeline = IngestionPipeline(
            vector_store=vector_store,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
        )

        keywords = args.keywords.split(",") if args.keywords else None
        # ── 실행 ───────────────────────────────────────────────────────────────
        if source_path.is_dir():
            results = pipeline.ingest_directory(source_path, keywords=keywords)
            log.info("[결과 요약]")
            for r in results:
                log.info(f"  ✅ {Path(r['source']).name}: {r['chunks_inserted']}개 청크 삽입")
        else:
            result = pipeline.ingest_file(
                source_path,
                use_cache=not args.no_cache,
                keywords=keywords
            )
            log.info(f"  ✅ {Path(result['source']).name}: {result['chunks_inserted']}개 청크 삽입")

    finally:
        client.close()


if __name__ == "__main__":
    main()
