import base64
import html
import json
import re
from collections import Counter

import pandas as pd
import requests
import streamlit as st

st.set_page_config(layout="wide", page_title="Project Risk Dashboard")

# ---------------- CONFIG ---------------- #
GITHUB_REPO = "balamuruganravi963-design/risk"
GITHUB_BRANCH = "main"

# Only needed if the repo is PRIVATE. Leave blank ("") if public.
# If set, add this in Streamlit Cloud -> App settings -> Secrets:
#   GITHUB_READ_TOKEN = "ghp_xxxxxxxxxxxx"
try:
    GITHUB_READ_TOKEN = st.secrets.get("GITHUB_READ_TOKEN", "")
except Exception:  # no secrets.toml configured -> treat as public repo
    GITHUB_READ_TOKEN = ""

# ---------------- GET DATA ---------------- #
# st.query_params automatically URL-decodes the value, so "path" arrives
# as a normal string like "dashboard-data/a1b2c3d4.json"
params = st.query_params
file_path = params.get("path")

if not file_path:
    st.error("No file path found in URL")
    st.stop()

api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file_path}"

headers = {"Accept": "application/vnd.github+json"}
if GITHUB_READ_TOKEN:
    headers["Authorization"] = f"token {GITHUB_READ_TOKEN}"

response = requests.get(api_url, headers=headers, params={"ref": GITHUB_BRANCH}, timeout=15)

if response.status_code != 200:
    st.error(f"Failed to load dashboard data (status {response.status_code}).")
    st.stop()

file_data = response.json()
content = base64.b64decode(file_data["content"]).decode("utf-8")
data = json.loads(content)

# ---------------- TOP-LEVEL DATA ---------------- #
# Schema: { "client": "", "projects": [ { ..., "risks": [...] } ] }
client = data.get("client", "")
projects = data.get("projects", [])

if not projects:
    st.error("No projects found in dashboard data.")
    st.stop()

# ---------------- HELPERS ---------------- #
RAG_ORDER = ["Red", "Amber", "Green"]
RAG_ICON = {"Red": "🔴", "Amber": "🟠", "Green": "🟢"}


def has_value(value):
    """A field is considered present only if it has real, non-empty content."""
    return value not in (None, "", [], {})


def display_id(risk_id):
    """'R - 001' -> 'R-001' (display only; the JSON value is untouched)."""
    return re.sub(r"\s*-\s*", "-", str(risk_id)).strip() if has_value(risk_id) else "-"


def rag_label(rag):
    return f"{RAG_ICON.get(rag, '⚪')} {rag}" if has_value(rag) else "⚪ -"


def risk_parts(r):
    """Return (context, condition, consequence) whatever shape riskDescription has."""
    d = r.get("riskDescription")
    if isinstance(d, dict):
        return d.get("context", ""), d.get("condition", ""), d.get("consequence", "")
    return "", d or "", ""


def risk_statement(r):
    """Short text for the table's Risk Description column."""
    context, condition, _ = risk_parts(r)
    return condition or context


def cell(value):
    return html.escape(str(value)) if has_value(value) else "—"


# (header, value getter, min width in px) — exactly the requested register layout.
TABLE_COLUMNS = [
    ("S.No", lambda r, i: r.get("sNo", i), 50),
    ("Risk ID", lambda r, i: display_id(r.get("riskId")), 70),
    ("Subject Area", lambda r, i: r.get("subjectArea"), 100),
    ("Risk Description", lambda r, i: risk_statement(r), 280),
    ("Category", lambda r, i: r.get("category"), 100),
    ("Probability", lambda r, i: r.get("probability"), 90),
    ("Impact", lambda r, i: r.get("impact"), 80),
    ("RAG", lambda r, i: rag_label(r.get("rag")), 85),
    ("Mitigation / Preventive Action", lambda r, i: r.get("mitigationPreventiveAction"), 240),
    ("Contingency / Corrective Action", lambda r, i: r.get("contingencyCorrectiveAction"), 240),
    ("Owner", lambda r, i: r.get("owner"), 140),
    ("Target Date", lambda r, i: r.get("targetDate"), 100),
    ("Status", lambda r, i: r.get("status"), 70),
]


