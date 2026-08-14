import streamlit as st
import requests
import base64
import json
import pandas as pd

st.set_page_config(layout="wide", page_title="Project Risk Dashboard")

# ---------------- CONFIG ---------------- #
GITHUB_REPO = "your-username/your-repo"
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

# ---------------- HEADER ---------------- #
kpis = data.get("kpis", {})

st.title(f"📊 {kpis.get('project_name', 'Project Risk Dashboard')}")

status = kpis.get("project_status", "Unknown")
risk_score = kpis.get("overall_risk_score", 0)
risk_level = kpis.get("overall_risk_level", "Unknown")
total_predicted_risks = kpis.get("total_predicted_risks", 0)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Project Status", status)
col2.metric("Overall Risk Score", risk_score)
col3.metric("Overall Risk Level", risk_level)
col4.metric("Total Predicted Risks", total_predicted_risks)

st.divider()

# ---------------- RISK SUMMARY KPIs ---------------- #
st.subheader("Risk Summary")

risk_summary = data.get("risk_summary", {})

kc1, kc2, kc3, kc4 = st.columns(4)
kc1.metric("Critical", risk_summary.get("critical", 0))
kc2.metric("High", risk_summary.get("high", 0))
kc3.metric("Medium", risk_summary.get("medium", 0))
kc4.metric("Low", risk_summary.get("low", 0))

st.divider()

# ---------------- CATEGORY DISTRIBUTION ---------------- #
st.subheader("Risk Category Distribution")

category_dist = data.get("category_distribution", [])
if category_dist:
    df_cat = pd.DataFrame(category_dist).set_index("segment")
    st.bar_chart(df_cat["value"])
else:
    st.write("No category distribution data available.")

st.divider()

# ---------------- RISKS ---------------- #
st.subheader("Predicted Risks")

risks = data.get("risks", [])

