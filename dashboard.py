import streamlit as st
import json
import base64
import pandas as pd

st.set_page_config(layout="wide", page_title="Project Risk Dashboard")


def decode_data(encoded_str):
    decoded = base64.b64decode(encoded_str).decode("utf-8")
    return json.loads(decoded)


# ---------------- GET DATA ---------------- #
# Supports either ?data=<base64 json> in the URL, or a local risk_data.json file
# placed next to this script (useful for local testing without query params).
params = st.query_params
encoded_data = params.get("data")

data = None
if encoded_data:
    data = decode_data(encoded_data)
else:
    try:
        with open("risk_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        st.error("No dashboard data found in URL and no local risk_data.json present.")
        st.stop()

# ---------------- HEADER ---------------- #
st.title(f"📊 {data.get('project', 'Project Risk Dashboard')}")

status = data.get("projectStatus", "Unknown")
risk_score = data.get("overallRiskScore", 0)
risk_level = data.get("overallRiskLevel", "Unknown")

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

        st.write(f"**Priority:** {r.get('priority', '-')}  |  **Owner:** {r.get('suggestedOwner', '-')}  |  **Review Frequency:** {r.get('reviewFrequency', '-')}")

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
st.subheader("Consolidated Risks")

for cr in data.get("consolidatedRisks", []):
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
    st.write(f"**Average Risk Duration:** {hp.get('averageRiskDuration', '-')}")
    st.write(f"**Risk Resolution Rate:** {hp.get('riskResolutionRate', '-')}")
    owners = hp.get("topRiskOwners", [])
    if owners:
        st.write("**Top Risk Owners:**")
        for o in owners:
            st.write(f"- {o}")

trend_cols = st.columns(3)
severity_trends = hp.get("severityTrends", {})
likelihood_trends = hp.get("likelihoodTrends", {})
impact_trends = hp.get("impactTrends", {})

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

st.divider()

# ---------------- COMPLIANCE & SECURITY ---------------- #
st.subheader("Compliance & Security")

cs = data.get("complianceAndSecurity", {})
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