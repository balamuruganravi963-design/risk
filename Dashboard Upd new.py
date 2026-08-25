import streamlit as st
import requests
import base64
import json
import pandas as pd
from datetime import datetime


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    layout="wide",
    page_title="Risk Intelligence Dashboard"
)


# ============================================================
# CONFIG
# ============================================================

GITHUB_REPO = "balamuruganravi963-design/risk"
GITHUB_BRANCH = "main"
GITHUB_READ_TOKEN = st.secrets.get("GITHUB_READ_TOKEN", "")


# ============================================================
# GET FILE PATH FROM DASHBOARD URL
# ============================================================

params = st.query_params
file_path = params.get("path")

if not file_path:
    st.error("No file path found in URL")
    st.stop()


# ============================================================
# LOAD JSON FROM GITHUB
# ============================================================

api_url = (
    f"https://api.github.com/repos/"
    f"{GITHUB_REPO}/contents/{file_path}"
)

headers = {
    "Accept": "application/vnd.github+json"
}

if GITHUB_READ_TOKEN:
    headers["Authorization"] = f"token {GITHUB_READ_TOKEN}"


response = requests.get(
    api_url,
    headers=headers,
    params={"ref": GITHUB_BRANCH},
    timeout=15
)

if response.status_code != 200:
    st.error(
        f"Failed to load dashboard data "
        f"(status {response.status_code})."
    )
    st.stop()


file_data = response.json()

try:
    content = base64.b64decode(
        file_data["content"]
    ).decode("utf-8")

    data = json.loads(content)

except Exception as e:
    st.error(f"Failed to parse dashboard JSON: {e}")
    st.stop()


# ============================================================
# EXTRACT NEW JSON STRUCTURE
#
# {
#   "portfolio_summary": {},
#   "projects": [
#       {
#           "project_name": "",
#           "kpis": {},
#           "risk_summary": {},
#           "category_distribution": [],
#           "risk_type_distribution": [],
#           "risks": [],
#           "risk_chains": [],
#           "historical_risk_summary": {},
#           "predictive_insights": {},
#           "risk_concentration": {},
#           "risk_forecast_insights": {}
#       }
#   ]
# }
# ============================================================

projects = data.get("projects", [])

portfolio_summary = data.get(
    "portfolio_summary",
    {}
)


# ============================================================
# FLATTEN ALL PROJECT RISKS
# ============================================================

all_risks = []

for project in projects:

    project_name = project.get(
        "project_name",
        "Unknown"
    )

    project_risks = project.get(
        "risks",
        []
    )

    for risk in project_risks:

        risk_copy = risk.copy()

        risk_copy["project"] = project_name

        all_risks.append(risk_copy)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_severity_icon(severity):

    return {
        "Critical": "🔴",
        "High": "🟠",
        "Medium": "🟡",
        "Low": "🟢"
    }.get(
        str(severity).strip().title(),
        "⚪"
    )


def safe_get(obj, key, default=""):

    if isinstance(obj, dict):
        return obj.get(key, default)

    return default


def normalize_text(value):

    if value is None:
        return ""

    return str(value).strip()


def confidence_rank(value):

    """
    Convert categorical confidence into a sortable rank.

    New JSON uses:
        High
        Medium
        Low
        None

    It does NOT use numeric confidence percentages.
    """

    ranking = {
        "High": 3,
        "Medium": 2,
        "Low": 1,
        "None": 0
    }

    return ranking.get(
        normalize_text(value).title(),
        -1
    )


def severity_rank(value):

    ranking = {
        "Critical": 0,
        "High": 1,
        "Medium": 2,
        "Low": 3
    }

    return ranking.get(
        normalize_text(value).title(),
        99
    )


def parse_recommendations(value):

    """
    Recommendations in the new JSON are strings.

    Example:
        1. Do X.
        2. Do Y.
        3. Do Z.

    Display them as individual numbered items
    when possible.
    """

    if isinstance(value, list):
        return [
            str(v).strip()
            for v in value
            if str(v).strip()
        ]

    if not isinstance(value, str):
        return []

    lines = value.split("\n")

    cleaned = []

    for line in lines:

        line = line.strip()

        if line:
            cleaned.append(line)

    return cleaned


