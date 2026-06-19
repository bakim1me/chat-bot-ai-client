"""
문서 인제스트 라우터 — 로드 및 전처리 + 청킹 + 임베딩 & 저장

POST   /api/v1/documents/ingest                → 파일 업로드 & 인제스트
GET    /api/v1/documents/collections           → 컬렉션 목록
DELETE /api/v1/documents/collections/{name}   → 컬렉션 삭제
"""
import tempfile
from pathlib import Path
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.config import settings
from app.core.dependencies import VectorStoreDep, DBServiceDep
from app.core.logger import get_logger
from app.data.ingestion import IngestionPipeline
from app.schemas.document import (
    CollectionDeleteResponse,
    CollectionListResponse,
    IngestFileResult,
    IngestResponse,
)

router = APIRouter(prefix="/documents", tags=["Documents — Ingestion"])

# 허용 파일 확장자
_ALLOWED_EXTENSIONS = {".txt", ".pdf", ".csv", ".xlsx"}
log =get_logger(__name__)

@router.post(
    "/ingest",
    response_model=IngestResponse,
    summary="문서 업로드 & 인제스트",
    description=(
        "`.txt` / `.pdf` 파일을 업로드합니다.  \n\n"
        "파일을 청크로 분할하고 `data/processed/`에 JSON 캐시를 저장합니다.  \n"
        "각 청크를 KR-SBERT로 임베딩 후 Weaviate에 저장합니다.  \n\n"
        "여러 파일을 동시에 업로드할 수 있습니다."
    ),
)
async def ingest_documents(
    vector_store: VectorStoreDep,
    files: List[UploadFile] = File(..., description=".txt,.pdf, .csv, .xlsx 파일 (다중 업로드 가능)"),
) -> IngestResponse:
    # ── 파일 확장자 사전 검증 ──────────────────────────────────────────────────
    for upload in files:
        ext = Path(upload.filename or "").suffix.lower()
        if ext not in _ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"'{upload.filename}': 지원하지 않는 파일 형식 '{ext}'. "
                    f"허용 형식: {', '.join(_ALLOWED_EXTENSIONS)}"
                ),
            )

    pipeline = IngestionPipeline(vector_store=vector_store)
    results: List[IngestFileResult] = []

    for upload in files:
        ext = Path(upload.filename or "file").suffix.lower()
        original_name = upload.filename or "unknown"

        # 임시 파일에 저장 후 파이프라인 실행
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            content = await upload.read()
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            result = pipeline.ingest_file(tmp_path, use_cache=False)
        finally:
            tmp_path.unlink(missing_ok=True)   # 임시 파일 반드시 삭제

        results.append(IngestFileResult(
            source=original_name,
            chunks_created=result["chunks_created"],
            chunks_inserted=result["chunks_inserted"],
        ))

    return IngestResponse(
        results=results,
        total_files=len(results),
        total_chunks_inserted=sum(r.chunks_inserted for r in results),
        collection=settings.WEAVIATE_COLLECTION,
    )
@router.post(
    "/ingest/rdb",
    summary="Weaviate 컬렉션 목록 조회",
)
async def ingest_RDB(
        vector_store: VectorStoreDep,
        db_service: DBServiceDep,
        table:str = None,
        keywords: list = None
) -> IngestResponse:
    pipeline = IngestionPipeline(vector_store=vector_store)

    results: List[IngestFileResult] = []

    if not table or "ox" in table:
        result_size = pipeline.ingest_db_exam_oxs(db_service, keywords)
        log.info(f"  ✅ Target Table [oxs]: {result_size}개 청크 삽입")
        results.append(IngestFileResult(
            source="ox",
            chunks_created=result_size,
            chunks_inserted=result_size,
        ))

    if not table or "faq" in table:
        result_size = pipeline.ingest_db_faqs(db_service, keywords)
        results.append(IngestFileResult(
            source="faq",
            chunks_created=result_size,
            chunks_inserted=result_size,
        ))
        log.info(f"  ✅ Target Table [faq]: {result_size}개 청크 삽입")

    if not table or "ipsi" in table:
        result_size = pipeline.ingest_db_ipsis(db_service, keywords)
        results.append(IngestFileResult(
            source="ipsi",
            chunks_created=result_size,
            chunks_inserted=result_size,
        ))
        log.info(f"  ✅ Target Table [ipsi]: {result_size}개 청크 삽입")

    if not table or "notice" in table:
        result_size = pipeline.ingest_db_notices(db_service, keywords)
        results.append(IngestFileResult(
            source="notice",
            chunks_created=result_size,
            chunks_inserted=result_size,
        ))
        log.info(f"  ✅ Target Table [notice]: {result_size}개 청크 삽입")

    return IngestResponse(
        results=results,
        total_files=len(results),
        total_chunks_inserted=sum(r.chunks_inserted for r in results),
        collection=settings.WEAVIATE_COLLECTION,
    )

@router.get(
    "/collections",
    response_model=CollectionListResponse,
    summary="Weaviate 컬렉션 목록 조회",
)
async def list_collections(vector_store: VectorStoreDep) -> CollectionListResponse:
    collections = vector_store.list_collections()
    return CollectionListResponse(
        collections=collections,
        total=len(collections),
    )


@router.delete(
    "/collections/{name}",
    response_model=CollectionDeleteResponse,
    summary="Weaviate 컬렉션 삭제",
    description="지정한 컬렉션과 그 안의 모든 벡터 데이터를 삭제합니다. 되돌릴 수 없습니다.",
)
async def delete_collection(
    name: str,
    vector_store: VectorStoreDep,
) -> CollectionDeleteResponse:
    deleted = vector_store.delete_collection(name)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"컬렉션 '{name}'을 찾을 수 없습니다.",
        )
    return CollectionDeleteResponse(deleted=name)
