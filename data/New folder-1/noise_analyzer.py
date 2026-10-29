
"""
SignalSage AIOps - Alert Noise Analyzer

Analyzes repeated alert patterns and identifies candidates
for human-reviewed tuning recommendations.

This module does not automatically suppress alerts.
"""

from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "realistic_alerts.csv"
OUTPUT_FILE = BASE_DIR / "noise_analysis_results.csv"


def analyze_alert_noise(input_file=INPUT_FILE):
    df = pd.read_csv(input_file)

    required_columns = {
        "timestamp",
        "service",
        "alert_name",
        "severity",
        "incident_id",
    }

    missing = required_columns - set(df.columns)

    if missing:
        raise ValueError(
            f"Dataset is missing required columns: {sorted(missing)}"
        )

    df["timestamp"] = pd.to_datetime(
        df["timestamp"], errors="coerce"
    )

    df["incident_id"] = df["incident_id"].fillna("").astype(str)
    df["service"] = df["service"].fillna("unknown").astype(str)
    df["alert_name"] = (
        df["alert_name"].fillna("unknown").astype(str)
    )
    df["severity"] = (
        df["severity"].fillna("unknown").astype(str).str.lower()
    )

    # A repeated pattern is the combination of service and alert name.
    summary = (
        df.groupby(
            ["service", "alert_name", "severity"],
            dropna=False,
        )
        .agg(
            alert_count=("alert_name", "size"),
            first_seen=("timestamp", "min"),
            last_seen=("timestamp", "max"),
            known_incident_alerts=(
                "incident_id",
                lambda values: (values != "").sum(),
            ),
            distinct_known_incidents=(
                "incident_id",
                lambda values: values[values != ""].nunique(),
            ),
        )
        .reset_index()
    )

    # Candidate repetition flag, not a declaration that alerts are useless.
    summary["repeated_pattern"] = summary["alert_count"] > 1

    summary["review_reason"] = summary.apply(
        lambda row: (
            "Repeated pattern: inspect whether grouping or threshold "
            "tuning could reduce duplicate notifications."
            if row["repeated_pattern"]
            else
            "Single observed occurrence: insufficient evidence to "
            "recommend suppression."
        ),
        axis=1,
    )

    # Explicitly distinguish incident-associated evidence from
    # alerts with no incident label in this dataset.
    summary["evidence_category"] = summary.apply(
        lambda row: (
            "Known incident-associated pattern"
            if row["known_incident_alerts"] > 0
            else "Unlabelled in this dataset - requires investigation"
        ),
        axis=1,
    )

    summary = summary.sort_values(
        ["alert_count", "service", "alert_name"],
        ascending=[False, True, True],
    )

    summary.to_csv(OUTPUT_FILE, index=False)

    print("\nSIGNALSAGE ALERT NOISE ANALYSIS")
    print("=" * 42)
    print(f"Total alerts analyzed: {len(df)}")
    print(f"Unique service/alert/severity patterns: {len(summary)}")
    print(
        "Repeated patterns: "
        f"{int(summary['repeated_pattern'].sum())}"
    )
    print(
        "Unlabelled alerts: "
        f"{int((df['incident_id'] == '').sum())}"
    )

    print("\nPattern summary:")
    print(
        summary[
            [
                "service",
                "alert_name",
                "severity",
                "alert_count",
                "known_incident_alerts",
                "evidence_category",
            ]
        ].to_string(index=False)
    )

    print(f"\nSaved results to: {OUTPUT_FILE}")
    print(
        "\nSafety note: repetition and missing incident labels "
        "do not prove an alert is noise. Review before tuning."
    )

    return summary


if __name__ == "__main__":
    analyze_alert_noise()