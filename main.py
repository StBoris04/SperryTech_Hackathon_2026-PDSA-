import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import psycopg

from api_models import (
    ErrorResponse,
    HealthResponse,
    OpportunitiesResponse,
    ProjectsResponse,
)
from db import get_opportunities as fetch_opportunities
from db import get_projects as fetch_projects
from recommendations.engine import build_recommendations, index_projects

app = FastAPI(title="GridLock")

# Browsers block cross-origin reads unless the API allows the frontend origin.
# Comma-separated; defaults to the local Vite dev server.
DEFAULT_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("GRIDLOCK_CORS_ORIGINS", DEFAULT_CORS_ORIGINS).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET"],
    allow_headers=[],
)


@app.get("/health", response_model=HealthResponse)
def health():
    return {"status": "ok"}


@app.get(
    "/projects",
    response_model=ProjectsResponse,
    responses={503: {"model": ErrorResponse}},
)
def get_projects():
    try:
        projects = fetch_projects()
    except (psycopg.Error, RuntimeError):
        raise HTTPException(
            status_code=503,
            detail="Project data is temporarily unavailable.",
        ) from None

    return {
        "schema_version": "1.0",
        "projects": projects,
    }


@app.get(
    "/opportunities",
    response_model=OpportunitiesResponse,
    responses={503: {"model": ErrorResponse}},
)
def get_opportunities():
    try:
        opportunities = fetch_opportunities()
    except (psycopg.Error, RuntimeError):
        raise HTTPException(
            status_code=503,
            detail="Opportunity data is temporarily unavailable.",
        ) from None

    return {"schema_version": "1.0", "opportunities": opportunities}


@app.get(
    "/recommendations",
    responses={503: {"model": ErrorResponse}},
)
def get_recommendations():
    """Explain deterministic project pairs without creating new matches."""
    try:
        projects = fetch_projects()
        opportunities = fetch_opportunities()
        return build_recommendations(
            opportunities,
            index_projects({"projects": projects}),
        )
    except (psycopg.Error, RuntimeError):
        raise HTTPException(
            status_code=503,
            detail="Recommendation data is temporarily unavailable.",
        ) from None
