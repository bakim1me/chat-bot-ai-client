import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler
from typing import Optional

#  임포트 시 환경변수 조작 (C++ 백엔드 경고 차단)
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["GRPC_VERBOSITY"] = "ERROR"
os.environ["GRPC_TRACE"] = ""

from app.core.config import settings

# 로그 디렉토리 생성 및 핸들러 설정
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "app.log")

log_level = logging.DEBUG if settings.DEBUG else logging.INFO
log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
date_format = "%Y-%m-%d %H:%M:%S"

# 포매터 생성
formatter = logging.Formatter(fmt=log_format, datefmt=date_format)

# 콘솔 출력용 핸들러
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)

# 파일 출력용 핸들러
file_handler = TimedRotatingFileHandler(
    LOG_FILE, when="midnight", interval=1, backupCount=0, encoding="utf-8"
)
file_handler.setFormatter(formatter)

# 핸들러 명시적 등록
logging.basicConfig(
    level=log_level,
    handlers=[stream_handler, file_handler],
)

# 일부 외부 라이브러리의 과도한 로그 출력 제어
logging.getLogger("uvicorn.access").setLevel(logging.INFO)
logging.getLogger("httpx").setLevel(logging.INFO)
logging.getLogger("weaviate").setLevel(logging.INFO)
logging.getLogger("grpcio").setLevel(logging.ERROR)

# 로거 획득 함수
def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    지정된 이름의 로거를 반환
    """
    return logging.getLogger(name or settings.APP_NAME)