# ============================================================
# SIDEBAR FILTERS
# ============================================================

st.sidebar.header("🔍 Filters")

pool = all_risks.copy()


# ------------------------------------------------------------
# PROJECT FILTER
# ------------------------------------------------------------

project_options = sorted(
    {
        r.get("project", "Unknown")
        for r in pool
        if r.get("project")
    }
)

if project_options:

    selected_projects = st.sidebar.multiselect(
        "Project",
        project_options,
        default=project_options
    )

    pool = [
        r for r in pool
        if r.get("project") in selected_projects
    ]


# ------------------------------------------------------------
# SEVERITY FILTER
# ------------------------------------------------------------

severity_options = [
    "Critical",
    "High",
    "Medium",
    "Low"
]

selected_severity = st.sidebar.multiselect(
    "Severity",
    severity_options,
    default=severity_options
)

if selected_severity:

    pool = [
        r for r in pool
        if r.get("severity") in selected_severity
    ]


# ------------------------------------------------------------
# CATEGORY FILTER
# ------------------------------------------------------------

category_options = sorted(
    {
        r.get("category", "Unknown")
        for r in pool
        if r.get("category")
    }
)

if category_options:

    selected_categories = st.sidebar.multiselect(
        "Category",
        category_options,
        default=category_options
    )

    pool = [
        r for r in pool
        if r.get("category") in selected_categories
    ]


# ------------------------------------------------------------
# RISK TYPE FILTER
# ------------------------------------------------------------

risk_type_options = sorted(
    {
        r.get("riskType", "Unknown")
        for r in pool
        if r.get("riskType")
    }
)

if risk_type_options:

    selected_risk_types = st.sidebar.multiselect(
        "Risk Type",
        risk_type_options,
        default=risk_type_options
    )

    pool = [
        r for r in pool
        if r.get("riskType") in selected_risk_types
    ]


# ------------------------------------------------------------
# HISTORICAL SUPPORT FILTER
# ------------------------------------------------------------

historical_support_options = sorted(
    {
        r.get(
            "historicalCorrelation",
            {}
        ).get(
            "historicalSupportLevel",
            ""
        )
        for r in pool
        if r.get("historicalCorrelation")
    }
)

historical_support_options = [
    x for x in historical_support_options
    if x
]

if historical_support_options:

    selected_historical_support = st.sidebar.multiselect(
        "Historical Support",
        historical_support_options,
        default=historical_support_options
    )

    pool = [
        r for r in pool
        if r.get(
            "historicalCorrelation",
            {}
        ).get(
            "historicalSupportLevel",
            ""
        ) in selected_historical_support
    ]


# ------------------------------------------------------------
# LIKELIHOOD FILTER
# ------------------------------------------------------------

likelihood_options = sorted(
    {
        r.get("likelihood", "")
        for r in pool
        if r.get("likelihood")
    }
)

if likelihood_options:

    selected_likelihood = st.sidebar.multiselect(
        "Likelihood",
        likelihood_options,
        default=likelihood_options
    )

    pool = [
        r for r in pool
        if r.get("likelihood")
        in selected_likelihood
    ]


# ------------------------------------------------------------
# RESET FILTERS
# ------------------------------------------------------------

if st.sidebar.button("Reset Filters"):
    st.rerun()


filtered_risks = pool


# ============================================================
# HEADER
# ============================================================

st.title("📊 Risk Intelligence Dashboard")

st.caption(
    "Multi-project risk analysis, historical intelligence, "
    "risk propagation, and mitigation insights."
)


# ============================================================
# PORTFOLIO KPI CARDS
# ============================================================

st.subheader("Portfolio Overview")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Total Projects",
    portfolio_summary.get(
        "totalProjects",
        len(projects)
    )
)

col2.metric(
    "Projects With Risks",
    portfolio_summary.get(
        "projectsWithCurrentRisks",
        0
    )
)

col3.metric(
    "Total Current Risks",
    portfolio_summary.get(
        "totalCurrentRisks",
        len(all_risks)
    )
)

