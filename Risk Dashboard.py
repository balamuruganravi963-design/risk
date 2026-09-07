import streamlit as st
import requests
import base64
import json
import pandas as pd
from collections import Counter

st.set_page_config(layout="wide", page_title="Project Risk Dashboard")

# ---------------- CONFIG ---------------- #
GITHUB_REPO = "balamuruganravi963-design/risk"
GITHUB_BRANCH = "main"

# Only needed if the repo is PRIVATE. Leave blank ("") if public.
# If set, add this in Streamlit Cloud -> App settings -> Secrets:
#   GITHUB_READ_TOKEN = "ghp_xxxxxxxxxxxx"
GITHUB_READ_TOKEN = st.secrets.get("GITHUB_READ_TOKEN", "")

# Severity/priority color coding, reused for both Overall Rating and Risk Priority.
rating_icon = {"Critical": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🟢"}


def has_value(value):
    """
    Dashboard-only rendering rule: a field 'has a value' if it isn't None,
    isn't an empty/whitespace-only string, and isn't an empty list/dict.
    Numbers (including 0) and booleans always count as present, since a
    real 0 (e.g. confidenceScore) can't be distinguished from a default 0.
    """
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, (list, dict)):
        return len(value) > 0
    return True


def priority_display(value):
    """Color-coded Risk Priority label, or '-' if not present."""
    if not has_value(value):
        return "-"
    return f"{rating_icon.get(value, '⚪')} {value}"


def render_dynamic_grid(pairs, cols_per_row=4):
    """
    Render (label, value) pairs as inline '**Label:** value' text laid out
    across a row of columns — NOT a data table. Pairs whose value is empty
    are dropped first, then the remaining pairs are chunked into rows of
    cols_per_row, so the grid always reflects only the fields that actually
    have data for this risk.
    """
    visible = [(label, val) for label, val in pairs if has_value(val)]
    for i in range(0, len(visible), cols_per_row):
        chunk = visible[i:i + cols_per_row]
        cols = st.columns(len(chunk))
        for col, (label, val) in zip(cols, chunk):
            col.write(f"**{label}:** {val}")


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
# Schema: { "clientName": "", "projects": [ { ... "predictedRisks": [...] } ] }
client_name = data.get("clientName", "")
projects = data.get("projects", [])

if not projects:
    st.error("No projects found in dashboard data.")
    st.stop()

# ---------------- HEADER ---------------- #
st.title("📊 Project Risk Dashboard")

# Client Name as a read-only text-box heading (single client per file).
st.text_input("Client Name", value=client_name or "Unknown Client", disabled=True)

# ---------------- PORTFOLIO SUMMARY (computed) ---------------- #
total_projects = len(projects)
projects_with_risks = sum(1 for p in projects if p.get("predictedRisks", []))
projects_without_risks = total_projects - projects_with_risks
total_risks = sum(len(p.get("predictedRisks", [])) for p in projects)

sc1, sc2, sc3, sc4 = st.columns(4)
sc1.metric("Total Projects", total_projects)
sc2.metric("Projects With Predicted Risks", projects_with_risks)
sc3.metric("Projects With No Predicted Risks", projects_without_risks)
sc4.metric("Total Predicted Risks", total_risks)

# ---------------- RISKS BY PROJECT (table, not chart) ---------------- #
risks_by_project = [
    {"Project": p.get("projectName", ""), "Predicted Risks Count": len(p.get("predictedRisks", []))}
    for p in projects
]
if risks_by_project:
    st.write("**Risks by Project**")
    df_rbp = pd.DataFrame(risks_by_project)
    st.table(df_rbp.set_index("Project"))

st.divider()

# ---------------- PROJECT -> RISK SELECTION ---------------- #
# Two-level selection only: Project, then Risk. There is no client selector
# because clientName is a single root-level value for the whole file.
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

pc1, pc2 = st.columns(2)
pc1.write(f"**Project Status:** {project.get('projectStatus', '-')}")
pc2.write(f"**Risk Prediction Date:** {project.get('riskPredictionDate', '-')}")

