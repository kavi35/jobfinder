"""Scorer Agent — match score, missing skills, feedback (OpenRouter)."""

from __future__ import annotations

import json
import re

from src.utils.schemas import CandidateProfile, JobMatch, RawJob

SCORE_PROMPT = """You are a job-fit evaluation agent.
Compare the candidate profile to the job posting.
Return ONLY valid JSON with:
- match_score (integer 0-100)
- matched_skills (array of strings)
- missing_skills (array of strings)
- feedback (2-3 sentences of actionable advice)

CRITICAL:
- If domains mismatch (e.g. Mathematics/English Teacher vs Software Engineer),
  give a LOW score (0-25) and explain the mismatch.
- Never give high scores to IT/software jobs for teaching or marketing CVs
  unless the CV clearly has that IT experience.
Be honest. Do not inflate scores when core skills are missing."""

REFLECT_PROMPT = """You previously scored this job match.
Review whether the score overstates fit given missing_skills.
If the score is too high, lower it. Return ONLY JSON:
- match_score (integer 0-100)
- matched_skills (array)
- missing_skills (array)
- feedback (string)"""


def score_job(profile: CandidateProfile, job: RawJob) -> JobMatch:
    try:
        from src.utils.models import get_reasoner_llm

        llm = get_reasoner_llm()
        first = _ask_score(llm, SCORE_PROMPT, profile, job)
        data = _ask_reflect(llm, first, profile, job)
    except Exception:
        data = _heuristic_score(profile, job)

    return JobMatch(
        title=job.title,
        company=job.company,
        location=job.location,
        description=job.description,
        source=job.source,
        apply_url=job.apply_url,
        job_id=job.job_id,
        match_score=int(max(0, min(100, data.get("match_score", 0)))),
        matched_skills=list(data.get("matched_skills") or []),
        missing_skills=list(data.get("missing_skills") or []),
        feedback=str(data.get("feedback") or ""),
    )


def score_jobs(profile: CandidateProfile, jobs: list[RawJob]) -> list[JobMatch]:
    matches = [score_job(profile, job) for job in jobs]
    matches.sort(key=lambda m: m.match_score, reverse=True)
    return matches


def _heuristic_score(profile: CandidateProfile, job: RawJob) -> dict:
    from src.utils.domain import detect_domain_from_profile, detect_domain_from_text

    job_blob = f"{job.title} {job.description}".lower()
    is_search_link = "search:" in job.title.lower() or "roles on linkedin" in job.title.lower()
    cand_domain = detect_domain_from_profile(profile)
    job_domain = detect_domain_from_text(job_blob)

    matched = [s for s in profile.skills if s.lower() in job_blob]
    role_bonus = any(r.lower() in job.title.lower() for r in profile.preferred_roles)

    if is_search_link:
        base = 55 + (10 if role_bonus else 0)
        feedback = (
            "This is a live search link on the job board. "
            "Open it to browse current openings matching your profile."
        )
        return {
            "match_score": min(70, base),
            "matched_skills": profile.skills[:3],
            "missing_skills": [],
            "feedback": feedback,
        }

    # Hard penalty for domain mismatch (teacher vs software, etc.)
    if (
        cand_domain not in {"general", "it"}
        and job_domain == "it"
        and cand_domain != job_domain
    ):
        return {
            "match_score": 12,
            "matched_skills": matched,
            "missing_skills": profile.preferred_roles[:3],
            "feedback": (
                f"Domain mismatch: your profile looks like {cand_domain}, "
                f"but this job is IT/software. Prefer roles such as "
                f"{', '.join(profile.preferred_roles) or cand_domain}."
            ),
        }

    base = 35 + min(45, len(matched) * 10) + (15 if role_bonus else 0)
    missing = []
    for token in ["python", "java", "sql", "react", "aws", "docker", "kubernetes", "degree"]:
        if token in job_blob and not any(token == s.lower() for s in profile.skills):
            missing.append(token.upper() if token in {"sql", "aws"} else token.title())
    feedback = (
        f"Heuristic score based on {len(matched)} overlapping skills"
        + (" and role title alignment." if role_bonus else ".")
        + " Add a real DeepSeek API key for richer LLM feedback."
    )
    return {
        "match_score": min(95, base),
        "matched_skills": matched,
        "missing_skills": missing[:6],
        "feedback": feedback,
    }


def _ask_score(llm, system: str, profile: CandidateProfile, job: RawJob) -> dict:
    prompt = (
        f"{system}\n\nCANDIDATE:\n{profile.model_dump_json(indent=2)}\n\n"
        f"JOB:\n{job.model_dump_json(indent=2)}\n\nJSON:"
    )
    response = llm.invoke(prompt)
    content = getattr(response, "content", str(response))
    return _parse_json(content)


def _ask_reflect(llm, previous: dict, profile: CandidateProfile, job: RawJob) -> dict:
    prompt = (
        f"{REFLECT_PROMPT}\n\nPREVIOUS_SCORE_JSON:\n{json.dumps(previous)}\n\n"
        f"CANDIDATE_SKILLS:\n{profile.skills}\n\n"
        f"JOB_TITLE:\n{job.title}\n\nJSON:"
    )
    try:
        response = llm.invoke(prompt)
        content = getattr(response, "content", str(response))
        return _parse_json(content)
    except Exception:
        return previous


def _parse_json(text: str) -> dict:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise ValueError(f"Could not parse score JSON: {text[:300]}")
