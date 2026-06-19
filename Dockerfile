# 1. 경량화된 파이썬 베이스 이미지 사용
FROM python:3.11-slim

# 2. 작업 디렉토리 설정
WORKDIR /app

# 3. OS 레벨 필수 패키지 설치 (빌드 도구)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 4. 의존성 설치 (캐시 효율을 위해 요구사항 파일만 먼저 복사)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 5. 프로젝트 소스 코드 복사
COPY ./app ./app
COPY ./data ./data
# 운영에 필요한 빈 디렉토리 생성
RUN mkdir -p logs plan scripts

# 6. 파이썬 버퍼링 해제 옵션 (Docker 로그 실시간 확인용)
ENV PYTHONUNBUFFERED=1

# 7. 포트 개방
EXPOSE 8000

# 8. FastAPI 서버 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
