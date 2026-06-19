from dataclasses import dataclass, field
from typing import Dict, Any, List

@dataclass
class RawDocument:
    """모든 Loader가 반환하는 공통 원본 문서 스키마"""
    chunk_id: str               # 아이디 (청크 ID)
    source_id: str        # PK 또는 파일명 (추후 업데이트/삭제 시 기준점)
    source_type: str      # 'rdb', 'excel', 'txt', 'db_notice' 등
    content: str          # 임베딩할 핵심 텍스트
    metadata: Dict[str, Any] = field(default_factory=dict)
    keywords: List[str] = field(default_factory=list) # 하이브리드 검색용 태그 및 키워드 배열
    parent_content: str = "" # 원본 전체 텍스트 보관용