col4.metric(
    "Filtered Risks",
    len(filtered_risks)
)

st.caption(
    f"Showing {len(filtered_risks)} of "
    f"{len(all_risks)} risks based on selected filters."
)

st.divider()


# ============================================================
# RISK SUMMARY
# ============================================================

st.subheader("Risk Summary")

severity_counts = {
    "Critical": 0,
    "High": 0,
    "Medium": 0,
    "Low": 0
}

for risk in filtered_risks:

    severity = risk.get(
        "severity",
        ""
    )

    if severity in severity_counts:
        severity_counts[severity] += 1


sc1, sc2, sc3, sc4 = st.columns(4)

sc1.metric(
    "Critical",
    severity_counts["Critical"]
)

sc2.metric(
    "High",
    severity_counts["High"]
)

sc3.metric(
    "Medium",
    severity_counts["Medium"]
)

sc4.metric(
    "Low",
    severity_counts["Low"]
)


st.divider()


# ============================================================
# CATEGORY & RISK TYPE DISTRIBUTION
# ============================================================

st.subheader("Risk Distribution")

if filtered_risks:

    col1, col2 = st.columns(2)

    # --------------------------------------------------------
    # CATEGORY
    # --------------------------------------------------------

    with col1:

        category_counts = pd.Series(
            [
                r.get(
                    "category",
                    "Unknown"
                )
                for r in filtered_risks
            ]
        ).value_counts()

        st.write("**By Category**")

        st.bar_chart(
            category_counts
        )

    # --------------------------------------------------------
    # RISK TYPE
    # --------------------------------------------------------

    with col2:

        risk_type_counts = pd.Series(
            [
                r.get(
                    "riskType",
                    "Unknown"
                )
                for r in filtered_risks
            ]
        ).value_counts()

        st.write("**By Risk Type**")

        st.bar_chart(
            risk_type_counts
        )

else:

    st.info(
        "No risks match the selected filters."
    )


st.divider()


# ============================================================
# HISTORICAL SUPPORT DISTRIBUTION
# ============================================================

st.subheader("Historical Risk Support")

if filtered_risks:

    historical_support_counts = pd.Series(
        [
            r.get(
                "historicalCorrelation",
                {}
            ).get(
                "historicalSupportLevel",
                "Unknown"
            )
            for r in filtered_risks
        ]
    ).value_counts()

    st.bar_chart(
        historical_support_counts
    )


st.divider()


# ============================================================
# RISK DETAILS
# ============================================================

st.subheader("Risk Details")

if not filtered_risks:

    st.info(
        "No risks match the current filter selection."
    )

