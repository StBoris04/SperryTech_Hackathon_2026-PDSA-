from fastapi import FastAPI, HTTPException
import psycopg

from api_models import (
    ErrorResponse,
    HealthResponse,
    OpportunitiesResponse,
    ProjectsResponse,
)
from db import get_opportunities as fetch_opportunities
from db import get_projects as fetch_projects

app = FastAPI(title="GridLock")


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