RAG_MATRIX_IMPACTS = ["High Impact", "Medium Impact", "Low Impact"]
RAG_MATRIX = [
    ("Very Likely", ["Red", "Red", "Amber"]),
    ("Likely", ["Red", "Amber", "Green"]),
    ("Possible", ["Amber", "Amber", "Green"]),
    ("Unlikely", ["Amber", "Green", "Green"]),
    ("Rare", ["Green", "Green", "Green"]),
]
RAG_BG = {
    "Red": "rgba(220, 53, 69, 0.35)",
    "Amber": "rgba(255, 152, 0, 0.35)",
    "Green": "rgba(40, 167, 69, 0.35)",
}


def render_rag_matrix():
    """Legend: likelihood x impact -> RAG."""
    th = "padding:8px 14px; text-align:center; background:rgba(128,128,128,0.15); border:1px solid rgba(128,128,128,0.4);"
    head = f"<th style='{th}'>Likelihood</th>" + "".join(
        f"<th style='{th}'>{html.escape(i)}</th>" for i in RAG_MATRIX_IMPACTS
    )
    rows = ""
    for likelihood, rags in RAG_MATRIX:
        cells = "".join(
            f"<td style='padding:8px 14px; text-align:center; background:{RAG_BG[rag]}; "
            f"border:1px solid rgba(128,128,128,0.4);'>{RAG_ICON[rag]} {rag}</td>"
            for rag in rags
        )
        rows += (
            f"<tr><td style='padding:8px 14px; font-weight:600; border:1px solid rgba(128,128,128,0.4);'>"
            f"{html.escape(likelihood)}</td>{cells}</tr>"
        )
    st.markdown(
        "<div style='overflow-x:auto;'>"
        "<table style='border-collapse:collapse; font-size:0.85rem;'>"
        f"<thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>",
        unsafe_allow_html=True,
    )


def render_risk_register(risk_list):
    """HTML table (text wraps; st.dataframe would truncate long cells)."""
    head = "".join(
        f"<th style='text-align:left; padding:8px 10px; min-width:{w}px; "
        f"background:rgba(128,128,128,0.15); border-bottom:1px solid rgba(128,128,128,0.4);'>"
        f"{html.escape(h)}</th>"
        for h, _, w in TABLE_COLUMNS
    )
    rows = ""
    for i, r in enumerate(risk_list, start=1):
        tds = ""
        for header, getter, _ in TABLE_COLUMNS:
            value = getter(r, i)
            body = cell(value)
            tds += (
                "<td style='vertical-align:top; padding:8px 10px; "
                f"border-bottom:1px solid rgba(128,128,128,0.25);'>{body}</td>"
            )
        rows += f"<tr>{tds}</tr>"
    st.markdown(
        "<div style='overflow-x:auto;'>"
        "<table style='width:100%; border-collapse:collapse; font-size:0.82rem;'>"
        f"<thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>",
        unsafe_allow_html=True,
    )


def rag_counts_for(risk_list):
    return Counter(r.get("rag") or "Unknown" for r in risk_list)


# ---------------- HEADER ---------------- #
st.title("📊 Project Risk Dashboard")

# Client Name as a read-only text-box heading (single client per file).
st.text_input("Client", value=client or "Unknown Client", disabled=True)

# ---------------- PORTFOLIO SUMMARY (computed) ---------------- #
total_projects = len(projects)
projects_with_risks = sum(1 for p in projects if p.get("risks", []))
projects_without_risks = total_projects - projects_with_risks
total_risks = sum(len(p.get("risks", [])) for p in projects)

