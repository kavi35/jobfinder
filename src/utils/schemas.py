"""Pydantic models shared across agents and tools."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


JobSource = Literal["linkedin", "topjobs", "xpressjobs", "fallback"]


class CandidateProfile(BaseModel):
    name: str = "Candidate"
    skills: list[str] = Field(default_factory=list)
    experience_years: float = 0.0
    experience_summary: str = ""
    education: str = ""
    preferred_roles: list[str] = Field(default_factory=list)


class RawJob(BaseModel):
    title: str
    company: str = "Unknown"
    location: str = "Sri Lanka"
    description: str = ""
    source: JobSource
    apply_url: str
    job_id: str = ""


class JobMatch(BaseModel):
    title: str
    company: str
    location: str
    description: str
    source: JobSource
    apply_url: str
    job_id: str = ""
    match_score: int = Field(ge=0, le=100)
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    feedback: str = ""


class PipelineResult(BaseModel):
    profile: CandidateProfile
    matches: list[JobMatch] = Field(default_factory=list)
    search_query: str = ""
    sources_used: list[str] = Field(default_factory=list)
    sources_failed: list[str] = Field(default_factory=list)
