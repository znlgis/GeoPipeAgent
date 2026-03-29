"""GeoPipeAgent Web UI - FastAPI Backend."""
import os
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .routers import pipeline, llm, export, skill

logger = logging.getLogger(__name__)

app = FastAPI(
    title="GeoPipeAgent Web UI",
    description="Web interface for GeoPipeAgent GIS pipeline framework",
    version="1.0.0",
)

# CORS — restrict origins via GEOPIPE_CORS_ORIGINS env var (comma-separated).
# Defaults to localhost dev servers; set to "*" only for local development.
_default_origins = "http://localhost:5173,http://localhost:3000"
_cors_origins = os.environ.get("GEOPIPE_CORS_ORIGINS", _default_origins).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global error handler ─────────────────────────────────────────────────────


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all handler for unhandled exceptions."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error_code": "INTERNAL_ERROR",
        },
    )


# Register routers
app.include_router(pipeline.router)
app.include_router(llm.router)
app.include_router(export.router)
app.include_router(skill.router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "GeoPipeAgent Web UI"}


# Serve frontend static files in production (must be LAST — catches all unmatched paths)
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