risks = project.get("predictedRisks", [])

st.divider()

# ---------------- RISK SUMMARY (computed) ---------------- #
st.subheader("Risk Summary")

rating_counts = Counter(r.get("overallRiskRating", "Unknown") for r in risks)
rc1, rc2, rc3, rc4 = st.columns(4)
rc1.metric("Critical", rating_counts.get("Critical", 0))
rc2.metric("High", rating_counts.get("High", 0))
rc3.metric("Medium", rating_counts.get("Medium", 0))
rc4.metric("Low", rating_counts.get("Low", 0))

st.divider()

# ---------------- CATEGORY DISTRIBUTION (table, not chart) ---------------- #
st.subheader("Risk Category Distribution")

severity_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
if risks:
    df_cat_dist = pd.DataFrame(
        [
            {
                "Category": r.get("riskCategory", "Unknown"),
                "Rating": r.get("overallRiskRating", "Unknown"),
            }
            for r in risks
        ]
    )
    df_cat_dist = (
        df_cat_dist.groupby(["Category", "Rating"]).size().reset_index(name="Count")
    )
    df_cat_dist["__order"] = df_cat_dist["Rating"].map(severity_order).fillna(4)
    df_cat_dist = df_cat_dist.sort_values(["Category", "__order"]).drop(columns="__order")
    st.table(df_cat_dist.set_index("Category"))
else:
    st.write("No category distribution data available.")

st.divider()

# ---------------- RISK TABLE ---------------- #
st.subheader("Predicted Risks")

if not risks:
    st.write("No risks recorded for this project.")
