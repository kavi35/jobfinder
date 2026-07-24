"""Shared HTTP helpers for job board tools."""

from __future__ import annotations

import hashlib
import re
import warnings
from urllib.parse import quote_plus

import httpx

# TopJobs/XpressJobs often fail CA verification on Windows student machines.
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


def fetch_html(url: str, timeout: float = 20.0) -> str:
    """Fetch HTML. verify=False handles broken/incomplete CA chains on some Windows setups."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    with httpx.Client(
        follow_redirects=True,
        timeout=timeout,
        headers=headers,
        verify=False,
    ) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


def make_job_id(source: str, title: str, company: str) -> str:
    raw = f"{source}|{title}|{company}".lower().strip()
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:12]


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def encode_query(query: str) -> str:
    return quote_plus(query.strip())
