import streamlit as st
import requests
import base64
import json
import pandas as pd

st.set_page_config(layout="wide", page_title="Risk Dashboard")

# ---------------- CONFIG ---------------- #
GITHUB_REPO = "balamuruganravi963-design/risk"
GITHUB_BRANCH = "main"

GITHUB_READ_TOKEN = st.secrets.get("GITHUB_READ_TOKEN", "")

# ---------------- GET DATA ---------------- #
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

kpis = data.get("kpis", {})
all_risks = data.get("risks", [])
all_consolidated = data.get("consolidated_risks", [])

# ---------------- FIELD HELPERS ---------------- #
# These match the template field names used to generate the risk JSON.
# The exact key is tried first; the rest are fallbacks in case a given
# risk record is missing the field or uses an older key name.
CLIENT_KEYS = ["client", "clientName", "client_name", "account", "customer"]
PROJECT_KEYS = ["project", "projectName", "sow", "sowName", "engagement"]
VERTICAL_KEYS = ["vertical", "industry", "sector"]
STATUS_KEYS = ["projectStatus", "status", "project_status"]
RISK_TYPE_KEYS = ["riskType", "risk_type", "type"]


def get_first(d, keys, default=None):
    for k in keys:
        if isinstance(d, dict) and d.get(k):
            return d.get(k)
    return default


def split_combined(value):
    if not value:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [v.strip() for v in str(value).split(",") if v.strip()]


# project_name in this dataset is a combined string of every SOW/engagement
# name, e.g. "Centene Corporation (SOW) - SOW 110, Volvo Car USA LLC - ...".
project_level_clients = split_combined(kpis.get("project_name"))


def risk_client(r):
    """
    Returns the client name for a risk, or None if it can't be determined.
    1) Explicit "client" field on the risk object (authoritative).
    2) Heuristic text-match fallback, only used if no risk in the dataset
       has an explicit client field at all.
    A risk with no determinable client returns None and is NOT excluded
    by the client slicer (rather than being mislabeled).
    """
    val = get_first(r, CLIENT_KEYS)
    if val:
        return str(val)

    if len(project_level_clients) > 1:
        haystack = " ".join(str(x) for x in [
            r.get("title", ""), r.get("category", ""), r.get("reason", "")
        ]).lower()
        for name in project_level_clients:
            token = name.split("(")[0].split("-")[0].strip().split(" ")[0]
            if token and token.lower() in haystack:
                return name

    if len(project_level_clients) == 1:
        return project_level_clients[0]

    return None


def risk_project(r):
    return get_first(r, PROJECT_KEYS)


def risk_vertical(r):
    return get_first(r, VERTICAL_KEYS)


def risk_status(r):
    return get_first(r, STATUS_KEYS)


def risk_type(r):
    return get_first(r, RISK_TYPE_KEYS)


# ---------------- CASCADING SIDEBAR SLICERS ---------------- #
# Each filter's option list is computed from data already narrowed by the
# filters above it, so you can never pick a combination that yields zero
# results by construction. Widgets are re-created without a fixed "key" so
# their default always matches the currently valid option set (prevents
# Streamlit errors when a shrinking option list no longer contains a
# previously selected value).

st.sidebar.header("🔍 Filters")


def multiselect_options(values):
    return sorted({v for v in values if v})


pool = all_risks  # progressively narrowed subset

# --- Client ---
client_options = multiselect_options([risk_client(r) for r in pool] + project_level_clients)
sel_clients = st.sidebar.multiselect("Client Name", client_options, default=client_options)
if client_options:
    # Risks with an unknown client are kept regardless of selection,
    # since we can't confirm which client they belong to.
    pool = [r for r in pool if risk_client(r) is None or risk_client(r) in sel_clients]

# --- Project ---
project_options = multiselect_options([risk_project(r) for r in pool])
if project_options:
    sel_project = st.sidebar.multiselect("Project", project_options, default=project_options)
    pool = [r for r in pool if risk_project(r) is None or risk_project(r) in sel_project]

