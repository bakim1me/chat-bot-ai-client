import csv
import os
from datetime import datetime
from pathlib import Path

from app.core.logger import get_logger

log = get_logger(__name__)

class HistoryService:
    """
    사용자 질의 및 LLM 토큰 사용량 이력(History)을 파일에 저장하는 전담 서비스.
    """

    def __init__(self, log_dir: str | Path = "data/history"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.csv_path = self.log_dir / "token_usage.csv"

        # 파일이 없을 경우 헤더를 먼저 생성
        if not self.csv_path.exists():
            try:
                with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        "timestamp",
                        "prompt_chars",
                        "prompt_tokens",
                        "prompt_ratio",
                        "response_chars",
                        "response_tokens",
                        "response_ratio",
                        "response_total_tokens",
                        "llm_time_ms",
                        "total_time_ms"
                    ])
            except Exception as e:
                log.error(f"History CSV 헤더 생성 실패: {e}")

    def log_token_usage(
        self,
        prompt_chars: int,
        prompt_tokens: int,
        response_chars: int,
        response_tokens: int,
        response_total_tokens: int,
        llm_time_ms: int,
        total_time_ms: int
    ) -> None:
        """
        주어진 글자 수와 토큰 수를 기반으로 비율을 계산하여 CSV 파일에 누적(Append)합니다.
        """
        try:
            prompt_ratio = round(prompt_chars / prompt_tokens, 2) if prompt_tokens else 0.0
            response_ratio = round(response_chars / response_tokens, 2) if response_tokens else 0.0

            with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.now().isoformat(),
                    prompt_chars,
                    prompt_tokens,
                    prompt_ratio,
                    response_chars,
                    response_tokens,
                    response_ratio,
                    response_total_tokens,
                    llm_time_ms,
                    total_time_ms
                ])
        except Exception as e:
            # 로깅 자체의 실패가 메인 파이프라인 중단으로 이어지지 않도록 예외 처리
            log.error(f"토큰 사용량 CSV 저장 실패: {e}")
