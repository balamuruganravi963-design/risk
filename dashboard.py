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
st.title(f"📊 {data.get('project', 'Project Risk Dashboard')}")

client = data.get("Client", "")
status = data.get("projectStatus", "Unknown")
risk_score = data.get("overallRiskScore", 0)
risk_level = data.get("overallRiskLevel", "Unknown")

if client:
    st.caption(f"Client: {client}")

col1, col2, col3 = st.columns(3)
col1.metric("Project Status", status)
col2.metric("Overall Risk Score", risk_score)
col3.metric("Overall Risk Level", risk_level)

st.divider()

# ---------------- RISK SUMMARY KPIs ---------------- #
st.subheader("Risk Summary")

risk_summary = data.get("riskSummary", {})
predicted_risks = data.get("predictedRisks", [])

kc1, kc2, kc3, kc4, kc5 = st.columns(5)
kc1.metric("Critical", risk_summary.get("critical", 0))
kc2.metric("High", risk_summary.get("high", 0))
kc3.metric("Medium", risk_summary.get("medium", 0))
kc4.metric("Low", risk_summary.get("low", 0))
kc5.metric("Total Predicted Risks", len(predicted_risks))

st.divider()

# ---------------- CATEGORY DISTRIBUTION ---------------- #
st.subheader("Risk Category Distribution")

category_dist = data.get("categoryDistribution", [])
if category_dist:
    df_cat = pd.DataFrame(category_dist).set_index("category")
    st.bar_chart(df_cat["count"])
else:
    st.write("No category distribution data available.")

st.divider()

# ---------------- PREDICTED RISKS ---------------- #
st.subheader("Predicted Risks")

for r in predicted_risks:
    severity = r.get("severity", "Unknown")
    icon = {"Critical": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🟢"}.get(severity, "⚪")

    with st.expander(f"{icon} {r.get('riskTitle', 'Untitled Risk')} — {severity} (Confidence: {r.get('confidence', 0)}%)"):
        c1, c2, c3 = st.columns(3)
        c1.write(f"**Category:** {r.get('category', '-')}")
        c2.write(f"**Likelihood:** {r.get('likelihood', '-')}%")
        c3.write(f"**Impact:** {r.get('impact', '-')}")

        review_freq = r.get("reviewFrequency", "")
        owner_line = f"**Priority:** {r.get('priority', '-')}  |  **Owner:** {r.get('suggestedOwner', '-')}"
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

# ---------------- CONSOLIDATED RISKS (optional) ---------------- #
consolidated_risks = data.get("consolidatedRisks", [])
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

hp = data.get("historicalPatterns", {})

hc1, hc2 = st.columns(2)

with hc1:
    st.write("**Most Frequent Risk Categories**")
    for item in hp.get("mostFrequentRiskCategories", []):
        st.write(f"- {item}")

    st.write("**Common Risk Types**")
    for item in hp.get("commonRiskTypes", []):
        st.write(f"- {item}")

with hc2:
    risk_freq = hp.get("riskFrequency", {})
    if risk_freq:
        st.write("**Risk Frequency**")
        for k, v in risk_freq.items():
            st.write(f"- {k}: {v}")

    if hp.get("averageRiskDuration"):
        st.write(f"**Average Risk Duration:** {hp.get('averageRiskDuration')}")
    if hp.get("riskResolutionRate"):
        st.write(f"**Risk Resolution Rate:** {hp.get('riskResolutionRate')}")
    owners = hp.get("topRiskOwners", [])
    if owners:
        st.write("**Top Risk Owners:**")
        for o in owners:
            st.write(f"- {o}")

trend_cols = st.columns(3)
severity_trends = {k: v for k, v in hp.get("severityTrends", {}).items() if isinstance(v, (int, float))}
likelihood_trends = {k: v for k, v in hp.get("likelihoodTrends", {}).items() if isinstance(v, (int, float))}
impact_data = hp.get("impactAnalysis", hp.get("impactTrends", {}))
impact_trends = {k: v for k, v in impact_data.items() if isinstance(v, (int, float))}

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

for label, obj in [("Severity", hp.get("severityTrends", {})),
                    ("Likelihood", hp.get("likelihoodTrends", {})),
                    ("Impact", impact_data),
                    ("Status", hp.get("statusEffects", {}))]:
    desc = obj.get("distribution") or obj.get("description")
    if desc:
        st.caption(f"{label}: {desc}")

st.divider()

# ---------------- RISK CHAINS ---------------- #
st.subheader("Risk Chains")

for rc in data.get("riskChains", []):
    with st.expander(f"⛓️ {rc.get('chainTitle', 'Untitled Chain')} — Overall Impact: {rc.get('overallImpact', '-')}"):
        sequence = rc.get("sequence", [])
        if sequence:
            st.write(" → ".join(sequence))
        st.write(f"**Description:** {rc.get('description', '-')}")
        st.write(f"**Mitigation Approach:** {rc.get('mitigationApproach', '-')}")

st.divider()

# ---------------- KEY INSIGHTS ---------------- #
st.subheader("Key Insights")

ki = data.get("keyInsights", {})
health = ki.get("projectHealthIndicators", {})

ic1, ic2 = st.columns(2)
with ic1:
    st.write("**Strengths**")
    for s in health.get("strengths", []):
        st.success(s)

with ic2:
    st.write("**Weaknesses**")
    for w in health.get("weaknesses", []):
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

critical_deps = ki.get("criticalDependencies", [])
if critical_deps:
    st.write("**Critical Dependencies**")
    for cd in critical_deps:
        st.write(f"- {cd}")

financial_exposure = ki.get("financialRiskExposure", {})
if financial_exposure:
    st.write("**Financial Risk Exposure**")
    for k, v in financial_exposure.items():
        st.write(f"- **{k}:** {v}")

st.divider()

# ---------------- COMPLIANCE & SECURITY (optional) ---------------- #
cs = data.get("complianceAndSecurity", {})
if cs:
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
