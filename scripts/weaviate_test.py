"""
weaviate 연결 테스트 스크립트
사전에 문서를 인제스트 해두지 않아도, 이 스크립트가 임시 파일을 생성하여 전체 과정을 테스트합니다.
"""
import asyncio
import sys
import tempfile
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


from app.core.config import settings
from app.core.weaviate_client import create_client
import argparse
from app.services.vector_store_service import VectorStoreService

async def main():
    # ── 테스트용 임시 문서 생성 ────────────────────────────────────────────────

    parser = argparse.ArgumentParser(
        description="Weaviate 연결 확인",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--option", type=str, default="D",
        help="추가할 RDB 테이블",
    )

    parser.add_argument(
        "--document", type=str, default="Documents",
        help="대상 다큐먼트",
    )

    args = parser.parse_args()
    client = create_client()
    try:
        # 테스트용 임시 컬렉션 사용
        collection = args.document
        
        vector_store = VectorStoreService(
            client=client,
            embedding_service=None,
            collection_name=collection,
            vector_dim=settings.EMBEDDING_DIMENSION,
        )
        
        # 기존 테스트 컬렉션 비우기
        if args.option == 'D' :
            vector_store.delete_collection(collection)

        # vector_store.ensure_collection()

    finally:
        # 정리
        client.close()

if __name__ == "__main__":
    asyncio.run(main())