# --- Vertical ---
vertical_options = multiselect_options([risk_vertical(r) for r in pool])
if vertical_options:
    sel_vertical = st.sidebar.multiselect("Vertical", vertical_options, default=vertical_options)
    pool = [r for r in pool if risk_vertical(r) is None or risk_vertical(r) in sel_vertical]

# --- Project Status ---
status_options = multiselect_options([risk_status(r) for r in pool])
if status_options:
    sel_status = st.sidebar.multiselect("Project Status", status_options, default=status_options)
    pool = [r for r in pool if risk_status(r) is None or risk_status(r) in sel_status]

# --- Severity ---
severity_options = multiselect_options([r.get("severity") for r in pool])
sel_severity = st.sidebar.multiselect("Severity", severity_options, default=severity_options)
if severity_options:
    pool = [r for r in pool if r.get("severity") in sel_severity]

# --- Category ---
category_options = multiselect_options([r.get("category") for r in pool])
sel_category = st.sidebar.multiselect("Category", category_options, default=category_options)
if category_options:
    pool = [r for r in pool if r.get("category") in sel_category]

# --- Risk Type ---
risk_type_options = multiselect_options([risk_type(r) for r in pool])
if risk_type_options:
    sel_risk_type = st.sidebar.multiselect("Risk Type", risk_type_options, default=risk_type_options)
    pool = [r for r in pool if risk_type(r) is None or risk_type(r) in sel_risk_type]

# --- Priority ---
priority_options = multiselect_options([r.get("priority") for r in pool])
if priority_options:
    sel_priority = st.sidebar.multiselect("Priority", priority_options, default=priority_options)
    pool = [r for r in pool if r.get("priority") is None or r.get("priority") in sel_priority]

# --- Owner ---
owner_options = multiselect_options([r.get("owner") for r in pool])
if owner_options:
    sel_owner = st.sidebar.multiselect("Owner", owner_options, default=owner_options)
    pool = [r for r in pool if r.get("owner") is None or r.get("owner") in sel_owner]

if st.sidebar.button("Reset Filters"):
    st.rerun()

risks = pool

visible_titles = {r.get("title") for r in risks}
consolidated_risks = [
    cr for cr in all_consolidated
    if not cr.get("mergedFrom") or any(m in visible_titles for m in cr.get("mergedFrom", []))
] if all_consolidated else []

# ---------------- HEADER ---------------- #
st.title("📊 Risk Dashboard")

if len(project_level_clients) > 1:
    st.caption("Aggregated view across: " + ", ".join(project_level_clients))

status = kpis.get("project_status", "Unknown")
risk_score = kpis.get("overall_risk_score", 0)
risk_level = kpis.get("overall_risk_level", "Unknown")
total_predicted_risks = len(risks)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Project Status", status)
col2.metric("Overall Risk Score", risk_score)
col3.metric("Overall Risk Level", risk_level)
col4.metric("Total Predicted Risks", total_predicted_risks)

st.caption(f"Showing {len(risks)} of {len(all_risks)} risks based on selected filters.")

st.divider()

# ---------------- RISK SUMMARY KPIs ---------------- #
st.subheader("Risk Summary")

severity_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
for r in risks:
    sev = r.get("severity")
    if sev in severity_counts:
        severity_counts[sev] += 1

kc1, kc2, kc3, kc4 = st.columns(4)
kc1.metric("Critical", severity_counts["Critical"])
kc2.metric("High", severity_counts["High"])
kc3.metric("Medium", severity_counts["Medium"])
kc4.metric("Low", severity_counts["Low"])

st.divider()

# ---------------- CATEGORY DISTRIBUTION ---------------- #
st.subheader("Risk Category Distribution")

if risks:
    cat_counts = pd.Series([r.get("category", "Unknown") for r in risks]).value_counts()
    st.bar_chart(cat_counts)
else:
    st.write("No risks match the selected filters.")

st.divider()

# ---------------- RISKS ---------------- #
st.subheader("Predicted Risks")

if not risks:
    st.info("No risks match the current filter selection.")

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
