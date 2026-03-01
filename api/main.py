"""FastAPI application — entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import get_settings
from api.routes import admin, analysis, auth, signals, systems, users

import strategy_engine

_settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup / shutdown lifecycle."""
    # On startup — could initialise DB pool, warm caches, etc.
    yield
    # On shutdown — cleanup
    from api.database import engine
    await engine.dispose()


app = FastAPI(
    title=_settings.app_name,
    version=strategy_engine.__version__,
    description="Quantitative allocation signal platform — open-source engine, proprietary API.",
    lifespan=lifespan,
    docs_url="/docs" if _settings.debug else None,
    redoc_url="/redoc" if _settings.debug else None,
)

# ─── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routes ───────────────────────────────────────────────────────────────────

app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(systems.router, prefix="/api/v1")
app.include_router(signals.router, prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")


@app.get("/api/v1/health")
async def health():
    return {
        "status": "ok",
        "version": strategy_engine.__version__,
        "environment": _settings.environment,
    }
