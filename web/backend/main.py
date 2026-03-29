"""GeoPipeAgent Web UI - FastAPI Backend."""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .routers import pipeline, llm, export

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

# Register routers
app.include_router(pipeline.router)
app.include_router(llm.router)
app.include_router(export.router)

# Serve frontend static files in production
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "GeoPipeAgent Web UI"}