sc1, sc2, sc3, sc4 = st.columns(4)
sc1.metric("Total Projects", total_projects)
sc2.metric("Projects With Predicted Risks", projects_with_risks)
sc3.metric("Projects With No Predicted Risks", projects_without_risks)
sc4.metric("Total Predicted Risks", total_risks)

# ---------------- RISKS BY PROJECT (table, not chart) ---------------- #
rbp_rows = []
for p in projects:
    counts = rag_counts_for(p.get("risks", []))
    rbp_rows.append(
        {
            "Project": p.get("projectName", ""),
            "Total Risks": len(p.get("risks", [])),
            "🔴 Red": counts.get("Red", 0),
            "🟠 Amber": counts.get("Amber", 0),
            "🟢 Green": counts.get("Green", 0),
        }
    )
st.write("**Risks by Project**")
st.dataframe(pd.DataFrame(rbp_rows), width="stretch", hide_index=True)

st.divider()

# ---------------- PROJECT SELECTION ---------------- #
project_names = [
    p.get("projectName", f"Project {i + 1}") for i, p in enumerate(projects)
]
selected_project_name = st.selectbox("Select Project", project_names)
project = next(
    (p for p in projects if p.get("projectName") == selected_project_name),
    projects[0],
)

# Project Name as a read-only text-box heading.
st.text_input("Project Name", value=project.get("projectName", ""), disabled=True)

pc1, pc2, pc3 = st.columns(3)
pc1.write(f"**Project Status:** {project.get('projectStatus') or '-'}")
pc3.write(f"**Sources Used:** {', '.join(project.get('sourcesUsed', [])) or '-'}")

risks = sorted(project.get("risks", []), key=lambda r: r.get("sNo") or 0)

st.divider()

# ---------------- RISK SUMMARY (computed from RAG) ---------------- #
st.subheader("Risk Summary")
rag_counts = rag_counts_for(risks)
rc1, rc2, rc3, rc4 = st.columns(4)
rc1.metric("🔴 Red", rag_counts.get("Red", 0))
rc2.metric("🟠 Amber", rag_counts.get("Amber", 0))
rc3.metric("🟢 Green", rag_counts.get("Green", 0))
rc4.metric("Total", len(risks))

st.divider()

# ---------------- CATEGORY DISTRIBUTION (table, not chart) ---------------- #
st.subheader("Risk Category Distribution")
if risks:
    ct = pd.crosstab(
        pd.Series([r.get("category") or "Unknown" for r in risks], name="Category"),
        pd.Series([r.get("rag") or "Unknown" for r in risks], name="RAG"),
    )
    cols = RAG_ORDER + [c for c in ct.columns if c not in RAG_ORDER]
    ct = ct.reindex(columns=cols, fill_value=0)
    ct["Total"] = ct.sum(axis=1)
    st.dataframe(ct, width="stretch")
else:
    st.write("No category distribution data available.")

st.divider()

# ---------------- RISK REGISTER TABLE ---------------- #
st.subheader("Risk Register")

if not risks:
    st.write("No risks recorded for this project.")
else:
    render_risk_register(risks)

st.divider()

# ---------------- RAG MATRIX (legend) ---------------- #
st.subheader("RAG Risk Matrix (Legend)")
render_rag_matrix()

st.divider()

# ---------------- OVERALL SUMMARY (computed) ---------------- #
st.subheader("Overall Summary")

if risks:
    category_counts = Counter(r.get("category") or "Unknown" for r in risks)
    top_category, top_category_count = category_counts.most_common(1)[0]
    n = len(risks)
    st.write(
        f"**{project.get('projectName', 'This project')}** carries **{n}** predicted "
        f"risk{'s' if n != 1 else ''}: "
        f"{rag_counts.get('Red', 0)} Red, {rag_counts.get('Amber', 0)} Amber, and "
        f"{rag_counts.get('Green', 0)} Green. "
        f"The most frequent risk category is **{top_category}** ({top_category_count} "
        f"risk{'s' if top_category_count != 1 else ''})."
    )
else:
    st.write("No risks recorded for this project.")
