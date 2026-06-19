import os
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import find_dotenv

APP_ENV = os.getenv("APP_ENV", "local")
ENV_FILENAME = f".env.{APP_ENV}"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=find_dotenv(ENV_FILENAME),
        env_file_encoding="utf-8",
        extra='ignore')

    # ── 앱 기본 설정 ──────────────────────────────────────────────
    APP_NAME: str
    APP_VERSION: str
    DEBUG: bool

    # ── Gemini API ────────────────────────────────────────────────
    GEMINI_API_KEY: str
    GEMINI_MODEL: str

    # ── DB 연동  ──────────────────────────────────────────────────
    MARIADB_URL: str

    # ── Embedding ─────────────────────────────────────────────────
    EMBEDDING_MODEL: str
    EMBEDDING_DIMENSION: int

    HF_TOKEN: str

    # ── Weaviate ──────────────────────────────────────────────────
    WEAVIATE_MODE: Literal["embedded", "local", "cloud"]
    WEAVIATE_HOST: str
    WEAVIATE_PORT: int
    WEAVIATE_URL: str
    WEAVIATE_API_KEY: str
    WEAVIATE_COLLECTION: str

    # ── RAG 검색 파라미터 ─────────────────────────────────────────
    RAG_TOP_K: int
    RAG_SCORE_THRESHOLD: float

    # ── 청킹 파라미터 ─────────────────────────────────────────────
    CHUNK_SIZE: int
    CHUNK_OVERLAP: int

    # ── 서버 ──────────────────────────────────────────────────────
    HOST: str
    PORT: int

settings = Settings()

