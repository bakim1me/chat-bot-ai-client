from __future__ import annotations

from typing import List

from sentence_transformers import SentenceTransformer

from app.core.logger import get_logger

log = get_logger(__name__)

class EmbeddingService:
    """
    sentence-transformers 기반 임베딩 서비스.
    의존성 주입 시 @lru_cache로 싱글턴 처리되므로
    모델은 앱 생애주기 동안 1회만 로드됩니다.
    """
    def __init__(self, model_name: str = "snunlp/KR-SBERT-V40K-klueNLI-augSTS", token = None):
        """
        모델: snunlp/KR-SBERT-V40K-klueNLI-augSTS
        - 한국어 특화 Sentence-BERT
        - 출력 차원: 768
        - 첫 실행 시 HuggingFace Hub에서 자동 다운로드 (~480MB)
        """
        log.info(f"[EmbeddingService] 모델 로딩 중: {model_name}")
        self.model_name = model_name
        self.model = SentenceTransformer(model_name, token = token)
        self.dimension: int = self.model.get_embedding_dimension()
        log.info(f"[EmbeddingService] 로딩 완료 | 출력 차원: {self.dimension}")

    # ── 단일 인코딩 (: 쿼리 임베딩) ───────────────────────────────────

    def encode(self, text: str) -> List[float]:
        """
        단일 텍스트 → float 벡터 (코사인 유사도용 L2 정규화 적용).
        쿼리 임베딩에 사용.
        """
        vector = self.model.encode(text, normalize_embeddings=True)
        return vector.tolist()

    # ── 배치 인코딩 (대량 청크 임베딩) ──────────────────────────────

    def encode_batch(
        self,
        texts: List[str],
        batch_size: int = 32,
        show_progress: bool = True,
    ) -> List[List[float]]:
        """
        텍스트 리스트 → 벡터 리스트 (배치 처리).
        대량 인제스트에 사용.

        Args:
            texts:          인코딩할 텍스트 목록
            batch_size:     배치 크기 (메모리-속도 트레이드오프)
            show_progress:  tqdm 진행 바 표시 여부
        """
        vectors = self.model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=show_progress,
        )
        return vectors.tolist()
