
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# Project folders
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CSV_PATH = DATA_DIR / "correlated_alerts.csv"

st.set_page_config(
    page_title="SignalSage AIOps",
    page_icon="🚨",
    layout="wide",
)

st.title("🚨 SignalSage AIOps")
st.subheader("AI-powered Alert Correlation & Incident Intelligence")
st.caption(
    "Turn noisy monitoring alerts into clearer, explainable incident views."
)

# Load alert data
if not CSV_PATH.exists():
    st.error(f"Dataset not found: {CSV_PATH}")
    st.info("Run this command from the project root first:")
    st.code("python data/correlation.py")
    st.stop()

df = pd.read_csv(CSV_PATH)
df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

# Sidebar filters
st.sidebar.header("Filters")

severity_options = sorted(df["severity"].dropna().unique().tolist())
selected_severities = st.sidebar.multiselect(
    "Severity",
    options=severity_options,
    default=severity_options,
)

service_options = sorted(df["service"].dropna().unique().tolist())
selected_services = st.sidebar.multiselect(
    "Services",
    options=service_options,
    default=service_options,
)

filtered = df[
    df["severity"].isin(selected_severities)
    & df["service"].isin(selected_services)
].copy()

# Top-level metrics
total_alerts = len(filtered)
total_groups = filtered["correlation_group"].nunique()
critical_alerts = (
    filtered["severity"].str.lower() == "critical"
).sum()

known_incidents = (
    filtered.loc[
        filtered["incident_id"].notna(),
        "incident_id",
    ].nunique()
)

col1, col2, col3, col4 = st.columns(4)

col1.metric("Alerts", total_alerts)
col2.metric("Candidate Groups", total_groups)
col3.metric("Critical Alerts", int(critical_alerts))
col4.metric("Known Demo Incidents", known_incidents)

st.divider()

# Alert volume chart
left, right = st.columns(2)

with left:
    st.subheader("Alert Severity Distribution")

    severity_counts = (
        filtered["severity"]
        .value_counts()
        .rename_axis("Severity")
        .reset_index(name="Count")
    )

    if not severity_counts.empty:
        fig = px.bar(
            severity_counts,
            x="Severity",
            y="Count",
            color="Severity",
            title="Alerts by severity",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No alerts match the selected filters.")

with right:
    st.subheader("Noisiest Services")

    service_counts = (
        filtered["service"]
        .value_counts()
        .head(10)
        .rename_axis("Service")
        .reset_index(name="Count")
    )

    if not service_counts.empty:
        fig = px.bar(
            service_counts,
            x="Count",
            y="Service",
            orientation="h",
            title="Top 10 services by alert count",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No services match the selected filters.")

st.divider()

# Incident group summaries
st.subheader("🧠 Incident & Correlation Groups")

if not filtered.empty:
    summaries = (
        filtered.groupby("correlation_group", dropna=False)
        .agg(
            alert_count=("alert_name", "size"),
            services=("service", "nunique"),
            highest_severity=("severity", "first"),
            probable_root_cause=("probable_root_cause", "first"),
            explanation=("correlation_reason", "first"),
            first_seen=("timestamp", "min"),
            last_seen=("timestamp", "max"),
        )
        .reset_index()
        .sort_values("alert_count", ascending=False)
    )

    st.dataframe(
        summaries,
        use_container_width=True,
        hide_index=True,
    )

    # Expandable details for each group
    st.subheader("Inspect a Group")

    group_ids = summaries["correlation_group"].astype(str).tolist()
    selected_group = st.selectbox("Choose a group", group_ids)

    details = filtered[
        filtered["correlation_group"].astype(str) == selected_group
    ]

    st.write(f"**Alerts in {selected_group}:** {len(details)}")

    if not details.empty:
        explanation = details["correlation_reason"].dropna()
        root_cause = details["probable_root_cause"].dropna()

        if not root_cause.empty:
            st.write(f"**Probable root cause:** {root_cause.iloc[0]}")

        if not explanation.empty:
            st.write(f"**Why grouped:** {explanation.iloc[0]}")

        st.dataframe(
            details[
                [
                    "timestamp",
                    "service",
                    "alert_name",
                    "severity",
                    "message",
                    "correlation_group",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )
else:
    st.warning("No alerts match your current filters.")

# Download filtered data
st.divider()
st.subheader("Export")

csv_bytes = filtered.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Download filtered alerts as CSV",
    data=csv_bytes,
    file_name="signalsage_filtered_alerts.csv",
    mime="text/csv",
)

st.caption(
    "Prototype using synthetic demo data. Correlation groups are candidates, "
    "not proof of a shared root cause. No live alerts are modified."
)