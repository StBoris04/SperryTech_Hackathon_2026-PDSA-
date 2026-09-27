"""The v1 HTTP handoff documented in context.md."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Source(ContractModel):
    reference: str
    locator: str
    supports: list[str]


class Project(ContractModel):
    project_id: str
    utility_id: Literal["dominion_sc", "georgia_power"]
    project_name: str
    project_type: Literal["transmission_line", "substation", "other", "unknown"]
    state: str | None
    description: str | None
    location_text: str | None
    latitude: float | None
    longitude: float | None
    location_quality: Literal["verified", "approximate", "unknown"]
    location_method: str | None
    construction_start: str | None
    construction_end: str | None
    in_service_date: str | None
    schedule_text: str | None
    sources: list[Source]
    review_status: Literal["needs_review", "validated"]
    notes: str | None


class ProjectsResponse(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    projects: list[Project]


class Opportunity(ContractModel):
    project_id_a: str
    project_id_b: str
    distance_miles: float
    distance_method: Literal["postgis_geography"]
    location_uncertain: bool
    timeline_status: Literal["overlap", "unknown", "no_overlap"]
    reason: str


class OpportunitiesResponse(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    opportunities: list[Opportunity]


class HealthResponse(ContractModel):
    status: Literal["ok"]


class ErrorResponse(ContractModel):
    detail: str