for r in risks:
    severity = r.get("severity", "Unknown")
    icon = {"Critical": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🟢"}.get(severity, "⚪")

    with st.expander(f"{icon} {r.get('title', 'Untitled Risk')} — {severity} (Confidence: {r.get('confidence', 0)}%)"):
        c1, c2, c3 = st.columns(3)
        c1.write(f"**Category:** {r.get('category', '-')}")
        c2.write(f"**Likelihood:** {r.get('likelihood', '-')}%")
        c3.write(f"**Impact:** {r.get('impact', '-')}")

        review_freq = r.get("reviewFrequency", "")
        owner_line = f"**Priority:** {r.get('priority', '-')}  |  **Owner:** {r.get('owner', '-')}"
        if review_freq:
            owner_line += f"  |  **Review Frequency:** {review_freq}"
        st.write(owner_line)

        st.write(f"**Reason:** {r.get('reason', '-')}")

        related = r.get("relatedHistoricalRisks", [])
        if related:
            st.write("**Related Historical Risks:**")
            for item in related:
                st.write(f"- {item}")

        actions = r.get("recommendedActions", [])
        if actions:
            st.write("**Recommended Actions:**")
            for a in actions:
                st.write(f"- {a}")

        st.write(f"**Preventive Action:** {r.get('preventiveActions', '-')}")
        st.write(f"**Mitigation:** {r.get('mitigation', '-')}")
        st.write(f"**Contingency:** {r.get('contingency', '-')}")

st.divider()

# ---------------- CONSOLIDATED RISKS ---------------- #
consolidated_risks = data.get("consolidated_risks", [])
if consolidated_risks:
    st.subheader("Consolidated Risks")
    for cr in consolidated_risks:
        with st.expander(f"🔗 {cr.get('title', 'Untitled')} (Occurrences: {cr.get('occurrences', 0)}, Confidence: {cr.get('confidence', 0)}%)"):
            st.write(f"**Description:** {cr.get('description', '-')}")
            st.write(f"**Root Cause:** {cr.get('rootCause', '-')}")
            st.write(f"**Business Impact:** {cr.get('businessImpact', '-')}")
            merged = cr.get("mergedFrom", [])
            if merged:
                st.write("**Merged From:**")
                for m in merged:
                    st.write(f"- {m}")
    st.divider()

# ---------------- HISTORICAL PATTERNS ---------------- #
st.subheader("Historical Patterns")

hp = data.get("historical_patterns", {})

hc1, hc2 = st.columns(2)

with hc1:
    st.write("**Most Frequent Risk Categories**")
    for item in hp.get("mostFrequentRiskCategories", []):
        st.write(f"- {item}")

    st.write("**Common Risk Types**")
    for item in hp.get("commonRiskTypes", []):
        st.write(f"- {item}")

with hc2:
    if hp.get("averageRiskDuration"):
        st.write(f"**Average Risk Duration:** {hp.get('averageRiskDuration')}")
    if hp.get("riskResolutionRate"):
        st.write(f"**Risk Resolution Rate:** {hp.get('riskResolutionRate')}")
    owners = hp.get("topRiskOwners", [])
    if owners:
        st.write("**Top Risk Owners:**")
        for o in owners:
            st.write(f"- {o}")

    status_dist = hp.get("statusDistribution", {})
    if status_dist:
        st.write("**Status Distribution**")
        for k, v in status_dist.items():
            st.write(f"- {k}: {v}")

trend_cols = st.columns(3)
severity_trends = {k: v for k, v in hp.get("severityTrends", {}).items() if isinstance(v, (int, float))}
likelihood_trends = {k: v for k, v in hp.get("likelihoodTrends", {}).items() if isinstance(v, (int, float))}
impact_trends = {k: v for k, v in hp.get("impactTrends", {}).items() if isinstance(v, (int, float))}

if severity_trends:
    with trend_cols[0]:
        st.write("**Severity Trends**")
        st.bar_chart(pd.Series(severity_trends))

if likelihood_trends:
    with trend_cols[1]:
        st.write("**Likelihood Trends**")
        st.bar_chart(pd.Series(likelihood_trends))

if impact_trends:
    with trend_cols[2]:
        st.write("**Impact Trends**")
        st.bar_chart(pd.Series(impact_trends))

st.divider()

# ---------------- RISK CHAINS ---------------- #
st.subheader("Risk Chains")

for rc in data.get("risk_chains", []):
    with st.expander(f"⛓️ {rc.get('chainTitle', 'Untitled Chain')} — Overall Impact: {rc.get('overallImpact', '-')}"):
        sequence = rc.get("sequence", [])
        if sequence:
            st.write(" → ".join(sequence))
        st.write(f"**Description:** {rc.get('description', '-')}")
        st.write(f"**Mitigation Approach:** {rc.get('mitigationApproach', '-')}")

st.divider()

# ---------------- KEY INSIGHTS ---------------- #
st.subheader("Key Insights")

ki = data.get("key_insights", {})

ic1, ic2 = st.columns(2)
with ic1:
    st.write("**Strengths**")
    for s in ki.get("strengths", []):
        st.success(s)

with ic2:
    st.write("**Weaknesses**")
    for w in ki.get("weaknesses", []):
        st.warning(w)

lessons = ki.get("lessonsLearned", [])
if lessons:
    st.write("**Lessons Learned**")
    for l in lessons:
        st.write(f"- {l}")

success_factors = ki.get("successFactors", [])
if success_factors:
    st.write("**Success Factors**")
    for sf in success_factors:
        st.write(f"- {sf}")

st.divider()

# ---------------- COMPLIANCE & SECURITY ---------------- #
cs = data.get("compliance_and_security", {})
if any(cs.get(k) for k in ["dataProtection", "encryption", "auditLog", "accessControl", "dataRetention"]):
    st.subheader("Compliance & Security")
    for label, key in [
        ("Data Protection", "dataProtection"),
        ("Encryption", "encryption"),
        ("Audit Log", "auditLog"),
        ("Access Control", "accessControl"),
        ("Data Retention", "dataRetention"),
    ]:
        val = cs.get(key)
        if val:
            st.write(f"**{label}:** {val}")
