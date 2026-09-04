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

st.divider()

# ---------------- RISK TABLE ---------------- #
st.subheader("Predicted Risks")

if not risks:
    st.write("No risks recorded for this project.")
else:
    rating_icon = {"Critical": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🟢"}

    df_risks = pd.DataFrame(
        [
            {
                "Risk ID": r.get("riskId", "-"),
                "Risk Title": r.get("riskTitle", "-"),
                "Category": r.get("riskCategory", "-"),
                "Risk Type": r.get("riskType", "-"),
                "Overall Rating": f"{rating_icon.get(r.get('overallRiskRating', 'Unknown'), '⚪')} {r.get('overallRiskRating', '-')}",
                "Likelihood": r.get("likelihood", "-"),
                "Impact Severity": r.get("impactSeverity", "-"),
                "Priority": r.get("riskPriority", "-"),
                "Confidence Score": r.get("confidenceScore", "-"),
                "Time To Materialization": r.get("timeToMaterialization", "-"),
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
            c1, c2, c3, c4 = st.columns(4)
            c1.write(f"**Category:** {r.get('riskCategory', '-')}")
            c2.write(f"**Risk Type:** {r.get('riskType', '-')}")
            c3.write(f"**Likelihood:** {r.get('likelihood', '-')}")
            c4.write(f"**Confidence Score:** {r.get('confidenceScore', '-')}")

            c5, c6, c7 = st.columns(3)
            c5.write(f"**Impact Severity:** {r.get('impactSeverity', '-')}")
            c6.write(f"**Risk Priority:** {r.get('riskPriority', '-')}")
            c7.write(f"**Time To Materialization:** {r.get('timeToMaterialization', '-')}")

            c8, c9, c10 = st.columns(3)
            c8.write(f"**Preventability:** {r.get('preventability', '-')}")
            c9.write(f"**Business Criticality:** {r.get('businessCriticality', '-')}")
            c10.write(f"**Estimated Resolution Time:** {r.get('estimatedResolutionTime', '-')}")

            st.write(f"**Description:** {r.get('riskDescription', '-')}")
            st.write(f"**Root Cause:** {r.get('rootCause', '-')}")

            p1, p2, p3 = st.columns(3)
            p1.write(f"**Current Project Phase:** {r.get('currentProjectPhase', '-')}")
            p2.write(f"**Expected Occurrence Phase:** {r.get('expectedOccurrencePhase', '-')}")
            p3.write(f"**Likely Impact Phase:** {r.get('likelyImpactPhase', '-')}")

            trigger_conditions = r.get("triggerConditions", [])
            if trigger_conditions:
                st.write("**Trigger Conditions**")
                for item in trigger_conditions:
                    st.write(f"- {item}")

            # Potential Impact
            potential_impact = r.get("potentialImpact", {})
            if potential_impact:
                st.write("**Potential Impact**")
                df_impact = pd.DataFrame(
                    {
                        "Dimension": ["Schedule", "Cost", "Quality", "Customer", "Operations"],
                        "Detail": [
                            potential_impact.get("schedule", "-"),
                            potential_impact.get("cost", "-"),
                            potential_impact.get("quality", "-"),
                            potential_impact.get("customer", "-"),
                            potential_impact.get("operations", "-"),
                        ],
                    }
                ).set_index("Dimension")
                st.table(df_impact)

            # Mitigation Plan (this risk's own stages/actions)
            mitigation_plan = r.get("mitigationPlan", [])
            if mitigation_plan:
                st.write("**Mitigation Plan**")
                df_mitigation_stages = pd.DataFrame(
                    [
                        {
                            "Stage": stage_entry.get("stage", "-"),
                            "Actions": "\n".join(f"- {a}" for a in stage_entry.get("actions", [])),
                        }
                        for stage_entry in mitigation_plan
                    ]
                ).set_index("Stage")
                st.table(df_mitigation_stages)

            # Recommendations
            recommendations = r.get("recommendations", {})
            if recommendations:
                st.write("**Recommendations**")
                df_recommendations = pd.DataFrame(
                    {
                        "Type": ["Preventive", "Monitoring", "Contingency", "Strategic"],
                        "Detail": [
                            recommendations.get("preventive", "-"),
                            recommendations.get("monitoring", "-"),
                            recommendations.get("contingency", "-"),
                            recommendations.get("strategic", "-"),
                        ],
                    }
                ).set_index("Type")
                st.table(df_recommendations)
