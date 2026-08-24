import streamlit as st
import requests
import base64
import json
import pandas as pd
from datetime import datetime

st.set_page_config(layout="wide", page_title="Enriched Risk Dashboard")

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

# Extract top-level data
projects = data.get("projects", [])
summary_stats = data.get("summaryStatistics", {})

# Flatten all enriched risks across projects for easier filtering
all_enriched_risks = []
for project in projects:
    project_name = project.get("projectName", "Unknown")
    for risk in project.get("enrichedCurrentRisks", []):
        risk["project"] = project_name
        all_enriched_risks.append(risk)

# ---------------- FIELD HELPERS & UTILITIES ---------------- #
def get_severity_icon(severity):
    """Return emoji icon for severity level"""
    return {
        "Critical": "🔴",
        "High": "🟠",
        "Medium": "🟡",
        "Low": "🟢"
    }.get(severity, "⚪")


def parse_list_field(value):
    """Convert string, list, or comma-separated value to list"""
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return []


def safe_get(obj, key, default=""):
    """Safely get nested or top-level dict values"""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return default


# ---------------- CASCADING SIDEBAR SLICERS ---------------- #
st.sidebar.header("🔍 Filters")

pool = all_enriched_risks.copy()

# --- Project ---
project_options = sorted({r.get("project", "Unknown") for r in pool if r.get("project")})
if project_options:
    sel_projects = st.sidebar.multiselect("Project", project_options, default=project_options)
    pool = [r for r in pool if r.get("project") in sel_projects]

# --- Severity ---
severity_options = ["Critical", "High", "Medium", "Low"]
sel_severity = st.sidebar.multiselect(
    "Severity",
    severity_options,
    default=severity_options
)
if sel_severity:
    pool = [r for r in pool if r.get("severity") in sel_severity]

# --- Category ---
category_options = sorted({r.get("category", "Unknown") for r in pool if r.get("category")})
if category_options:
    sel_category = st.sidebar.multiselect("Category", category_options, default=category_options)
    pool = [r for r in pool if r.get("category") in sel_category]

# --- Risk Type ---
risk_type_options = sorted({r.get("riskType", "Unknown") for r in pool if r.get("riskType")})
if risk_type_options:
    sel_risk_type = st.sidebar.multiselect("Risk Type", risk_type_options, default=risk_type_options)
    pool = [r for r in pool if r.get("riskType") in sel_risk_type]

# --- Mitigation Owner ---
owner_options = sorted({r.get("mitigation", {}).get("mitigationOwner", "Unknown") for r in pool if r.get("mitigation")})
if owner_options:
    sel_owners = st.sidebar.multiselect("Mitigation Owner", owner_options, default=owner_options)
    pool = [r for r in pool if r.get("mitigation", {}).get("mitigationOwner") in sel_owners]

# --- Mitigation Priority ---
priority_options = ["Critical", "High", "Medium", "Low"]
sel_priority = st.sidebar.multiselect(
    "Mitigation Priority",
    priority_options,
    default=priority_options
)
if sel_priority:
    pool = [r for r in pool if r.get("mitigation", {}).get("mitigationPriority") in sel_priority]

# Reset Filters
if st.sidebar.button("Reset Filters"):
    st.rerun()

filtered_risks = pool

# ---------------- HEADER & SUMMARY STATS ---------------- #
st.title("📊 Enriched Risk Dashboard")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Projects", summary_stats.get("totalProjects", 0))
col2.metric("Projects With Risks", summary_stats.get("projectsWithEnrichedRisks", 0))
col3.metric("Total Enriched Risks", summary_stats.get("totalEnrichedRisks", 0))
col4.metric("Filtered Risks", len(filtered_risks))

st.caption(f"Showing {len(filtered_risks)} of {len(all_enriched_risks)} risks based on selected filters.")

st.divider()

# ---------------- RISK SUMMARY BY SEVERITY & PRIORITY ---------------- #
st.subheader("Risk Summary")

severity_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
priority_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}

for r in filtered_risks:
    sev = r.get("severity")
    if sev in severity_counts:
        severity_counts[sev] += 1
    
    prio = r.get("mitigation", {}).get("mitigationPriority")
    if prio in priority_counts:
        priority_counts[prio] += 1

col1, col2 = st.columns(2)

