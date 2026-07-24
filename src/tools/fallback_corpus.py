"""Offline fallback: search local data/jobs_corpus when live sites fail."""

from __future__ import annotations

from pathlib import Path

from src.tools.http_utils import make_job_id
from src.utils.schemas import RawJob

CORPUS_DIR = Path(__file__).resolve().parents[2] / "data" / "jobs_corpus"


def search_fallback(query: str, limit: int = 8) -> list[RawJob]:
    tokens = [t.lower() for t in query.replace(",", " ").split() if len(t) > 2]
    scored: list[tuple[int, RawJob]] = []

    for path in sorted(CORPUS_DIR.glob("job_*.txt")):
        text = path.read_text(encoding="utf-8")
        meta = _parse_header(text)
        blob = text.lower()
        score = sum(1 for t in tokens if t in blob) if tokens else 1
        if score <= 0:
            continue

        apply_url = (
            "https://www.topjobs.lk/applicant/vacancybyfunctionalarea.jsp"
            f"?FA=SDQ&jst=OPEN&txtKeyWord={meta['title'].replace(' ', '+')}"
        )
        job = RawJob(
            title=meta["title"],
            company=meta["company"],
            location=meta["location"],
            description=text,
            source="fallback",
            apply_url=apply_url,
            job_id=make_job_id("fallback", meta["title"], meta["company"]),
        )
        scored.append((score, job))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [job for _, job in scored[:limit]]


def _parse_header(text: str) -> dict[str, str]:
    meta = {
        "title": "Unknown Role",
        "company": "Local Corpus",
        "location": "Sri Lanka",
    }
    for line in text.splitlines()[:10]:
        if line.startswith("Title:"):
            meta["title"] = line.replace("Title:", "", 1).strip()
        elif line.startswith("Company:"):
            meta["company"] = line.replace("Company:", "", 1).strip()
        elif line.startswith("Location:"):
            meta["location"] = line.replace("Location:", "", 1).strip()
    return meta
