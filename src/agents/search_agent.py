"""Search Agent — build query, call LinkedIn/TopJobs/XpressJobs, dedupe."""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.tools.fallback_corpus import search_fallback
from src.tools.linkedin_jobs import search_linkedin_jobs
from src.tools.topjobs import search_topjobs
from src.tools.xpressjobs import search_xpressjobs
from src.utils.domain import detect_domain_from_profile, is_tech_domain, topjobs_fa_for_domain
from src.utils.schemas import CandidateProfile, RawJob


def build_search_query(profile: CandidateProfile) -> str:
    roles = profile.preferred_roles[:2]
    if not roles:
        domain = detect_domain_from_profile(profile)
        roles = [domain.replace("_", " ").title() + " roles"]
    skills = profile.skills[:5]
    parts = list(roles) + skills
    seen: set[str] = set()
    ordered: list[str] = []
    for p in parts:
        key = p.lower().strip()
        if key and key not in seen:
            seen.add(key)
            ordered.append(p.strip())
    return " ".join(ordered[:8])


def build_board_query(profile: CandidateProfile) -> str:
    """Shorter query works better on TopJobs / XpressJobs keyword search."""
    if profile.preferred_roles:
        role = profile.preferred_roles[0].strip()
    else:
        role = detect_domain_from_profile(profile)
    # Prefer role only for non-IT (skills like "Excel" shouldn't dilute "English Teacher")
    domain = detect_domain_from_profile(profile)
    if domain == "it" and profile.skills:
        skill = profile.skills[0]
        if skill.lower() not in role.lower():
            return f"{role} {skill}"
    return role


def find_jobs(
    profile: CandidateProfile,
    query: str | None = None,
    per_source: int = 6,
    max_jobs: int = 18,
) -> tuple[list[RawJob], list[str], list[str]]:
    """
    Returns (jobs, sources_used, sources_failed).
    Uses live tools in parallel; falls back to local corpus only for IT profiles.
    """
    display_query = query or build_search_query(profile)
    board_query = build_board_query(profile)
    domain = detect_domain_from_profile(profile)
    fa = topjobs_fa_for_domain(domain)

    sources_used: list[str] = []
    sources_failed: list[str] = []
    collected: list[RawJob] = []

    tool_map = {
        "linkedin": lambda: search_linkedin_jobs(display_query, limit=min(3, per_source)),
        "topjobs": lambda: search_topjobs(board_query, limit=per_source, fa=fa),
        "xpressjobs": lambda: search_xpressjobs(board_query, limit=per_source),
    }

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(fn): name for name, fn in tool_map.items()}
        for fut in as_completed(futures):
            name = futures[fut]
            try:
                jobs = fut.result()
                if jobs:
                    collected.extend(jobs)
                    sources_used.append(name)
                else:
                    sources_failed.append(name)
            except Exception:
                sources_failed.append(name)

    # Filter obvious domain mismatches (e.g. teacher CV vs random IT listing)
    collected = _filter_by_domain(collected, domain, profile)

    live_concrete = [
        j
        for j in collected
        if j.source in {"topjobs", "xpressjobs"} and "search:" not in j.title.lower()
    ]
    # IT-only local corpus — never use it for teachers/marketing CVs
    if not live_concrete and is_tech_domain(domain):
        fallback = search_fallback(display_query, limit=per_source)
        collected.extend(fallback)
        if fallback:
            sources_used.append("fallback")
        elif "fallback" not in sources_failed:
            sources_failed.append("fallback")

    deduped = _dedupe_jobs(collected)
    return deduped[:max_jobs], sources_used, sources_failed


def _filter_by_domain(
    jobs: list[RawJob],
    domain: str,
    profile: CandidateProfile,
) -> list[RawJob]:
    if domain in {"general", "it"}:
        return jobs

    keep: list[RawJob] = []
    role_tokens = [r.lower() for r in profile.preferred_roles]
    domain_tokens = {
        "education": ["teacher", "tutor", "lecturer", "instructor", "education", "school", "academic"],
        "marketing": ["marketing", "brand", "seo", "digital", "content", "advertis"],
        "sales": ["sales", "business development", "account"],
        "hr": ["hr", "human resource", "recruit"],
        "finance": ["account", "finance", "audit", "bookkeep"],
    }.get(domain, [domain])

    it_only = ["software engineer", "devops", "full stack", "backend developer", "frontend developer", "java/", "react native"]

    for job in jobs:
        # Always keep board search deep-links for the user's query
        if "search:" in job.title.lower() or "roles on linkedin" in job.title.lower():
            keep.append(job)
            continue

        blob = f"{job.title} {job.description}".lower()
        if any(tok in blob for tok in domain_tokens) or any(r in blob for r in role_tokens):
            keep.append(job)
            continue
        # Drop clear IT noise for non-IT candidates
        if any(bad in blob for bad in it_only):
            continue
        # Keep other non-IT jobs from the right category (may still be relevant)
        keep.append(job)

    return keep or jobs


def _dedupe_jobs(jobs: list[RawJob]) -> list[RawJob]:
    best: dict[str, RawJob] = {}
    for job in jobs:
        key = _normalize_key(job.title, job.company)
        existing = best.get(key)
        if existing is None or len(job.description) > len(existing.description):
            best[key] = job
    return list(best.values())


def _normalize_key(title: str, company: str) -> str:
    raw = f"{title} {company}".lower()
    return re.sub(r"[^a-z0-9]+", "", raw)
