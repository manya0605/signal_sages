
"""
SignalSage AIOps - Human-Reviewed Tuning Recommender

Creates recommendations from noise analysis results.
It never automatically suppresses or mutes alerts.
"""

from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = BASE_DIR / "noise_analysis_results.csv"
OUTPUT_FILE = BASE_DIR / "tuning_recommendations.csv"


def generate_recommendations():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"{INPUT_FILE} not found. Run noise_analyzer.py first."
        )

    df = pd.read_csv(INPUT_FILE)
    recommendations = []

    for _, row in df.iterrows():
        service = row["service"]
        alert_name = row["alert_name"]
        count = int(row["alert_count"])
        known_incidents = int(row["known_incident_alerts"])
        evidence_category = row["evidence_category"]

        if count > 1 and known_incidents > 0:
            recommendation = (
                "Evaluate grouping repeated alerts into one incident view"
            )
            reason = (
                f"This pattern appeared {count} times and is associated "
                f"with {known_incidents} known-incident alerts. "
                "Preserve all occurrences and investigate whether "
                "they share an underlying incident."
            )
            risk = "Do not suppress automatically"

        elif known_incidents == 0:
            recommendation = (
                "Collect more history and investigate alert relevance"
            )
            reason = (
                "No known incident is associated with this pattern in "
                "the current dataset. Missing labels do not mean the "
                "alert is unnecessary."
            )
            risk = "Insufficient evidence for suppression"

        else:
            recommendation = (
                "Keep monitoring; collect more observations"
            )
            reason = (
                "The pattern is associated with a known incident "
                "and has not repeated in this dataset."
            )
            risk = "Do not suppress automatically"

        recommendations.append({
            "service": service,
            "alert_name": alert_name,
            "observed_count": count,
            "known_incident_alerts": known_incidents,
            "evidence_category": evidence_category,
            "recommendation": recommendation,
            "reason": reason,
            "risk_control": risk,
            "approval_required": True,
        })

    result = pd.DataFrame(recommendations)
    result.to_csv(OUTPUT_FILE, index=False)

    print("\nSIGNALSAGE TUNING RECOMMENDATIONS")
    print("=" * 42)
    print(f"Patterns reviewed: {len(result)}")
    print(
        "Patterns suggested for grouping: "
        f"{int(result['recommendation'].str.startswith('Evaluate grouping').sum())}"
    )
    print(
        "Patterns needing investigation: "
        f"{int(result['recommendation'].str.startswith('Collect more history').sum())}"
    )
    print("Automatic suppression: DISABLED")
    print("Human approval required: YES")
    print(f"\nSaved recommendations to: {OUTPUT_FILE}")

    print("\nRecommendations:")
    print(
        result[
            [
                "service",
                "alert_name",
                "recommendation",
                "risk_control",
            ]
        ].to_string(index=False)
    )

    return result


if __name__ == "__main__":
    generate_recommendations()