with col1:
    st.write("**Severity Distribution**")
    sc1, sc2, sc3, sc4 = st.columns(4)
    sc1.metric("Critical", severity_counts["Critical"])
    sc2.metric("High", severity_counts["High"])
    sc3.metric("Medium", severity_counts["Medium"])
    sc4.metric("Low", severity_counts["Low"])

with col2:
    st.write("**Mitigation Priority Distribution**")
    pc1, pc2, pc3, pc4 = st.columns(4)
    pc1.metric("Critical", priority_counts["Critical"])
    pc2.metric("High", priority_counts["High"])
    pc3.metric("Medium", priority_counts["Medium"])
    pc4.metric("Low", priority_counts["Low"])

st.divider()

# ---------------- CATEGORY & RISK TYPE DISTRIBUTION ---------------- #
st.subheader("Risk Distribution")

if filtered_risks:
    col1, col2 = st.columns(2)
    
    with col1:
        cat_counts = pd.Series([r.get("category", "Unknown") for r in filtered_risks]).value_counts()
        st.write("**By Category**")
        st.bar_chart(cat_counts)
    
    with col2:
        type_counts = pd.Series([r.get("riskType", "Unknown") for r in filtered_risks]).value_counts()
        st.write("**By Risk Type**")
        st.bar_chart(type_counts)
else:
    st.info("No risks match the selected filters.")

st.divider()

# ---------------- ENRICHED RISKS DETAIL VIEW ---------------- #
st.subheader("Enriched Risks")

if not filtered_risks:
    st.info("No risks match the current filter selection.")
else:
    # Create sortable risk list
    sort_by = st.selectbox("Sort by:", ["Severity (High→Low)", "Confidence Score (High→Low)", "Title (A→Z)"])
    
    if sort_by == "Severity (High→Low)":
        severity_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
        sorted_risks = sorted(filtered_risks, key=lambda r: severity_order.get(r.get("severity"), 99))
    elif sort_by == "Confidence Score (High→Low)":
        sorted_risks = sorted(filtered_risks, key=lambda r: r.get("confidenceScore", 0), reverse=True)
    else:
        sorted_risks = sorted(filtered_risks, key=lambda r: r.get("riskTitle", ""))
    
    for i, r in enumerate(sorted_risks, 1):
        severity = r.get("severity", "Unknown")
        icon = get_severity_icon(severity)
        risk_title = r.get("riskTitle", "Untitled Risk")
        confidence = r.get("confidenceScore", 0)
        
        with st.expander(f"{i}. {icon} {risk_title} — {severity} (Confidence: {confidence}%)"):
            # --- Risk Core Information ---
            st.write("### Core Information")
            rcol1, rcol2, rcol3 = st.columns(3)
            rcol1.write(f"**Project:** {r.get('project', 'Unknown')}")
            rcol2.write(f"**Risk ID:** {r.get('riskID', '-')}")
            rcol3.write(f"**Risk Type:** {r.get('riskType', '-')}")
            
            st.write(f"**Description:** {r.get('riskDescription', '-')}")
            
            # --- Risk Assessment ---
            st.write("### Risk Assessment")
            acol1, acol2, acol3, acol4 = st.columns(4)
            acol1.write(f"**Category:** {r.get('category', '-')}")
            acol2.write(f"**Likelihood:** {r.get('likelihood', '-')}")
            acol3.write(f"**Severity:** {r.get('severity', '-')}")
            acol4.write(f"**Business Impact:** {r.get('businessImpact', '-')}")
            
            # --- Current Context ---
            st.write("### Current Context")
            st.write(f"**Evidence:** {r.get('currentProjectEvidence', '-')}")
            st.write(f"**Reasoning:** {r.get('currentContextReasoning', '-')}")
            
            # --- Risk Chain ---
            st.write("### Risk Chain Analysis")
            chain = r.get("riskChain", {})
            chain_col1, chain_col2 = st.columns(2)
            
            with chain_col1:
                st.write(f"**Root Cause:** {chain.get('rootCause', '-')}")
                st.write(f"**Trigger:** {chain.get('trigger', '-')}")
                st.write(f"**Primary Risk:** {chain.get('primaryRisk', '-')}")
            
            with chain_col2:
                st.write(f"**Downstream Risk:** {chain.get('downstreamRisk', '-')}")
                st.write(f"**Overall Impact:** {chain.get('impact', '-')}")
            
            # --- Historical Correlation ---
            st.write("### Historical Correlation")
            hist_corr = r.get("historicalCorrelation", {})
            st.write(f"**Similar Historical Pattern:** {hist_corr.get('similarHistoricalPattern', '-')}")
            st.write(f"**Support Level:** {hist_corr.get('historicalSupportLevel', '-')}")
            st.write(f"**Reasoning:** {hist_corr.get('historicalReasoning', '-')}")
            
            # --- Forward-Looking Analysis ---
            st.write("### Forward-Looking Analysis")
            st.write(f"**Future Projection:** {r.get('futureRiskProjection', '-')}")
            st.write(f"**Recurrence Justification:** {r.get('recurrenceJustification', '-')}")
            st.write(f"**Leading Indicators:** {r.get('leadingIndicators', '-')}")
            st.write(f"**Predictive Insight:** {r.get('predictiveInsight', '-')}")
            
            # --- Mitigation Strategy ---
            st.write("### Mitigation Strategy")
            mitigation = r.get("mitigation", {})
            st.write(f"**Strategy:** {mitigation.get('mitigationStrategy', '-')}")
            
            actions = parse_list_field(mitigation.get("mitigationActions", []))
            if actions:
                st.write("**Actions:**")
                for action in actions:
                    st.write(f"- {action}")
            
            mcol1, mcol2, mcol3 = st.columns(3)
            mcol1.write(f"**Owner:** {mitigation.get('mitigationOwner', '-')}")
            mcol2.write(f"**Priority:** {mitigation.get('mitigationPriority', '-')}")
            mcol3.write(f"**Confidence Score:** {r.get('confidenceScore', '-')}%")
            
            # --- Recommendations ---
            st.write("### Recommendations")
            recommendations = r.get("recommendations", {})
            
            rec_col1, rec_col2 = st.columns(2)
            
            with rec_col1:
                st.write("**Immediate Actions:**")
                st.write(recommendations.get('immediateRecommendations', '-'))
            
            with rec_col2:
                st.write("**Preventive Measures:**")
                st.write(recommendations.get('preventiveRecommendations', '-'))
            
            st.write("**Monitoring & Review:**")
            st.write(recommendations.get('monitoringRecommendations', '-'))

