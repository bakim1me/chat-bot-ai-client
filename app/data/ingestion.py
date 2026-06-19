from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List

from bs4 import BeautifulSoup

from app.core.config import settings
from app.core.logger import get_logger
from app.data.file_loader import DocumentLoader, ExcelLoader
from app.data.preprocessor import ChunkCache, TextChunker
from app.schemas.RawDocument import RawDocument
from app.services.db_service import DBService
from app.services.vector_store_service import VectorStoreService

log = get_logger(__name__)

class IngestionPipeline:
    """
    문서 인제스트 전체 파이프라인.
    data_loader: DocumentLoader
    preprocessor: TextChunker → ChunkCache(JSON 저장)
    vector_store: EmbeddingService(KR-SBERT) → VectorStoreService(Weaviate 삽입)
    """

    def __init__(
        self,
        vector_store: VectorStoreService,
        chunk_size: int = settings.CHUNK_SIZE,
        chunk_overlap: int = settings.CHUNK_OVERLAP,
        cache_dir: str = "data/processed",
    ):
        self.vector_store = vector_store
        self.chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self.cache = ChunkCache(cache_dir=cache_dir)

    # ── 단일 파일 인제스트 ────────────────────────────────────────────────────

    def ingest_file(
        self,
        file_path: str | Path,
        use_cache: bool = True,
        keywords: List[str] = None,
    ) -> Dict:
        """
        단일 파일을  ->   preprocessor ->  vector_store 순서로 처리
        Args:
            file_path:  인제스트할 파일 경로
            use_cache:  True면 기존 청크 캐시 재사용 (청킹 단계 스킵)
            keywords: 검색 키워드 목록
        Returns:
            {"source", "chunks_created", "chunks_inserted"}
        """
        path = Path(file_path)
        cache_name = f"{path.stem}_chunks"

        # ── ,2: 데이터 로드 + 청킹 ─────────────────────────────────────────
        if use_cache and self.cache.exists(cache_name):
            chunks = self.cache.load(cache_name)
            log.info(f"[Ingestion] 캐시 로드: {len(chunks)}개 청크 ({path.name})")
        else:
            text_data = self._read_document(path)
            chunks = self._chunk_document(text_data, path, cache_name, keywords=keywords)

        # ──  3: Weaviate 저장 ────────────────────────────────
        inserted = self._insert_chunk(chunks)

        return {
            "source": str(path),
            "chunks_created": len(chunks),
            "chunks_inserted": inserted,
        }

    # ── 디렉토리 일괄 인제스트 ───────────────────────────────────────────────
    def ingest_directory(self, dir_path: str | Path, keywords : List[str] = None) -> List[Dict]:
        """
        디렉토리 내 모든 지원 파일(.txt, .pdf)을 순서대로 인제스트.

        Returns:
            파일별 인제스트 결과 리스트
        """
        log.info(f"[Ingestion] 디렉토리 스캔: {dir_path}")

        loader = DocumentLoader(dir_path)
        documents = loader.load_directory(dir_path)

        if not documents:
            log.info("[Ingestion] 처리할 파일이 없습니다.")
            return []

        results: List[Dict] = []
        for file_path, text_data in documents.items():
            path = Path(file_path)
            cache_name = f"{path.stem}_chunks"

            chunks = self._chunk_document(text_data, path, cache_name, keywords=keywords)

            inserted = self._insert_chunk(chunks)
            results.append({
                "source": file_path,
                "chunks_created": len(chunks),
                "chunks_inserted": inserted,
            })

        total = sum(r["chunks_inserted"] for r in results)
        log.info(f"[Ingestion] 전체 완료: {len(results)}개 파일, {total}개 청크 삽입")
        return results

    # ── 내부 단계 메서드 ──────────────────────────────────────────────────────
    def _read_document(self, path: Path) -> List[str]:
        """ 문서 로드"""
        loader = ExcelLoader(path) if path.suffix in ['.xlsx', '.csv'] else DocumentLoader(path)
        log.info(f"\n문서 로드: {path.name}")
        return loader.load()

    def _chunk_document(self, text_data: List[str], path: Path, cache_name: str, keywords: List[str] = None) -> List[RawDocument]:
        chunks = []
        for idx, row_text in enumerate(text_data):
            row_text = row_text.strip()
            if not row_text:
                continue
            row_source = f"{path.name}_row{idx}"
            row_chunks = self.chunker.split(row_text, source=row_source, keywords=keywords)
            chunks.extend(row_chunks)
            
        self.cache.save(chunks, cache_name)
        log.info(f"문서 청킹 완료: {len(chunks)}개 청크 생성")
        return chunks

    def _insert_chunk(self, chunks: List[RawDocument]) -> int:
        """KR-SBERT 임베딩 후 Weaviate 삽입"""
        inserted = self.vector_store.insert_chunks(chunks)
        log.info(f"Weaviate 삽입 완료: {inserted}개 삽입")
        return inserted

    # ── DB 인제스트 ─────────────────────────────────────────────────────────

    def ingest_db_notices(self, db_service: DBService, keywords: List[str] = None, use_cache: bool = True) -> int:
        """공지사항 DB 데이터를 벡터 DB에 인제스트"""
        cache_name = "db_notices_chunks"
        if use_cache and self.cache.exists(cache_name):
            chunks = self.cache.load(cache_name)
            log.info(f"[Ingestion] 캐시 로드: {len(chunks)}개 청크 (db_notices)")
            return self._insert_chunk(chunks)

        records = db_service.get_notices()
        chunks = []
        for record in records:
            text_parts = [f"Q: {record.title}",
                          f"A: 관련 링크 - https://dsdo.co.kr/pages/board/post-detail.html?boardType=notice&articleNo={record.id}"]
            if getattr(record, 'file_name', None):
                text_parts.append(f" A: 파일 경로 - https://kr.object.ncloudstorage.com/{record.file_name}")

            combined_text = "\n".join(text_parts)
            current_keywords = (keywords or []) + ["공지사항"] + record.title.split()
            record_chunks = self.chunker.split(combined_text, source=f"notice_{record.id}", keywords=current_keywords)

            for chunk in record_chunks:
                chunk.source_id = str(record.id)
                chunk.source_type = "db_notice"
                chunks.append(chunk)

        self.cache.save(chunks, cache_name)
        log.info(f"\n공지사항 데이터 청킹 완료: {len(chunks)}개 청크 생성 및 캐시 저장")
        return self._insert_chunk(chunks)

    def ingest_db_faqs(self, db_service: DBService, keywords: List[str] = None, use_cache: bool = True) -> int:
        """자주하는질문 DB 데이터를 벡터 DB에 인제스트"""
        cache_name = "db_faqs_chunks"
        if use_cache and self.cache.exists(cache_name):
            chunks = self.cache.load(cache_name)
            log.info(f"[Ingestion] 캐시 로드: {len(chunks)}개 청크 (db_faqs)")
            return self._insert_chunk(chunks)

        records = db_service.get_faqs()
        chunks = []
        for record in records:
            text_parts = [f"Q: {record.title}"]
            if getattr(record, 'body', None):
                body_text = BeautifulSoup(record.body, "html.parser").get_text(separator="\n", strip=True)
                text_parts.append(f"A: {body_text}")

            if len(text_parts) > 1 :
                combined_text = "\n\n".join(text_parts)
                current_keywords = (keywords or []) + ["자주하는질문", "FAQ"] + record.title.split()
                record_chunks = self.chunker.split(combined_text, source=f"faq_{record.id}", keywords=current_keywords)

                for chunk in record_chunks:
                    chunk.source_id = str(record.id)
                    chunk.source_type = "db_faq"
                    chunks.append(chunk)

        self.cache.save(chunks, cache_name)
        log.info(f"\n자주하는질문 데이터 청킹 완료: {len(chunks)}개 청크 생성 및 캐시 저장")
        return self._insert_chunk(chunks)

    def ingest_db_exam_oxs(self, db_service: DBService, keywords: List[str] = None, use_cache: bool = True) -> int:
        """정오표 DB 데이터를 벡터 DB에 인제스트"""
        cache_name = "db_exam_oxs_chunks"
        if use_cache and self.cache.exists(cache_name):
            chunks = self.cache.load(cache_name)
            log.info(f"[Ingestion] 캐시 로드: {len(chunks)}개 청크 (db_exam_oxs)")
            return self._insert_chunk(chunks)

        records = db_service.get_exam_oxs()
        chunks = []
        for record in records:
            title = record.title.replace('THE PREMIUM', 'THE PREMIUM, 더프모, 더 프리미엄 모의고사') \
                if 'THE PREMIUM' in record.title else record.title
            text_parts = [f"Q: {title} 정오표 오류 정정 문제 정정",
                          f"A: 관련 링크 - https://dsdo.co.kr/pages/board/post-detail.html?boardType=ox&articleNo={record.id}"]
            if getattr(record, 'file_name', None):
                text_parts.append(f"A: 첨부 파일 경로 - https://kr.object.ncloudstorage.com/{record.file_name}")

            combined_text = "\n\n".join(text_parts)
            current_keywords = (keywords or []) + ["정오표", "문제오류","오류정정","문제정정"] + record.title.split()
            record_chunks = self.chunker.split(combined_text, source=f"exam_ox_{record.id}", keywords=current_keywords)

            for chunk in record_chunks:
                chunk.source_id = str(record.id)
                chunk.source_type = "db_exam_ox"
                chunks.append(chunk)

        self.cache.save(chunks, cache_name)
        log.info(f"\n정오표 데이터 청킹 완료: {len(chunks)}개 청크 생성 및 캐시 저장")
        return self._insert_chunk(chunks)

    def ingest_db_ipsis(self, db_service: DBService, keywords: List[str] = None, use_cache: bool = True) -> int:
        """입시자료 DB 데이터를 벡터 DB에 인제스트"""
        cache_name = "db_ipsis_chunks"
        if use_cache and self.cache.exists(cache_name):
            chunks = self.cache.load(cache_name)
            log.info(f"[Ingestion] 캐시 로드: {len(chunks)}개 청크 (db_ipsis)")
            return self._insert_chunk(chunks)

        records = db_service.get_ipsis()
        chunks = []
        for record in records:

            text_parts = [f"Q: {record.title} 입시 자료",
                          f"A: 관련 자료 링크 - https://dsdo.co.kr/pages/board/post-detail.html?boardType=ipsi&articleNo={record.b_no}"]
            combined_text = "\n\n".join(text_parts)
            current_keywords = (keywords or []) + ["입시자료", "입시"] + record.title.split()
            record_chunks = self.chunker.split(combined_text, source=f"ipsi_{record.b_no}", keywords=current_keywords)

            for chunk in record_chunks:
                chunk.source_id = str(record.b_no)
                chunk.source_type = "db_ipsi"
                chunks.append(chunk)

        self.cache.save(chunks, cache_name)
        log.info(f"\n입시자료 데이터 청킹 완료: {len(chunks)}개 청크 생성 및 캐시 저장")
        return self._insert_chunk(chunks)
