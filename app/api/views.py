import os
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from app.core.config import BASE_DIR, FRONTEND_DIR

views_router = APIRouter(tags=["Frontend Views"])

@views_router.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serves the primary Single Page Application HTML portal."""
    html_path = FRONTEND_DIR / "index.html" if (FRONTEND_DIR / "index.html").exists() else BASE_DIR / "index.html"
    if html_path.exists():
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()
        return HTMLResponse(content=content)
    return HTMLResponse(content="<h1>Dashboard index.html not found in front-end/</h1>", status_code=404)