else:

    sort_by = st.selectbox(
        "Sort by:",
        [
            "Severity (High → Low)",
            "Confidence (High → Low)",
            "Title (A → Z)"
        ]
    )

    # --------------------------------------------------------
    # SORT RISKS
    # --------------------------------------------------------

    if sort_by == "Severity (High → Low)":

        sorted_risks = sorted(
            filtered_risks,
            key=lambda r: severity_rank(
                r.get("severity")
            )
        )

    elif sort_by == "Confidence (High → Low)":

        sorted_risks = sorted(
            filtered_risks,
            key=lambda r: confidence_rank(
                r.get("confidence")
            ),
            reverse=True
        )

    else:

        sorted_risks = sorted(
            filtered_risks,
            key=lambda r: normalize_text(
                r.get("title", "")
            ).lower()
        )


    # --------------------------------------------------------
    # DISPLAY EACH RISK
    # --------------------------------------------------------

    for i, risk in enumerate(
        sorted_risks,
        1
    ):

        severity = risk.get(
            "severity",
            "Unknown"
        )

        icon = get_severity_icon(
            severity
        )

        risk_title = risk.get(
            "title",
            "Untitled Risk"
        )

        confidence = risk.get(
            "confidence",
            ""
        )

        with st.expander(
            f"{i}. {icon} {risk_title} "
            f"— {severity} "
            f"(Confidence: {confidence})"
        ):

            # =================================================
            # CORE INFORMATION
            # =================================================

            st.write(
                "### Core Information"
            )

            rcol1, rcol2, rcol3, rcol4 = st.columns(4)

            rcol1.write(
                f"**Project:** "
                f"{risk.get('project', '-')}"
            )

            rcol2.write(
                f"**Risk ID:** "
                f"{risk.get('riskID', '-')}"
            )

            rcol3.write(
                f"**Category:** "
                f"{risk.get('category', '-')}"
            )

            rcol4.write(
                f"**Risk Type:** "
                f"{risk.get('riskType', '-')}"
            )

            st.write(
                f"**Title:** "
                f"{risk.get('title', '-')}"
            )

            st.write(
                f"**Description:** "
                f"{risk.get('description', '-')}"
            )


            # =================================================
            # RISK ASSESSMENT
            # =================================================

            st.write(
                "### Risk Assessment"
            )

            acol1, acol2, acol3, acol4 = st.columns(4)

            acol1.write(
                f"**Likelihood:** "
                f"{risk.get('likelihood', '-')}"
            )

            acol2.write(
                f"**Severity:** "
                f"{risk.get('severity', '-')}"
            )

            acol3.write(
                f"**Confidence:** "
                f"{risk.get('confidence', '-')}"
            )

            acol4.write(
                f"**Risk Type:** "
                f"{risk.get('riskType', '-')}"
            )

            st.write(
                f"**Business Impact:** "
                f"{risk.get('businessImpact', '-')}"
            )


            # =================================================
            # CURRENT PROJECT CONTEXT
            # =================================================

            st.write(
                "### Current Project Context"
            )

            st.write(
                f"**Evidence:** "
                f"{risk.get('currentProjectEvidence', '-')}"
            )

            st.write(
                f"**Context Reasoning:** "
                f"{risk.get('currentContextReasoning', '-')}"
            )


            # =================================================
            # RISK CHAIN
            # =================================================

            st.write(
                "### Risk Chain Analysis"
            )

            chain = risk.get(
                "riskChain",
                {}
            )

            if not chain:

                # New dashboard JSON may contain
                # risk-chain information through
                # the generated risk_chains structure.
                matching_chain = next(
                    (
                        c for c in
                        data.get(
                            "risk_chains",
                            []
                        )
                        if c.get("riskID")
                        == risk.get("riskID")
                    ),
                    {}
                )

                chain = matching_chain


            chain_col1, chain_col2 = st.columns(2)

            with chain_col1:

                st.write(
                    f"**Root Cause:** "
                    f"{chain.get('rootCause', '-')}"
                )

                st.write(
                    f"**Trigger:** "
                    f"{chain.get('trigger', '-')}"
                )

                st.write(
                    f"**Primary Risk:** "
                    f"{chain.get('primaryRisk', '-')}"
                )

            with chain_col2:

                st.write(
                    f"**Downstream Risk:** "
                    f"{chain.get('downstreamRisk', '-')}"
                )

                st.write(
                    f"**Impact:** "
                    f"{chain.get('impact', '-')}"
                )


            # =================================================
            # HISTORICAL CORRELATION
            # =================================================

            st.write(
                "### Historical Correlation"
            )

            historical = risk.get(
                "historicalCorrelation",
                {}
            )

            st.write(
                f"**Similar Historical Pattern:** "
                f"{historical.get('similarHistoricalPattern', '-')}"
            )

            st.write(
                f"**Support Level:** "
                f"{historical.get('historicalSupportLevel', '-')}"
            )

            st.write(
                f"**Historical Reasoning:** "
                f"{historical.get('historicalReasoning', '-')}"
            )


            # =================================================
            # FORWARD-LOOKING ANALYSIS
            # =================================================

            st.write(
                "### Forward-Looking Analysis"
            )

            st.write(
                f"**Future Risk Projection:** "
                f"{risk.get('futureRiskProjection', '-')}"
            )

            st.write(
                f"**Recurrence Justification:** "
                f"{risk.get('recurrenceJustification', '-')}"
            )

            st.write(
                f"**Leading Indicators:** "
                f"{risk.get('leadingIndicators', '-')}"
            )

            st.write(
                f"**Predictive Insight:** "
                f"{risk.get('predictiveInsight', '-')}"
            )


            # =================================================
            # MITIGATION
            # =================================================

            st.write(
                "### Mitigation"
            )

            mitigation = risk.get(
                "mitigation",
                ""
            )

            st.write(
                mitigation
                if mitigation
                else "-"
            )


            # =================================================
            # RECOMMENDATIONS
            # =================================================

            st.write(
                "### Recommendations"
            )

            recommendations = risk.get(
                "recommendations",
                ""
            )

            recommendation_items = (
                parse_recommendations(
                    recommendations
                )
            )

            if recommendation_items:

                for recommendation in recommendation_items:

                    st.write(
                        f"- {recommendation}"
                    )

            else:

                st.write("-")


