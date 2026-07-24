"""XpressJobs live fetch + parse tool."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from src.tools.http_utils import clean_text, encode_query, fetch_html, make_job_id
from src.utils.schemas import RawJob

BASE = "https://xpress.jobs"
SEARCH_URL = BASE + "/Jobs?Keywords={query}"


def search_xpressjobs(query: str, limit: int = 8) -> list[RawJob]:
    url = SEARCH_URL.format(query=encode_query(query.strip() or "software"))
    try:
        html = fetch_html(url, timeout=25.0)
    except Exception:
        # Site can be slow/timeout — return search deep-link
        return [
            RawJob(
                title=f"XpressJobs search: {query}",
                company="XpressJobs",
                location="Sri Lanka",
                description=f"Open XpressJobs listings for '{query}'.",
                source="xpressjobs",
                apply_url=url,
                job_id=make_job_id("xpressjobs", query, "search"),
            )
        ]

    soup = BeautifulSoup(html, "lxml")
    jobs: list[RawJob] = []

    # Try common card / article / link patterns
    candidates = []
    for selector in [
        "a[href*='/Jobs/']",
        "a[href*='/jobs/']",
        "div.job",
        "article",
        ".job-listing",
        ".job-item",
    ]:
        found = soup.select(selector)
        if found:
            candidates.extend(found)

    seen: set[str] = set()
    for node in candidates:
        link = node if node.name == "a" else node.find("a", href=True)
        if not link or not link.get("href"):
            continue
        href = link["href"]
        if not re.search(r"/[Jj]obs/", href):
            continue

        title = clean_text(link.get_text()) or clean_text(node.get_text())[:80]
        if not title or len(title) < 3:
            continue
        if title.lower() in {"jobs", "all jobs", "cv-less jobs", "walk-in interviews"}:
            continue

        apply_url = href if href.startswith("http") else BASE + href
        if apply_url in seen:
            continue
        seen.add(apply_url)

        company = "XpressJobs Employer"
        company_el = node.select_one(".company, .employer, .job-company") if hasattr(node, "select_one") else None
        if company_el:
            company = clean_text(company_el.get_text()) or company

        location = "Sri Lanka"
        loc_el = node.select_one(".location, .job-location") if hasattr(node, "select_one") else None
        if loc_el:
            location = clean_text(loc_el.get_text()) or location

        description = clean_text(node.get_text())[:500]

        jobs.append(
            RawJob(
                title=title[:120],
                company=company,
                location=location,
                description=description,
                source="xpressjobs",
                apply_url=apply_url,
                job_id=make_job_id("xpressjobs", title, company),
            )
        )
        if len(jobs) >= limit:
            break

    if not jobs:
        jobs.append(
            RawJob(
                title=f"XpressJobs search: {query}",
                company="XpressJobs",
                location="Sri Lanka",
                description=f"Open XpressJobs listings for '{query}'.",
                source="xpressjobs",
                apply_url=url,
                job_id=make_job_id("xpressjobs", query, "search"),
            )
        )
    return jobs[:limit]
