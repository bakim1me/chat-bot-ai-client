from typing import List

from pydantic import BaseModel, Field


# ── 인제스트 결과 ─────────────────────────────────────────────────────────────

class IngestFileResult(BaseModel):
    """단일 파일 인제스트 결과"""
    source: str          = Field(..., description="원본 파일명")
    chunks_created: int  = Field(..., description="생성된 청크 수")
    chunks_inserted: int = Field(..., description="Weaviate에 삽입된 청크 수")
    status: str          = Field(default="success", description="처리 상태")


class IngestResponse(BaseModel):
    """다중 파일 인제스트 최종 응답"""
    results: List[IngestFileResult]  = Field(..., description="파일별 결과 목록")
    total_files: int                 = Field(..., description="처리된 파일 수")
    total_chunks_inserted: int       = Field(..., description="총 삽입된 청크 수")
    collection: str                  = Field(..., description="저장된 Weaviate 컬렉션명")
    status: str                      = Field(default="success")

    model_config = {
        "json_schema_extra": {
            "example": {
                "results": [
                    {
                        "source": "my_document.pdf",
                        "chunks_created": 42,
                        "chunks_inserted": 42,
                        "status": "success",
                    }
                ],
                "total_files": 1,
                "total_chunks_inserted": 42,
                "collection": "Documents",
                "status": "success",
            }
        }
    }


# ── 컬렉션 관리 ───────────────────────────────────────────────────────────────

class CollectionListResponse(BaseModel):
    """Weaviate 컬렉션 목록"""
    collections: List[str] = Field(..., description="컬렉션 이름 목록")
    total: int             = Field(..., description="컬렉션 수")


class CollectionDeleteResponse(BaseModel):
    """컬렉션 삭제 결과"""
    deleted: str   = Field(..., description="삭제된 컬렉션명")
    status: str    = Field(default="success")