st.divider()


# ============================================================
# PROJECT FORECAST INSIGHTS
# ============================================================

st.subheader(
    "Project Forecast Insights"
)

for project in projects:

    project_name = project.get(
        "project_name",
        "Unknown"
    )

    forecast = project.get(
        "risk_forecast_insights",
        {}
    )

    with st.expander(
        f"📌 {project_name}"
    ):

        # ----------------------------------------------------
        # OUTLOOK
        # ----------------------------------------------------

        st.write(
            "### Overall Outlook"
        )

        st.info(
            forecast.get(
                "overallOutlook",
                "-"
            )
        )


        # ----------------------------------------------------
        # BOTTLENECKS
        # ----------------------------------------------------

        bottlenecks = forecast.get(
            "majorBottlenecks",
            []
        )

        if bottlenecks:

            st.write(
                "### Major Bottlenecks"
            )

            for item in bottlenecks:

                st.write(
                    f"- {item}"
                )


        # ----------------------------------------------------
        # RISK PROPAGATION
        # ----------------------------------------------------

        propagation = forecast.get(
            "riskPropagationPatterns",
            []
        )

        if propagation:

            st.write(
                "### Risk Propagation Patterns"
            )

            for item in propagation:

                st.write(
                    f"- {item}"
                )


        # ----------------------------------------------------
        # EMERGING CONCERNS
        # ----------------------------------------------------

        concerns = forecast.get(
            "emergingConcerns",
            []
        )

        if concerns:

            st.write(
                "### Emerging Concerns"
            )

            for item in concerns:

                st.write(
                    f"- {item}"
                )


        # ----------------------------------------------------
        # HIGH-RISK DEPENDENCIES
        # ----------------------------------------------------

        dependencies = forecast.get(
            "highRiskDependencies",
            []
        )

        if dependencies:

            st.write(
                "### High-Risk Dependencies"
            )

            for item in dependencies:

                st.write(
                    f"- {item}"
                )


        # ----------------------------------------------------
        # ROOT CAUSE CONCENTRATION
        # ----------------------------------------------------

        root_causes = forecast.get(
            "rootCauseConcentration",
            []
        )

        if root_causes:

            st.write(
                "### Root Cause Concentration"
            )

            for item in root_causes:

                st.write(
                    f"- {item}"
                )


        # ----------------------------------------------------
        # FAILURE TRIGGERS
        # ----------------------------------------------------

        failure_triggers = forecast.get(
            "mostLikelyFailureTriggers",
            []
        )

        if failure_triggers:

            st.write(
                "### Most Likely Failure Triggers"
            )

            for item in failure_triggers:

                st.write(
                    f"- {item}"
                )


st.divider()


# ============================================================
# PROJECT SUMMARY TABLE
# ============================================================

st.subheader(
    "Summary Statistics by Project"
)

risks_by_project = portfolio_summary.get(
    "risksByProject",
    []
)

if risks_by_project:

    project_stats = pd.DataFrame(
        risks_by_project
    )

    st.dataframe(
        project_stats,
        use_container_width=True,
        hide_index=True
    )

