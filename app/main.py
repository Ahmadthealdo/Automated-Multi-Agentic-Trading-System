import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings, BASE_DIR, FRONTEND_DIR
from app.core.telemetry import init_telemetry
from app.db import run_startup_migrations, close_db_engine
from app.api.v1.router import api_router
from app.api.views import views_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager: sets up telemetry and runs startup DB migrations."""
    # 1. Initialize distributed tracing and telemetry
    init_telemetry()

    # 2. Run non-destructive database migrations
    await run_startup_migrations()

    yield
    # 3. Cleanly dispose database connection engine
    await close_db_engine()
    print("🛑 [Application Shutdown] FastAPI multi-agent gateway shutting down cleanly.")

def create_app() -> FastAPI:
    """Application factory for the Automated Multi-Agentic Trading System."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description=settings.DESCRIPTION,
        lifespan=lifespan
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )

    # Mount static assets from front-end/static
    static_dir = FRONTEND_DIR / "static" if (FRONTEND_DIR / "static").exists() else BASE_DIR / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Register Routers
    app.include_router(views_router)
    app.include_router(api_router, prefix="/api")

    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 75)
    print("      AUTOMATED MULTI-AGENTIC QUANTITATIVE TRADING DESK GATEWAY")
    print("=" * 75)
    print("Booting Asynchronous FastAPI Web Server & Multi-Agent Cognitive Gateway...")
    print(f"Access the Dashboard at: http://{settings.SERVER_HOST}:{settings.SERVER_PORT}")
    print("=" * 75 + "\n")
    uvicorn.run("app.main:app", host=settings.SERVER_HOST, port=settings.SERVER_PORT, reload=False, log_level="info")
