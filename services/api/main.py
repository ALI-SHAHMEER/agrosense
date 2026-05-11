"""
AgroSense API — FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from core.config import settings
from core.database import engine, Base
from core.logging import setup_logging

# ── Route imports ─────────────────────────────────────────────
from routes import auth, farms, fields, imagery, predictions, health


# ── Lifespan (startup / shutdown) ─────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs on startup and shutdown."""
    setup_logging()

    # Create DB tables if they don't exist (migrations handle schema changes)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("✓ AgroSense API started")
    yield
    print("AgroSense API shutting down...")


# ── App instance ──────────────────────────────────────────────
app = FastAPI(
    title="AgroSense API",
    description=(
        "Satellite-Based AI Crop Monitoring System for Pakistan.\n\n"
        "Processes Sentinel-2 & Landsat-8 imagery to deliver crop stress detection, "
        "precision irrigation, yield prediction, and soil assessment."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ── Middleware ────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


# ── Routers ───────────────────────────────────────────────────
app.include_router(health.router,       tags=["Health"])
app.include_router(auth.router,         prefix="/auth",        tags=["Authentication"])
app.include_router(farms.router,        prefix="/farms",       tags=["Farms"])
app.include_router(fields.router,       prefix="/fields",      tags=["Fields"])
app.include_router(imagery.router,      prefix="/imagery",     tags=["Satellite Imagery"])
app.include_router(predictions.router,  prefix="/predictions", tags=["ML Predictions"])


# ── Global exception handler ──────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )
