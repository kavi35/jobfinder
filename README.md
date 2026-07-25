# Job Matching Multi-Agent App

Upload a CV → parse profile → search **LinkedIn / TopJobs.lk / XpressJobs** → score matches → Streamlit UI with apply links.

## Setup

```powershell
cd "c:\Users\kavin\OneDrive\Desktop\job"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Put real keys in `.streamlit/secrets.toml` (DeepSeek is enough for the full app):

```toml
DEEPSEEK_API_KEY = "sk-..."
OPENROUTER_API_KEY = "sk-or-..."
```

Get a DeepSeek key from [platform.deepseek.com](https://platform.deepseek.com).

## Run

```powershell
streamlit run app.py
```

## Pipeline

```text
Upload CV (PDF)
    → PDF Parser Agent (DeepSeek)
    → Candidate Profile
    → Search Agent
        → LinkedIn | TopJobs.lk | XpressJobs
    → Collect + Dedupe (+ local corpus fallback)
    → Scorer Agent (DeepSeek / OpenRouter)
    → Streamlit UI (ranked jobs + apply links)
```

## Notes

- LinkedIn results are public search deep-links (LinkedIn blocks scrapers).
- TopJobs / XpressJobs use live HTTP fetch; if a site is down, the pipeline continues.
- `data/jobs_corpus/` is used as offline fallback when live boards fail.
# jobfinder
