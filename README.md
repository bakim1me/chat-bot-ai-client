# 🤖 RAG 챗봇 시스템 (Retrieval-Augmented Generation Chatbot)

이 프로젝트는 사내 및 서비스 데이터를 기반으로 답변을 생성하는 RAG 기반의 교육용 AI 챗봇 시스템입니다.

## 🚀 주요 기능 및 특징 (Features)

- **Small-to-Big Retrieval 전략:** 문서 검색 속도를 위해 데이터를 작게 쪼개어 검색하되, LLM 응답 시에는 잘려나간 원본 데이터 전체(`parent_content`)를 복원하여 넘겨줌으로써 문맥 보존율을 극대화했습니다.
- **Row-Level 데이터 파싱 (독립성 보장):** 로컬 파일(`.csv`, `.txt`) 및 MariaDB 연동 시, 각 행(Row) 단위로 완전히 분리된 청킹(Chunking)을 수행하여 각 문서 내용이 혼합되는 노이즈를 완벽히 차단했습니다.
- **당해 연도 동적 필터링:** 챗봇이 과거의 정보로 오답을 내는 것을 막기 위해 시스템 가동 시점을 기준으로 MariaDB에서 "당해 연도" 데이터만 필터링하여 Ingestion 하도록 설계했습니다.
- **정교한 프롬프트 엔지니어링:** 10대 대상의 다정한 어조(해요체) 유지, 1:1 대화 몰입을 위해 RAG 시스템 참조 사실 노출 금지, 외부 문서 검색 결과가 없을 시 자연스러운 방어(Fallback) 기제 등을 도입했습니다.
- **History & 토큰 모니터링:** LLM 소요 시간, 전체 응답 시간, 그리고 프롬프트와 응답의 글자수 대비 사용 토큰량을 정밀하게 계산하여 CSV 파일로 자동 로깅합니다.
- **Glassmorphism 웹 데모 UI:** 초현대적인 다크 모드 기반의 바닐라 JS 프론트엔드가 내장되어 있으며, Gemini 끄기/켜기 토글 및 RAG 파라미터(Top-K, Threshold)를 실시간으로 조작할 수 있습니다.

## 🛠 기술 스택 (Tech Stack)

- **Backend Framework:** FastAPI (Python 3.11)
- **Vector Database:** Weaviate (Docker)
- **Relational Database:** MariaDB
- **LLM Engine:** Google Gemini Pro
- **Embedding Model:** KR-SBERT
- **Frontend:** Vanilla HTML5 / CSS3 / JavaScript

## ⚙️ 설치 및 실행 방법 (Getting Started)

### 1. 환경 설정
Python 3.11 가상환경을 생성하고 의존성 패키지를 설치합니다.
```bash
python -m venv .venv
source .venv/Scripts/activate  # Windows의 경우
pip install -r requirements.txt
```

### 2. 환경 변수 구성
루트 경로에 `.env.local` 파일을 생성하고 아래와 같은 형태로 설정값을 기입합니다.
```env
GEMINI_API_KEY=your_gemini_api_key
WEAVIATE_URL=http://localhost:8080
MARIADB_URI=mysql+pymysql://user:password@host:port/dbname
```

### 3. Vector DB 구동 (Weaviate)
Docker Desktop을 실행한 뒤, Weaviate 컨테이너를 구동해야 합니다. 
*(프로젝트 내에 제공된 docker run 명령어나 docker-compose.yml을 참고하세요.)*

### 4. 서버 구동
아래 명령어를 통해 FastAPI 백엔드 서버를 구동합니다.
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. UI 시연
브라우저를 열고 다음 주소에 접속하면 즉시 데모 화면을 테스트할 수 있습니다.
- **접속 주소:** `http://localhost:8000/`

## 📁 디렉토리 구조 (Directory Structure)

```text
chat_bot_t/
├── app/
│   ├── api/v1/        # FastAPI 라우터 및 엔드포인트
│   ├── core/          # DI, Config, Logger 등 공통 모듈
│   ├── data/          # 로더(Loader), Ingestion 파이프라인
│   ├── db/            # RDB 세션 및 Connection Pool 관리
│   ├── schemas/       # Pydantic 기반 Request/Response 모델
│   ├── services/      # RAG, Gemini, Vector Store, History 서비스 로직
│   └── static/        # 데모 UI용 HTML, CSS, JS 파일
├── data/
│   ├── raw/           # 업로드된 원본 문서 임시 저장소
│   ├── processed/     # Chunking 결과물(Cache JSON) 저장소
│   └── history/       # 토큰 및 응답 속도 CSV 로그 저장소
├── plan/              # 개발자 보고서 및 시연 준비서 (Markdown)
├── .env.local         # 환경 변수 파일 (Git 제외)
└── README.md
```