st.divider()

# ---------------- SUMMARY STATISTICS BY PROJECT ---------------- #
st.subheader("Summary Statistics by Project")

risks_by_project = summary_stats.get("enrichedRisksByProject", [])

if risks_by_project:
    project_stats = pd.DataFrame(risks_by_project)
    st.dataframe(project_stats, use_container_width=True, hide_index=True)
    
    st.write("**Risk Breakdown by Project & Severity:**")
    project_risk_details = []
    
    for project in projects:
        project_name = project.get("projectName", "Unknown")
        proj_risks = [r for r in all_enriched_risks if r.get("project") == project_name]
        
        if proj_risks:
            severity_breakdown = {
                "Project": project_name,
                "Critical": sum(1 for r in proj_risks if r.get("severity") == "Critical"),
                "High": sum(1 for r in proj_risks if r.get("severity") == "High"),
                "Medium": sum(1 for r in proj_risks if r.get("severity") == "Medium"),
                "Low": sum(1 for r in proj_risks if r.get("severity") == "Low"),
                "Total": len(proj_risks)
            }
            project_risk_details.append(severity_breakdown)
    
    if project_risk_details:
        detail_df = pd.DataFrame(project_risk_details)
        st.dataframe(detail_df, use_container_width=True, hide_index=True)

st.divider()

# ---------------- KEY METRICS SUMMARY ------- #
st.subheader("Key Metrics")

metric_col1, metric_col2, metric_col3 = st.columns(3)

with metric_col1:
    st.metric(
        "Avg Confidence Score",
        f"{sum(r.get('confidenceScore', 0) for r in filtered_risks) / len(filtered_risks) if filtered_risks else 0:.1f}%"
    )

with metric_col2:
    critical_count = sum(1 for r in filtered_risks if r.get("severity") == "Critical")
    st.metric("Critical Risks", critical_count, delta="⚠️" if critical_count > 0 else "✓")

with metric_col3:
    highest_confidence = max([r.get("confidenceScore", 0) for r in filtered_risks]) if filtered_risks else 0
    st.metric("Highest Confidence", f"{highest_confidence:.0f}%")

st.divider()

# --- Footer ---
st.caption(f"Dashboard generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Data source: GitHub {GITHUB_BRANCH} branch")
