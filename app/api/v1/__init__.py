from fastapi import APIRouter

from app.api.v1.routes import chat, documents

api_router = APIRouter(prefix="/api/v1")

# ── 라우터 등록 ───────────────────────────────────────────────────────────────
api_router.include_router(chat.router)       # /api/v1/chat/
api_router.include_router(documents.router)  # /api/v1/documents/

# 추가 라우터가 생기면 여기에 include_router를 추가
# api_router.include_router(image.router)
