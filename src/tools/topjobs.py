"""TopJobs.lk live fetch + parse tool."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from src.tools.http_utils import clean_text, encode_query, fetch_html, make_job_id
from src.utils.schemas import RawJob

BASE = "https://www.topjobs.lk"
SEARCH_URL = (
    BASE
    + "/applicant/vacancybyfunctionalarea.jsp"
    + "?FA={fa}&jst=OPEN&txtKeyWord={query}"
)


def search_topjobs(query: str, limit: int = 8, fa: str = "SDQ") -> list[RawJob]:
    """
    fa: TopJobs functional area code.
    Examples: SDQ=IT software, TAL=Education, SMM=Sales/Marketing, ''=All.
    """
    keyword = query.strip() or "job"
    url = SEARCH_URL.format(fa=fa or "", query=encode_query(keyword))
    html = fetch_html(url)
    soup = BeautifulSoup(html, "lxml")
    jobs: list[RawJob] = []

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue

        header = " ".join(clean_text(c.get_text()) for c in rows[0].find_all(["td", "th"]))
        if "Job Ref" not in header and "Position and Employer" not in header:
            continue

        for row in rows[1:]:
            cells = row.find_all("td")
            if len(cells) < 4:
                continue

            ref = clean_text(cells[1].get_text())
            position_text = _clean_position(clean_text(cells[2].get_text(" ", strip=True)))
            description = clean_text(cells[3].get_text())
            location = clean_text(cells[6].get_text()) if len(cells) > 6 else "Sri Lanka"
            if not location:
                location = "Sri Lanka"

            link = cells[2].find("a", href=True)
            apply_url = _absolute_url(link["href"]) if link else url

            title, company = _split_title_company(position_text)
            if not title or len(title) < 3:
                continue

            jobs.append(
                RawJob(
                    title=title,
                    company=company or "TopJobs Employer",
                    location=location,
                    description=description or position_text,
                    source="topjobs",
                    apply_url=apply_url,
                    job_id=make_job_id("topjobs", title, company or ref),
                )
            )
            if len(jobs) >= limit:
                return jobs

    if not jobs:
        jobs.append(
            RawJob(
                title=f"TopJobs search: {query}",
                company="TopJobs.lk",
                location="Sri Lanka",
                description=f"Open TopJobs IT listings matching '{query}'.",
                source="topjobs",
                apply_url=url,
                job_id=make_job_id("topjobs", query, "search"),
            )
        )
    return jobs[:limit]


def _clean_position(text: str) -> str:
    text = re.sub(r"\bDEFZZZ\b", " ", text, flags=re.I)
    text = re.sub(r"\b0+\d+\b", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _split_title_company(text: str) -> tuple[str, str]:
    text = clean_text(text)
    # "Title (1) Company Name"
    match = re.match(r"^(.+?)\s+\(\d+\)\s+(.+)$", text)
    if match:
        return clean_text(match.group(1)), clean_text(match.group(2))

    suffix = re.search(
        r"(\s(?:\(Pvt\)\s*Ltd|Pvt\.?\s*Ltd|Limited|PLC|Ltd\.?))$",
        text,
        flags=re.I,
    )
    if suffix:
        before = text[: suffix.start()].rstrip()
        words = before.split()
        corp = suffix.group(1).strip()
        if len(words) >= 4:
            company = f"{words[-2]} {words[-1]} {corp}"
            title = " ".join(words[:-2])
            return clean_text(title), clean_text(company)
        if len(words) >= 2:
            company = f"{words[-1]} {corp}"
            title = " ".join(words[:-1])
            return clean_text(title), clean_text(company)

    words = text.split()
    if len(words) >= 3 and words[-1][:1].isupper() and len(words[-1]) > 2:
        return clean_text(" ".join(words[:-1])), words[-1]

    if " - " in text:
        left, right = text.rsplit(" - ", 1)
        return clean_text(left), clean_text(right)

    return text, "TopJobs Employer"


def _absolute_url(href: str) -> str:
    href = href.strip()
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return BASE + href
    if href.startswith("javascript"):
        return BASE + "/applicant/vacancybyfunctionalarea.jsp?jst=OPEN"
    return BASE + "/applicant/" + href.lstrip("./")
