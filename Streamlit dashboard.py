import streamlit as st
import requests
import base64
import json
import pandas as pd
from collections import Counter, OrderedDict

st.set_page_config(layout="wide", page_title="Project Risk Dashboard")

# ---------------- CONFIG ---------------- #
GITHUB_REPO = "balamuruganravi963-design/risk"
GITHUB_BRANCH = "main"

# Only needed if the repo is PRIVATE. Leave blank ("") if public.
# If set, add this in Streamlit Cloud -> App settings -> Secrets:
#   GITHUB_READ_TOKEN = "ghp_xxxxxxxxxxxx"
GITHUB_READ_TOKEN = st.secrets.get("GITHUB_READ_TOKEN", "")

UNKNOWN_CLIENT_LABEL = "Unknown Client"

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
projects = data.get("projects", [])
summary_stats = data.get("summaryStatistics", {})

if not projects:
    st.error("No projects found in dashboard data.")
    st.stop()


def client_label(name):
    """Display-only fallback grouping label; never written back to the data."""
    name = (name or "").strip()
    return name if name else UNKNOWN_CLIENT_LABEL


# ---------------- HEADER / SUMMARY STATISTICS ---------------- #
st.title("📊 Project Risk Dashboard")

sc1, sc2, sc3, sc4 = st.columns(4)
sc1.metric("Total Projects", summary_stats.get("totalProjects", len(projects)))
sc2.metric("Projects With Current Risks", summary_stats.get("projectsWithCurrentRisks", 0))
sc3.metric("Projects With No Current Risks", summary_stats.get("projectsWithNoCurrentRisks", 0))
sc4.metric("Total Current Risks", summary_stats.get("totalCurrentRisks", 0))

# Build a projectName -> clientName lookup so risksByProject rows can show
# which client each project belongs to, without altering summaryStatistics.
project_to_client = {
    p.get("projectName", ""): client_label(p.get("clientName", "")) for p in projects
}

risks_by_project = summary_stats.get("risksByProject", [])
if risks_by_project:
    st.write("**Risks by Project**")
    df_rbp = pd.DataFrame(risks_by_project)
    df_rbp["clientName"] = df_rbp["projectName"].map(project_to_client).fillna(UNKNOWN_CLIENT_LABEL)
    df_rbp = df_rbp.rename(
        columns={"projectName": "Project", "currentRisksCount": "Current Risks Count", "clientName": "Client"}
    )[["Client", "Project", "Current Risks Count"]]
    st.table(df_rbp.set_index("Client"))

st.divider()

# ---------------- CLIENT -> PROJECT -> RISK DRILL-DOWN ---------------- #
st.subheader("Drill Down")

# Step 1: Client
clients = OrderedDict()
for p in projects:
    clients.setdefault(client_label(p.get("clientName", "")), []).append(p)

client_names = list(clients.keys())
selected_client = st.selectbox("1️⃣ Select Client", client_names)

client_projects = clients[selected_client]

# Step 2: Project (filtered by selected client)
project_names = [
    p.get("projectName", f"Project {i+1}") for i, p in enumerate(client_projects)
]
selected_project_name = st.selectbox("2️⃣ Select Project", project_names)
project = next(
    (p for p in client_projects if p.get("projectName") == selected_project_name),
    client_projects[0],
)

# ---------------- CLIENT / PROJECT NAME HEADINGS (text boxes) ---------------- #
hc1, hc2 = st.columns(2)
with hc1:
    st.text_input("Client Name", value=project.get("clientName", "") or UNKNOWN_CLIENT_LABEL, disabled=True)
with hc2:
    st.text_input("Project Name", value=project.get("projectName", ""), disabled=True)

risks = project.get("RiskAnalysis", {}).get("Risks", [])
forecast = project.get("projectForecastInsights", {})

# ---------------- RISK SUMMARY (computed) ---------------- #
st.subheader("Risk Summary")

severity_counts = Counter(r.get("severity", "Unknown") for r in risks)
rc1, rc2, rc3, rc4 = st.columns(4)
rc1.metric("Critical", severity_counts.get("Critical", 0))
rc2.metric("High", severity_counts.get("High", 0))
rc3.metric("Medium", severity_counts.get("Medium", 0))
rc4.metric("Low", severity_counts.get("Low", 0))

st.divider()

# ---------------- CATEGORY DISTRIBUTION (computed) ---------------- #
st.subheader("Risk Category Distribution")

category_counts = Counter(r.get("category", "Unknown") for r in risks)
if category_counts:
    df_cat = pd.DataFrame(
        {"Category": list(category_counts.keys()), "Count": list(category_counts.values())}
    ).set_index("Category")
    st.table(df_cat)
else:
    st.write("No category distribution data available.")

