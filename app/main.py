import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app.core.logger import get_logger
from app.api.v1 import api_router
from app.core.config import settings

log = get_logger(__name__)
app = FastAPI(
    title = "RAG Chatbot API",
    description="챗봇 테스트 프로젝트",
    version="0.0.1"
)
app.include_router(api_router)

# ── 정적 파일(UI) 서빙 ──────────────────────────────────────────────────────────
static_dir = Path("app/static")
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/", summary="챗봇 UI 화면")
async def serve_index():
    return FileResponse("app/static/index.html")

@app.get("/health")
def read_root():
    return {
        "status" : "200",
        "message": "서버 정상 실행"
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
    )