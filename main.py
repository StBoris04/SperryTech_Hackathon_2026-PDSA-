from fastapi import FastAPI
import json
from pathlib import Path
from db import get_projects as fetch_projects
from fastapi import HTTPException
import psycopg

app = FastAPI(title="GridLock")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/projects")
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