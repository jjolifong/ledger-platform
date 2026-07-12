"""FastAPI 앱 진입점. API 라우터 + (배포 시) React dist 정적 서빙."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.auth.router import router as auth_router
from app.ledger.router import router as ledger_router
from app.users.router import router as users_router

# backend/app/main.py → 프로젝트 루트/frontend/dist
DIST_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

app = FastAPI(title="대장관리 플랫폼")
app.include_router(auth_router)
app.include_router(ledger_router)
app.include_router(users_router)


def _mount_frontend() -> None:
    if not DIST_DIR.is_dir():
        return

    assets_dir = DIST_DIR / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/")
    async def serve_index() -> FileResponse:
        return FileResponse(DIST_DIR / "index.html")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str) -> FileResponse:
        # /api/* 는 위 라우터가 우선 처리. 여기에는 API가 아닌 경로만 온다.
        candidate = (DIST_DIR / full_path).resolve()
        try:
            candidate.relative_to(DIST_DIR.resolve())
        except ValueError:
            return FileResponse(DIST_DIR / "index.html")

        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(DIST_DIR / "index.html")


_mount_frontend()
