"""Streamlit UI — upload CV, show ranked jobs + apply links."""

from __future__ import annotations

import streamlit as st

from src.workflows import run_pipeline

st.set_page_config(
    page_title="Job Matching Agent",
    page_icon="🧭",
    layout="wide",
)

SOURCE_COLORS = {
    "linkedin": "#0A66C2",
    "topjobs": "#C45C26",
    "xpressjobs": "#1B7A4E",
    "fallback": "#5A5A5A",
}


def main() -> None:
    st.title("Job Matching Agent")
    st.caption(
        "Upload your CV → parse profile → search LinkedIn, TopJobs.lk & XpressJobs "
        "→ score fit → ranked apply links"
    )

    with st.sidebar:
        st.header("How it works")
        st.markdown(
            """
1. **PDF Parser Agent** extracts skills & roles  
2. **Search Agent** queries LinkedIn / TopJobs / XpressJobs  
3. **Scorer Agent** ranks fit & missing skills  
4. Open **Apply** links on each source  
            """
        )
        st.divider()
        max_jobs = st.slider("Jobs to score", min_value=3, max_value=12, value=6)

    uploaded = st.file_uploader("Upload CV (PDF)", type=["pdf"])

    if not uploaded:
        st.info("Upload a text-based PDF CV to start.")
        return

    if st.button("Find matching jobs", type="primary", use_container_width=True):
        with st.spinner("Running multi-agent pipeline…"):
            try:
                result = run_pipeline(uploaded.getvalue(), max_score_jobs=max_jobs)
            except Exception as exc:
                st.error(str(exc))
                return

        st.session_state["pipeline_result"] = result

    result = st.session_state.get("pipeline_result")
    if not result:
        return

    profile = result.profile
    st.subheader("Candidate profile")
    c1, c2, c3 = st.columns(3)
    c1.metric("Experience (years)", profile.experience_years)
    c2.write("**Preferred roles**")
    c2.write(", ".join(profile.preferred_roles) or "—")
    c3.write("**Education**")
    c3.write(profile.education or "—")

    with st.expander("Full parsed profile", expanded=False):
        st.json(profile.model_dump())

    st.write(f"**Search query:** `{result.search_query}`")
    cols = st.columns(2)
    cols[0].success("Sources used: " + (", ".join(result.sources_used) or "none"))
    if result.sources_failed:
        cols[1].warning("Sources failed: " + ", ".join(result.sources_failed))

    st.subheader("Ranked job matches")
    if not result.matches:
        st.warning("No jobs found. Check API keys and network, then try again.")
        return

    for rank, match in enumerate(result.matches, start=1):
        with st.container(border=True):
            top = st.columns([6, 2, 2])
            top[0].markdown(f"### {rank}. {match.title}")
            top[0].caption(f"{match.company} · {match.location}")
            top[1].metric("Match", f"{match.match_score}%")
            color = SOURCE_COLORS.get(match.source, "#333")
            top[2].markdown(
                f"<span style='background:{color};color:white;padding:4px 10px;"
                f"border-radius:6px;font-size:0.85rem'>{match.source}</span>",
                unsafe_allow_html=True,
            )

            m1, m2 = st.columns(2)
            m1.write("**Matched skills**")
            m1.write(", ".join(match.matched_skills) or "—")
            m2.write("**Missing skills**")
            m2.write(", ".join(match.missing_skills) or "—")

            st.write(match.feedback)
            st.link_button("Apply / Open listing", match.apply_url, use_container_width=False)


if __name__ == "__main__":
    main()
