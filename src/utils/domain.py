"""Detect career domain from CV / profile text so searches stay on-topic."""

from __future__ import annotations

from src.utils.schemas import CandidateProfile

# TopJobs.lk functional area codes
TOPJOBS_FA = {
    "education": "TAL",
    "marketing": "SMM",
    "sales": "SMM",
    "it": "SDQ",
    "hr": "HRS",  # may vary; All Vacancies used if unknown
    "general": "",
}

DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "education": [
        "teacher", "teaching", "tutor", "lecturer", "instructor", "educator",
        "mathematics", "math teacher", "english teacher", "science teacher",
        "primary teacher", "secondary teacher", "school", "classroom",
        "lesson plan", "curriculum", "pedagogy", "students", "o/l", "a/l",
        "sinhala teacher", "history teacher", "commerce teacher",
    ],
    "marketing": [
        "marketing", "digital marketing", "brand", "seo", "sem", "social media",
        "content marketing", "campaign", "market research", "advertising",
        "copywriting", "google ads", "facebook ads", "branding",
    ],
    "sales": [
        "sales executive", "sales manager", "business development", "b2b sales",
        "account executive", "retail sales",
    ],
    "it": [
        "software engineer", "developer", "programmer", "full stack", "backend",
        "frontend", "devops", "qa engineer", "data engineer", "react", "python",
        "java", "fastapi", "docker", "kubernetes", "api", "github",
    ],
    "hr": [
        "human resources", "hr executive", "recruitment", "talent acquisition",
        "payroll", "hr manager",
    ],
    "finance": [
        "accountant", "accounting", "finance", "audit", "bookkeeping", "cashier",
    ],
}


def detect_domain_from_text(text: str) -> str:
    lower = (text or "").lower()
    scores: dict[str, int] = {k: 0 for k in DOMAIN_KEYWORDS}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                scores[domain] += 1 if " " in kw else 1
                # stronger weight for multi-word phrases
                if " " in kw:
                    scores[domain] += 1

    best = max(scores, key=scores.get)
    if scores[best] <= 0:
        return "general"
    return best


def detect_domain_from_profile(profile: CandidateProfile) -> str:
    blob = " ".join(
        [
            " ".join(profile.preferred_roles),
            " ".join(profile.skills),
            profile.experience_summary,
            profile.education,
        ]
    )
    return detect_domain_from_text(blob)


def topjobs_fa_for_domain(domain: str) -> str:
    return TOPJOBS_FA.get(domain, "")


def default_roles_for_domain(domain: str, cv_text: str = "") -> list[str]:
    lower = cv_text.lower()
    if domain == "education":
        roles = []
        if "math" in lower or "mathematics" in lower:
            roles.append("Mathematics Teacher")
        if "english" in lower:
            roles.append("English Teacher")
        if "science" in lower:
            roles.append("Science Teacher")
        if "marketing" in lower and "teacher" in lower:
            roles.append("Marketing Teacher")
        if not roles:
            if "teacher" in lower:
                roles.append("Teacher")
            else:
                roles.append("Teacher")
        return roles[:4]
    if domain == "marketing":
        return ["Marketing Executive", "Digital Marketing Specialist"]
    if domain == "sales":
        return ["Sales Executive"]
    if domain == "hr":
        return ["HR Executive"]
    if domain == "finance":
        return ["Accountant"]
    if domain == "it":
        return ["Software Engineer"]
    return ["Job Seeker"]


def is_tech_domain(domain: str) -> bool:
    return domain == "it"
