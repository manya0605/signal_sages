
import os

import pandas as pd
import requests
import streamlit as st

# ---------------- PAGE CONFIGURATION ----------------
st.set_page_config(
    page_title="SignalSage AIOps",
    page_icon="⚡",
    layout="wide",
)

API_BASE_URL = os.getenv(
    "SIGNALSAGE_API_URL",
    "http://127.0.0.1:8000",
)

# ---------------- DARK ENTERPRISE THEME ----------------
st.markdown(
    """
    <style>
    .stApp {
        background-color: #0B1120;
        color: #E2E8F0;
    }
    [data-testid="stHeader"] {
        background-color: #0B1120;
    }
    [data-testid="stSidebar"] {
        background-color: #111827;
    }
    .block-container {
        padding-top: 1.5rem;
        max-width: 1500px;
    }
    h1, h2, h3 {
        color: #F1F5F9 !important;
    }
    p, label {
        color: #CBD5E1;
    }
    [data-testid="stMetric"] {
        background-color: #151F32;
        border: 1px solid #29374D;
        padding: 16px;
        border-radius: 12px;
    }
    [data-testid="stMetricValue"] {
        color: #55D6BE !important;
    }
    div.stButton > button {
        background-color: #0F766E;
        color: white;
        border-radius: 8px;
        min-height: 40px;
        font-weight: 600;
    }
    hr {
        border-color: #29374D;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------- API HELPER ----------------
def fetch_endpoint(endpoint):
    """Fetch data from the local FastAPI backend."""
    try:
        response = requests.get(
            f"{API_BASE_URL}{endpoint}",
            timeout=30,
        )
        response.raise_for_status()
        return response.json(), None
    except requests.RequestException as exc:
        return None, str(exc)
    except ValueError:
        return None, "The API returned an invalid JSON response."


# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.title("⚡ SignalSage")
    st.caption("AI Operations Intelligence")
    st.markdown("---")

    page = st.radio(
        "Navigation",
        [
            "System Overview",
            "Incident Correlation",
            "Root Cause Analysis",
            "Noise Analysis",
            "Tuning Recommendations",
        ],
    )

    st.markdown("---")
    st.caption("Backend API")
    st.code(API_BASE_URL, language=None)
    st.caption("Recommendations require human review.")


# ---------------- HEADER ----------------
st.title("⚡ SIGNALSAGE AIOPS")
st.caption(
    "Cross-service incident intelligence | "
    "Alert correlation | Root-cause evidence | "
    "Human-reviewed tuning"
)
st.markdown("---")


# ---------------- LOAD DATA ----------------
# Cache only for this Streamlit session and clear it when
# the user requests a refresh.
if "analysis_data" not in st.session_state:
    st.session_state.analysis_data = None

if "noise_data" not in st.session_state:
    st.session_state.noise_data = None

if "tuning_data" not in st.session_state:
    st.session_state.tuning_data = None

if st.button("↻ Refresh Analysis"):
    st.session_state.analysis_data = None
    st.session_state.noise_data = None
    st.session_state.tuning_data = None

# Load analysis only when required.
if (
    page in ["System Overview", "Incident Correlation",
             "Root Cause Analysis"]
    and st.session_state.analysis_data is None
):
    with st.spinner("Analyzing alerts..."):
        data, error = fetch_endpoint("/analyze")
        if error:
            st.error(
                "Could not reach the API. Make sure FastAPI is "
                "running in another terminal.\n\n" + error
            )
        else:
            st.session_state.analysis_data = data

if page == "Noise Analysis" and st.session_state.noise_data is None:
    with st.spinner("Analyzing alert patterns..."):
        data, error = fetch_endpoint("/noise")
        if error:
            st.error("Noise analysis failed: " + error)
        else:
            st.session_state.noise_data = data

if (
    page == "Tuning Recommendations"
    and st.session_state.tuning_data is None
):
    with st.spinner("Generating recommendations..."):
        data, error = fetch_endpoint("/tuning")
        if error:
            st.error("Tuning analysis failed: " + error)
        else:
            st.session_state.tuning_data = data


# ---------------- SYSTEM OVERVIEW ----------------
if page == "System Overview":
    data = st.session_state.analysis_data

    if data:
        alerts = data.get("correlated_alerts", [])
        roots = data.get("root_cause_analysis", [])
        alert_df = pd.DataFrame(alerts)
        root_df = pd.DataFrame(roots)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("ALERTS PROCESSED", data.get("alerts_processed", 0))
        col2.metric("CANDIDATE GROUPS", data.get("candidate_groups", 0))

        critical_count = 0
        if not alert_df.empty and "severity" in alert_df.columns:
            critical_count = int(
                alert_df["severity"].astype(str).str.lower()
                .eq("critical").sum()
            )

        col3.metric("CRITICAL ALERTS", critical_count)
        col4.metric("ROOT-CAUSE CANDIDATES", len(root_df))

        st.markdown("---")
        st.subheader("Incident Group Summary")

        if not alert_df.empty and "correlation_group" in alert_df.columns:
            group_summary = (
                alert_df.groupby("correlation_group")
                .agg(
                    Alert_Count=("correlation_group", "size"),
                    Services=("service", "nunique"),
                )
                .reset_index()
                .sort_values("Alert_Count", ascending=False)
            )
            st.dataframe(
                group_summary,
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No correlation-group data is available.")

        st.info(
            "These results use the project's synthetic test dataset. "
            "Candidate groups and root-cause scores need validation "
            "against real operational incidents."
        )


# ---------------- INCIDENT CORRELATION ----------------
elif page == "Incident Correlation":
    data = st.session_state.analysis_data

    if data:
        st.subheader("Cross-Service Alert Groups")
        alert_df = pd.DataFrame(data.get("correlated_alerts", []))

        if not alert_df.empty:
            if "correlation_group" in alert_df.columns:
                groups = sorted(
                    alert_df["correlation_group"].dropna().unique()
                )
                selected = st.selectbox("Select a group", groups)
                selected_df = alert_df[
                    alert_df["correlation_group"] == selected
                ]
                st.write(f"**Selected group:** {selected}")
                st.dataframe(
                    selected_df,
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.dataframe(
                    alert_df,
                    use_container_width=True,
                    hide_index=True,
                )
        else:
            st.info("No alerts were returned.")


# ---------------- ROOT CAUSE ANALYSIS ----------------
elif page == "Root Cause Analysis":
    data = st.session_state.analysis_data

    if data:
        st.subheader("Probable Root Causes")
        roots = data.get("root_cause_analysis", [])
        root_df = pd.DataFrame(roots)

        if not root_df.empty:
            st.dataframe(
                root_df,
                use_container_width=True,
                hide_index=True,
            )
            st.warning(
                "Scores are heuristic evidence, not probabilities "
                "or proof of causation. Verify candidates manually."
            )
        else:
            st.info("No root-cause candidates were returned.")


# ---------------- NOISE ANALYSIS ----------------
elif page == "Noise Analysis":
    data = st.session_state.noise_data

    if data:
        st.subheader("Alert Pattern Analysis")
        st.metric(
            "Patterns Analyzed",
            data.get("patterns_analyzed", 0),
        )

        noise_df = pd.DataFrame(data.get("noise_analysis", []))
        if not noise_df.empty:
            st.dataframe(
                noise_df,
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No alert-pattern results were returned.")

        st.warning(
            "Repeated or unlabelled patterns are investigation "
            "candidates, not confirmed noise."
        )


# ---------------- TUNING RECOMMENDATIONS ----------------
elif page == "Tuning Recommendations":
    data = st.session_state.tuning_data

    if data:
        st.subheader("Human-Reviewed Tuning Recommendations")

        col1, col2 = st.columns(2)
        col1.metric(
            "Recommendations",
            data.get("recommendations_count", 0),
        )
        col2.metric(
            "Automatic Suppression",
            "Disabled" if not data.get(
                "automatic_suppression", True
            ) else "Enabled",
        )

        st.success(
            "Human approval required: "
            + str(data.get("human_approval_required", True))
        )

        rec_df = pd.DataFrame(data.get("recommendations", []))
        if not rec_df.empty:
            st.dataframe(
                rec_df,
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No recommendations were returned.")

        st.warning(
            "This dashboard displays recommendations only. "
            "It does not apply tuning changes or suppress alerts."
        )


# ---------------- FOOTER ----------------
st.markdown("---")
st.caption(
    "SignalSage AIOps | Synthetic-data demonstration | "
    "Human oversight required for operational decisions"
)