"""PDF Parser Agent — CV text -> CandidateProfile (DeepSeek)."""

from __future__ import annotations

import json
import re

from src.utils.domain import (
    default_roles_for_domain,
    detect_domain_from_text,
)
from src.utils.schemas import CandidateProfile

SYSTEM_PROMPT = """You are a CV parsing agent.
Extract a structured candidate profile from the CV text.
Return ONLY valid JSON with these keys:
- name (string)
- skills (array of strings)
- experience_years (number)
- experience_summary (short string)
- education (string)
- preferred_roles (array of job titles the candidate likely wants)

CRITICAL RULES:
- preferred_roles MUST match the candidate's actual field (e.g. Mathematics Teacher,
  English Teacher, Marketing Executive, Accountant). 
- NEVER invent Software Engineer / Developer roles unless the CV clearly shows
  software/IT engineering experience or skills.
- For teachers: include the subject (Math, English, Science, etc.) in the role title.
- Skills should match the domain (teaching methods, subjects, marketing tools, etc.).
Do not wrap the JSON in markdown."""

SKILL_HINTS = [
    # IT
    "python", "java", "javascript", "typescript", "react", "node", "fastapi",
    "django", "flask", "sql", "postgresql", "mysql", "mongodb", "aws", "azure",
    "docker", "kubernetes", "git", "linux", "html", "css", "angular", "vue",
    # Teaching / soft
    "lesson planning", "classroom management", "curriculum", "assessment",
    "mathematics", "english literature", "grammar", "pedagogy", "tutoring",
    # Marketing
    "seo", "sem", "google ads", "facebook ads", "content writing", "branding",
    "social media", "market research", "copywriting", "canva",
    # General
    "excel", "powerpoint", "communication", "leadership", "ms office",
]


def parse_cv(cv_text: str) -> CandidateProfile:
    try:
        from src.utils.models import get_fast_llm

        llm = get_fast_llm()
        prompt = f"{SYSTEM_PROMPT}\n\nCV TEXT:\n{cv_text[:12000]}\n\nJSON:"
        response = llm.invoke(prompt)
        content = getattr(response, "content", str(response))
        data = _parse_json(content)
        profile = CandidateProfile.model_validate(data)
        return _sanitize_profile(profile, cv_text)
    except Exception:
        return _heuristic_profile(cv_text)


def _sanitize_profile(profile: CandidateProfile, cv_text: str) -> CandidateProfile:
    """Stop IT role hallucination when the CV is clearly non-tech."""
    domain = detect_domain_from_text(cv_text)
    if domain != "it":
        it_words = ("software", "developer", "devops", "full stack", "backend", "frontend", "programmer")
        cleaned_roles = [
            r for r in profile.preferred_roles
            if not any(w in r.lower() for w in it_words)
        ]
        if not cleaned_roles:
            cleaned_roles = default_roles_for_domain(domain, cv_text)
        profile.preferred_roles = cleaned_roles
    elif not profile.preferred_roles:
        profile.preferred_roles = default_roles_for_domain("it", cv_text)
    return profile


def _heuristic_profile(cv_text: str) -> CandidateProfile:
    lower = cv_text.lower()
    domain = detect_domain_from_text(cv_text)

    skills: list[str] = []
    for s in SKILL_HINTS:
        if s in lower:
            skills.append(s.title())

    years = 0.0
    m = re.search(r"(\d+)\+?\s*\+?\s*years?", lower)
    if m:
        years = float(m.group(1))

    roles = default_roles_for_domain(domain, cv_text)

    name = "Candidate"
    first_line = cv_text.strip().splitlines()[0].strip() if cv_text.strip() else ""
    if first_line and len(first_line) < 60 and "@" not in first_line:
        name = first_line

    edu = ""
    for line in cv_text.splitlines():
        if any(k in line.lower() for k in ("bsc", "bachelor", "degree", "diploma", "university", "hnd", "pgde", "bed")):
            edu = line.strip()
            break

    return CandidateProfile(
        name=name,
        skills=skills[:15],
        experience_years=years,
        experience_summary=cv_text[:400].replace("\n", " "),
        education=edu,
        preferred_roles=roles[:4],
    )


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
        raise ValueError(f"Could not parse profile JSON from model output: {text[:300]}")
