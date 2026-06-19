"""
Weaviate 클라이언트 연결 관리 모듈
"""
from contextlib import contextmanager
from typing import Generator

import weaviate

from app.core.config import settings


def create_client() -> weaviate.WeaviateClient:
    # 환경변수(WEAVIATE_MODE) 설정에 따라 Weaviate 클라이언트 객체를 생성

    mode = settings.WEAVIATE_MODE
    #  클라우드 사용
    if mode == "cloud":
        return weaviate.connect_to_weaviate_cloud(
            cluster_url=settings.WEAVIATE_URL,
            auth_credentials=weaviate.auth.AuthApiKey(settings.WEAVIATE_API_KEY),
        )
    #  Docker에 올려서 사용
    elif mode == "local":
        return weaviate.connect_to_local(
            host=settings.WEAVIATE_HOST,
            port=settings.WEAVIATE_PORT,
        )
    else:
        # 기본 모드: embedded (로컬에서 Docker 없이 구동)
        return weaviate.connect_to_embedded()


@contextmanager
def weaviate_session() -> Generator[weaviate.WeaviateClient, None, None]:
    """
    weaviate session 컨텍스트 매니저.
    사용 예시:
        with weaviate_session() as client:
            client.collections.list_all()
    """
    client = create_client()
    try:
        yield client
    finally:
        client.close()