st.divider()

# ---------------- STEP 3: RISK DRILL-DOWN ---------------- #
st.subheader("Predicted Risks")

if not risks:
    st.write("No risks recorded for this project.")
else:
    severity_icon = {"Critical": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🟢"}

    def risk_option_label(r):
        icon = severity_icon.get(r.get("severity", "Unknown"), "⚪")
        risk_id = r.get("riskID", "-")
        title = r.get("riskTitle", "Untitled Risk")
        return f"{icon} [{risk_id}] {title}"

    risk_labels = [risk_option_label(r) for r in risks]
    selected_risk_label = st.selectbox("3️⃣ Select Risk", risk_labels)
    r = risks[risk_labels.index(selected_risk_label)]

    severity = r.get("severity", "Unknown")
    icon = severity_icon.get(severity, "⚪")
    risk_id = r.get("riskID", "-")
    title = r.get("riskTitle", "Untitled Risk")

    st.markdown(f"### {icon} [{risk_id}] {title} — {severity}")

    c1, c2, c3, c4 = st.columns(4)
    c1.write(f"**Category:** {r.get('category', '-')}")
    c2.write(f"**Risk Type:** {r.get('riskType', '-')}")
    c3.write(f"**Likelihood:** {r.get('likelihood', '-')}")
    c4.write(f"**Confidence Score:** {r.get('confidenceScore', '-')}")

    st.write(f"**Description:** {r.get('riskDescription', '-')}")
    st.write(f"**Business Impact:** {r.get('businessImpact', '-')}")

    # Risk Chain
    risk_chain = r.get("riskChain", {})
    if risk_chain:
        st.write("**Risk Chain**")
        df_chain = pd.DataFrame(
            {
                "Stage": ["Root Cause", "Trigger", "Primary Risk", "Downstream Risk", "Impact"],
                "Detail": [
                    risk_chain.get("rootCause", "-"),
                    risk_chain.get("trigger", "-"),
                    risk_chain.get("primaryRisk", "-"),
                    risk_chain.get("downstreamRisk", "-"),
                    risk_chain.get("impact", "-"),
                ],
            }
        ).set_index("Stage")
        st.table(df_chain)

    st.write(f"**Current Project Evidence:** {r.get('currentProjectEvidence', '-')}")
    st.write(f"**Current Context Reasoning:** {r.get('currentContextReasoning', '-')}")

    # Historical Correlation
    hist_corr = r.get("historicalCorrelation", {})
    if hist_corr:
        st.write("**Historical Correlation**")
        df_hist = pd.DataFrame(
            {
                "Field": ["Similar Historical Pattern", "Historical Support Level", "Historical Reasoning"],
                "Detail": [
                    hist_corr.get("similarHistoricalPattern", "-"),
                    hist_corr.get("historicalSupportLevel", "-"),
                    hist_corr.get("historicalReasoning", "-"),
                ],
            }
        ).set_index("Field")
        st.table(df_hist)

    st.write(f"**Future Risk Projection:** {r.get('futureRiskProjection', '-')}")
    st.write(f"**Recurrence Justification:** {r.get('recurrenceJustification', '-')}")
    st.write(f"**Leading Indicators:** {r.get('leadingIndicators', '-')}")
    st.write(f"**Predictive Insight:** {r.get('predictiveInsight', '-')}")
    st.write(f"**Mitigation:** {r.get('mitigation', '-')}")
    st.write(f"**Recommendations:** {r.get('recommendations', '-')}")

st.divider()

# ---------------- PROJECT FORECAST INSIGHTS ---------------- #
st.subheader("Project Forecast Insights")

if forecast:
    fc1, fc2 = st.columns(2)

    with fc1:
        st.write("**Major Bottlenecks**")
        for item in forecast.get("majorBottlenecks", []):
            st.write(f"- {item}")

        st.write("**Risk Propagation Patterns**")
        for item in forecast.get("riskPropagationPatterns", []):
            st.write(f"- {item}")

        st.write("**Emerging Concerns**")
        for item in forecast.get("emergingConcerns", []):
            st.write(f"- {item}")

    with fc2:
        st.write("**High Risk Dependencies**")
        for item in forecast.get("highRiskDependencies", []):
            st.write(f"- {item}")

        st.write("**Root Cause Concentration**")
        for item in forecast.get("rootCauseConcentration", []):
            st.write(f"- {item}")

        st.write("**Most Likely Failure Triggers**")
        for item in forecast.get("mostLikelyFailureTriggers", []):
            st.write(f"- {item}")

    overall_outlook = forecast.get("overallOutlook")
    if overall_outlook:
        st.write("**Overall Outlook**")
        st.info(overall_outlook)
else:
    st.write("No forecast insights available for this project.")
