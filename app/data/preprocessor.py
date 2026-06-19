"""
1. 문서 로드 및 전처리
1. 텍스트 청킹

Classes:
    DocumentLoader  - .txt / .pdf 파일을 RawDocument로 변환
    ExcelLoader     - .csv / .xlsx 파일을 RawDocument로 변환
    TextConvertor   - .xlsx / db 데이터를 텍스르 파일로 변환
    TextChunker     - RecursiveCharacterTextSplitter 스타일 슬라이딩 윈도우 청킹
    ChunkCache      - 청킹 결과를 JSON으로 캐시/복원
    TextChunk       - 단일 청크 데이터 클래스
"""
from __future__ import annotations

import json
import os.path
import re
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List

from app.core.logger import get_logger
from app.schemas.RawDocument import RawDocument

log = get_logger(__name__)

# ── 텍스트 청커 ───────────────────────────────────────────────────────────────

class TextChunker:
    """
    RecursiveCharacterTextSplitter 스타일 슬라이딩 윈도우 청킹.

    분할 우선순위: 단락 구분("\\n\\n") → 줄바꿈("\\n") → 문장("." 등) → 공백 → 문자
    오버랩을 통해 청크 간 문맥 연속성을 보장합니다.
    """

    # 분할 우선순위 구분자 (앞쪽이 높은 우선순위)
    SEPARATORS: List[str] = ["\n\n", "\n", ". ", "! ", "? ", " ", ""]

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        if chunk_overlap >= chunk_size:
            raise ValueError(
                f"chunk_overlap({chunk_overlap})은 chunk_size({chunk_size})보다 작아야 합니다."
            )
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split(self, text: str, source: str = "unknown", keywords: List[str] = None) -> List[RawDocument]:
        """텍스트 → RawDocument 리스트"""
        # 연속된 공백 정규화
        text = re.sub(r"[ \t]+", " ", text)
        raw_chunks = self._split_text(text, self.SEPARATORS)

        chunks: List[RawDocument] = []
        if os.path.isfile(source):
            _, ext = os.path.splitext(source)
            source_id = Path(source).stem
        else:
            ext = "db"
            source_id = ""

        for idx, chunk_text in enumerate(raw_chunks):
            chunk_text = chunk_text.strip()
            if not chunk_text:
                continue
            data = RawDocument(
                chunk_id=f"{source_id}_{idx}",
                source_id=source_id,
                source_type=ext,
                content=chunk_text,
                metadata={"source": source, "chunk_index": idx},
                keywords=keywords or [],
                parent_content=text
            )
            chunks.append(data)
        return chunks

    def split_documents(self, documents: Dict[str, str]) -> List[RawDocument]:
        """여러 문서를 한 번에 청킹"""
        all_chunks: List[RawDocument] = []
        for source, text in documents.items():
            chunks = self.split(text, source=source)
            all_chunks.extend(chunks)
            log.info(f"[TextChunker] {Path(source).name}: {len(chunks)}개 청크 생성")
        return all_chunks

    # ── 내부 구현 ─────────────────────────────────────────────────────────────

    def _split_text(self, text: str, separators: List[str]) -> List[str]:
        """재귀적으로 구분자를 적용해 chunk_size 이하의 청크 생성"""
        # 사용할 구분자 선택
        sep :str = ""
        remaining_seps: List[str] = []
        for i, s in enumerate(separators):
            if s == "" or s in text:
                sep = s
                remaining_seps = separators[i + 1:]
                break

        parts = text.split(sep) if sep else [text]
        final_chunks: List[str] = []
        current_parts: List[str] = []
        current_len = 0

        for part in parts:
            part_len = len(part)

            # 단일 파트가 chunk_size를 초과하면 하위 구분자로 재귀 분할
            if part_len > self.chunk_size and remaining_seps:
                sub_chunks = self._split_text(part, remaining_seps)
                for sub in sub_chunks:
                    final_chunks.extend(
                        self._merge_and_flush(current_parts, current_len, sep, sub)
                    )
                    current_parts, current_len = [], 0
                continue

            # 현재 파트를 추가하면 chunk_size 초과 → 플러시 후 오버랩 처리
            if current_len + len(sep) + part_len > self.chunk_size and current_parts:
                merged = sep.join(current_parts).strip()
                if merged:
                    final_chunks.append(merged)
                # 오버랩: 뒤에서부터 overlap 크기만큼 유지
                current_parts = self._overlap_parts(current_parts, sep)
                current_len = len(sep.join(current_parts))

            current_parts.append(part)
            current_len += len(sep) + part_len

        # 남은 파트 처리
        if current_parts:
            merged = sep.join(current_parts).strip()
            if merged:
                final_chunks.append(merged)

        return final_chunks

    def _merge_and_flush(
        self,
        current_parts: List[str],
        current_len: int,
        sep: str,
        new_part: str,
    ) -> List[str]:
        results = []
        if current_parts:
            merged = sep.join(current_parts).strip()
            if merged:
                results.append(merged)
        if new_part.strip():
            results.append(new_part.strip())
        return results

    def _overlap_parts(self, parts: List[str], sep: str) -> List[str]:
        """오버랩 크기만큼 파트 리스트의 후미를 반환"""
        overlap_parts: List[str] = []
        overlap_len = 0
        for part in reversed(parts):
            if overlap_len + len(part) + len(sep) <= self.chunk_overlap:
                overlap_parts.insert(0, part)
                overlap_len += len(part) + len(sep)
            else:
                break
        return overlap_parts


# ── 청크 캐시 ─────────────────────────────────────────────────────────────────

class ChunkCache:
    """청킹 결과를 JSON 파일로 캐시 (재실행 시 청킹 단계 스킵)"""

    def __init__(self, cache_dir: str | Path = "data/processed"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def save(self, chunks: List[RawDocument], name: str) -> Path:
        """청크 리스트를 JSON으로 저장"""
        out_path = self.cache_dir / f"{name}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump([asdict(c) for c in chunks], f, ensure_ascii=False, indent=2)
        log.info(f"[ChunkCache] 저장: {out_path} ({len(chunks)}개 청크)")
        return out_path

    def load(self, name: str) -> List[RawDocument]:
        """JSON에서 청크 리스트 복원"""
        in_path = self.cache_dir / f"{name}.json"
        if not in_path.exists():
            raise FileNotFoundError(f"캐시 파일 없음: {in_path}")
        with open(in_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [RawDocument(**item) for item in data]

    def exists(self, name: str) -> bool:
        return (self.cache_dir / f"{name}.json").exists()