else:
    # Summary table: Risk ID, Risk Title, Category, Risk Priority (color-coded).
    # Overall Rating, Risk Type, Likelihood, and Impact Severity are intentionally
    # left out of this table — they're still available in each risk's detail panel.
    df_risks = pd.DataFrame(
        [
            {
                "Risk ID": r.get("riskId", "-"),
                "Risk Title": r.get("riskTitle", "-"),
                "Category": r.get("riskCategory") or "-",
                "Risk Priority": priority_display(r.get("riskPriority", "")),
            }
            for r in risks
        ]
    )
    st.table(df_risks.set_index("Risk ID"))

    st.write("**Risk Details**")
    st.caption("Expand the ➕ next to a risk title for its full breakdown.")

    for r in risks:
        risk_id = r.get("riskId", "-")
        title = r.get("riskTitle", "Untitled Risk")
        overall_rating = r.get("overallRiskRating", "Unknown")
        icon = rating_icon.get(overall_rating, "⚪")

        with st.expander(f"➕ [{risk_id}] {title} — {icon} {overall_rating}"):
            # ---- Key attributes (dynamic: only fields with a value are shown, ---- #
            # ---- rendered inline as bold Label: value text, not a table)     ---- #
            attribute_rows = [
                ("Category", r.get("riskCategory", "")),
                ("Risk Type", r.get("riskType", "")),
                ("Likelihood", r.get("likelihood", "")),
                ("Confidence Score", r.get("confidenceScore", None)),
                ("Impact Severity", r.get("impactSeverity", "")),
                ("Risk Priority", priority_display(r.get("riskPriority", "")) if has_value(r.get("riskPriority")) else ""),
                ("Time To Materialization", r.get("timeToMaterialization", "")),
                ("Preventability", r.get("preventability", "")),
                ("Business Criticality", r.get("businessCriticality", "")),
                ("Estimated Resolution Time", r.get("estimatedResolutionTime", "")),
            ]
            render_dynamic_grid(attribute_rows, cols_per_row=4)

            # ---- Description / Root cause (dynamic) ---- #
            if has_value(r.get("riskDescription")):
                st.write(f"**Description:** {r.get('riskDescription')}")
            if has_value(r.get("rootCause")):
                st.write(f"**Root Cause:** {r.get('rootCause')}")

            # ---- Phases (dynamic, inline grid) ---- #
            phase_rows = [
                ("Current Project Phase", r.get("currentProjectPhase", "")),
                ("Expected Occurrence Phase", r.get("expectedOccurrencePhase", "")),
                ("Likely Impact Phase", r.get("likelyImpactPhase", "")),
            ]
            render_dynamic_grid(phase_rows, cols_per_row=3)

            # ---- Trigger Conditions (dynamic) ---- #
            trigger_conditions = r.get("triggerConditions", [])
            if has_value(trigger_conditions):
                st.write("**Trigger Conditions**")
                for item in trigger_conditions:
                    st.write(f"- {item}")

            # ---- Potential Impact (dynamic per dimension) ---- #
            potential_impact = r.get("potentialImpact", {}) or {}
            impact_rows = [
                (label, potential_impact.get(key, ""))
                for label, key in [
                    ("Schedule", "schedule"),
                    ("Cost", "cost"),
                    ("Quality", "quality"),
                    ("Customer", "customer"),
                    ("Operations", "operations"),
                ]
            ]
            visible_impact = [(label, val) for label, val in impact_rows if has_value(val)]
            if visible_impact:
                st.write("**Potential Impact**")
                df_impact = pd.DataFrame(visible_impact, columns=["Dimension", "Detail"]).set_index("Dimension")
                st.table(df_impact)

            # ---- Mitigation Plan (dynamic: only stages with content) ---- #
            mitigation_plan = r.get("mitigationPlan", []) or []
            visible_stages = [
                stage_entry for stage_entry in mitigation_plan
                if has_value(stage_entry.get("stage")) or has_value(stage_entry.get("actions"))
            ]
            if visible_stages:
                st.write("**Mitigation Plan**")
                df_mitigation_stages = pd.DataFrame(
                    [
                        {
                            "Stage": stage_entry.get("stage", "-"),
                            "Actions": "\n".join(f"- {a}" for a in stage_entry.get("actions", [])),
                        }
                        for stage_entry in visible_stages
                    ]
                ).set_index("Stage")
                st.table(df_mitigation_stages)

            # ---- Recommendations (dynamic per sub-field) ---- #
            recommendations = r.get("recommendations", {}) or {}
            rec_rows = [
                (label, recommendations.get(key, ""))
                for label, key in [
                    ("Preventive", "preventive"),
                    ("Monitoring", "monitoring"),
                    ("Contingency", "contingency"),
                    ("Strategic", "strategic"),
                ]
            ]
            visible_rec = [(label, val) for label, val in rec_rows if has_value(val)]
            if visible_rec:
                st.write("**Recommendations**")
                df_recommendations = pd.DataFrame(visible_rec, columns=["Type", "Detail"]).set_index("Type")
                st.table(df_recommendations)

st.divider()

# ---------------- OVERALL SUMMARY (computed) ---------------- #
st.subheader("Overall Summary")

if risks:
    total_risks = len(risks)
    rating_counts_summary = Counter(r.get("overallRiskRating", "Unknown") for r in risks)
    category_counts_summary = Counter(r.get("riskCategory", "Unknown") for r in risks)
    top_category, top_category_count = category_counts_summary.most_common(1)[0]
    critical_priority_count = sum(1 for r in risks if r.get("riskPriority") == "Critical")

    summary_text = (
        f"**{project.get('projectName', 'This project')}** carries **{total_risks}** predicted risk"
        f"{'s' if total_risks != 1 else ''}: "
        f"{rating_counts_summary.get('Critical', 0)} Critical, "
        f"{rating_counts_summary.get('High', 0)} High, "
        f"{rating_counts_summary.get('Medium', 0)} Medium, and "
        f"{rating_counts_summary.get('Low', 0)} Low. "
        f"The most frequent risk category is **{top_category}** ({top_category_count} risk"
        f"{'s' if top_category_count != 1 else ''}), and "
        f"**{critical_priority_count}** risk{'s are' if critical_priority_count != 1 else ' is'} "
        f"flagged as Critical priority."
    )
    st.write(summary_text)
else:
    st.write("No risks recorded for this project.")
