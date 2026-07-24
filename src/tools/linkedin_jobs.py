"""LinkedIn Jobs tool — public search deep-links (no HTML scrape)."""

from __future__ import annotations

from src.tools.http_utils import encode_query, make_job_id
from src.utils.schemas import RawJob


def search_linkedin_jobs(query: str, location: str = "Sri Lanka", limit: int = 5) -> list[RawJob]:
    """
    LinkedIn blocks scrapers, so we return searchable apply/search links
    the candidate can open, tagged as LinkedIn source for the UI.
    """
    q = query.strip() or "software engineer"
    loc = location.strip() or "Sri Lanka"
    search_url = (
        "https://www.linkedin.com/jobs/search/"
        f"?keywords={encode_query(q)}&location={encode_query(loc)}"
    )

    roles = [part.strip() for part in re_split_roles(q)][:limit] or [q]
    jobs: list[RawJob] = []
    for role in roles[:limit]:
        url = (
            "https://www.linkedin.com/jobs/search/"
            f"?keywords={encode_query(role)}&location={encode_query(loc)}"
        )
        jobs.append(
            RawJob(
                title=f"{role.title()} roles on LinkedIn",
                company="LinkedIn Jobs",
                location=loc,
                description=(
                    f"Open LinkedIn Jobs search for '{role}' in {loc}. "
                    "Browse live openings and apply on LinkedIn."
                ),
                source="linkedin",
                apply_url=url,
                job_id=make_job_id("linkedin", role, loc),
            )
        )

    if not jobs:
        jobs.append(
            RawJob(
                title=f"Search: {q}",
                company="LinkedIn Jobs",
                location=loc,
                description=f"LinkedIn Jobs search for '{q}' in {loc}.",
                source="linkedin",
                apply_url=search_url,
                job_id=make_job_id("linkedin", q, loc),
            )
        )
    return jobs


def re_split_roles(query: str) -> list[str]:
    parts = [p.strip() for p in query.replace("|", ",").split(",") if p.strip()]
    if len(parts) <= 1:
        # Fall back to whole query as one role
        return [query.strip()] if query.strip() else ["software engineer"]
    return parts
