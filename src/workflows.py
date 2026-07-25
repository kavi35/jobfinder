"""Pipeline orchestration: PDF -> parse -> search -> score -> results."""

from __future__ import annotations

from src.agents.parser_agent import parse_cv
from src.agents.scorer_agent import score_jobs
from src.agents.search_agent import build_search_query, find_jobs
from src.utils.pdf_parser import extract_text_from_pdf
from src.utils.schemas import PipelineResult


def run_pipeline(pdf_bytes: bytes, max_score_jobs: int = 8) -> PipelineResult:
    """
    Full multi-agent pipeline:
    1. Extract CV text
    2. Parse candidate profile
    3. Search LinkedIn / TopJobs / XpressJobs (+ fallback)
    4. Score top jobs
    """
    cv_text = extract_text_from_pdf(pdf_bytes)
    profile = parse_cv(cv_text)
    query = build_search_query(profile)
    jobs, sources_used, sources_failed = find_jobs(profile, query=query)

    # Limit scoring for latency/cost
    to_score = jobs[:max_score_jobs]
    matches = score_jobs(profile, to_score) if to_score else []

    return PipelineResult(
        profile=profile,
        matches=matches,
        search_query=query,
        sources_used=sources_used,
        sources_failed=sources_failed,
    )