else:

    # Build fallback summary directly from projects

    fallback_project_stats = []

    for project in projects:

        project_name = project.get(
            "project_name",
            "Unknown"
        )

        project_risks = project.get(
            "risks",
            []
        )

        fallback_project_stats.append(
            {
                "projectName": project_name,
                "currentRisksCount": len(
                    project_risks
                )
            }
        )

    if fallback_project_stats:

        st.dataframe(
            pd.DataFrame(
                fallback_project_stats
            ),
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# PROJECT × SEVERITY BREAKDOWN
# ============================================================

st.write(
    "**Risk Breakdown by Project & Severity:**"
)

project_risk_details = []

for project in projects:

    project_name = project.get(
        "project_name",
        "Unknown"
    )

    project_risks = project.get(
        "risks",
        []
    )

    if project_risks:

        severity_breakdown = {
            "Project": project_name,
            "Critical": sum(
                1
                for r in project_risks
                if r.get("severity")
                == "Critical"
            ),
            "High": sum(
                1
                for r in project_risks
                if r.get("severity")
                == "High"
            ),
            "Medium": sum(
                1
                for r in project_risks
                if r.get("severity")
                == "Medium"
            ),
            "Low": sum(
                1
                for r in project_risks
                if r.get("severity")
                == "Low"
            ),
            "Total": len(
                project_risks
            )
        }

        project_risk_details.append(
            severity_breakdown
        )


if project_risk_details:

    detail_df = pd.DataFrame(
        project_risk_details
    )

    st.dataframe(
        detail_df,
        use_container_width=True,
        hide_index=True
    )


st.divider()


# ============================================================
# KEY METRICS
# ============================================================

st.subheader(
    "Key Metrics"
)

metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)


# ------------------------------------------------------------
# HIGH CONFIDENCE RISKS
# ------------------------------------------------------------

high_confidence_count = sum(
    1
    for r in filtered_risks
    if normalize_text(
        r.get("confidence")
    ).lower()
    == "high"
)

with metric_col1:

    st.metric(
        "High Confidence Risks",
        high_confidence_count
    )


# ------------------------------------------------------------
# CRITICAL RISKS
# ------------------------------------------------------------

critical_count = sum(
    1
    for r in filtered_risks
    if r.get("severity")
    == "Critical"
)

with metric_col2:

    st.metric(
        "Critical Risks",
        critical_count,
        delta=(
            "⚠️"
            if critical_count > 0
            else "✓"
        )
    )


# ------------------------------------------------------------
# HIGH SEVERITY RISKS
# ------------------------------------------------------------

high_count = sum(
    1
    for r in filtered_risks
    if r.get("severity")
    == "High"
)

with metric_col3:

    st.metric(
        "High Risks",
        high_count
    )


# ------------------------------------------------------------
# HISTORICALLY STRONG RISKS
# ------------------------------------------------------------

strong_historical_count = sum(
    1
    for r in filtered_risks
    if r.get(
        "historicalCorrelation",
        {}
    ).get(
        "historicalSupportLevel",
        ""
    )
    == "Strong"
)

with metric_col4:

    st.metric(
        "Strong Historical Support",
        strong_historical_count
    )


st.divider()


# ============================================================
# HISTORICAL RISK SUMMARY BY PROJECT
# ============================================================

st.subheader(
    "Historical Risk Intelligence"
)

historical_project_rows = []

for project in projects:

    project_name = project.get(
        "project_name",
        "Unknown"
    )

    historical_summary = project.get(
        "historical_risk_summary",
        {}
    )

    historical_project_rows.append(
        {
            "Project": project_name,
            "Strong": historical_summary.get(
                "strongSupport",
                0
            ),
            "Moderate": historical_summary.get(
                "moderateSupport",
                0
            ),
            "Weak": historical_summary.get(
                "weakSupport",
                0
            ),
            "None": historical_summary.get(
                "noSupport",
                0
            )
        }
    )


if historical_project_rows:

    historical_df = pd.DataFrame(
        historical_project_rows
    )

    st.dataframe(
        historical_df,
        use_container_width=True,
        hide_index=True
    )


st.divider()


# ============================================================
# FOOTER
# ============================================================

st.caption(
    f"Dashboard generated on "
    f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} "
    f"| Data source: GitHub "
    f"{GITHUB_BRANCH} branch"
)
