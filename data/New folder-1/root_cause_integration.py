
from pathlib import Path
import json
import pandas as pd

from root_cause import rank_root_causes

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_PATH = (
    BASE_DIR / "data" / "cross_service_correlated_alerts.csv"
)
OUTPUT_PATH = (
    BASE_DIR / "data" / "root_cause_results.csv"
)


def analyze_candidate_groups(alerts):
    required = {"correlation_group", "service"}
    missing = required - set(alerts.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    results = []

    for group_id, group in alerts.groupby(
        "correlation_group", dropna=False, sort=False
    ):
        services = sorted(
            group["service"].dropna().astype(str).unique()
        )

        ranked = rank_root_causes(group)
        top = ranked[0] if ranked else None

        if len(group) == 1:
            status = "LOW EVIDENCE - SINGLE ALERT"
        elif top and top["score"] >= 0.75:
            status = "STRONGER DEPENDENCY SUPPORT"
        elif top:
            status = "POSSIBLE ROOT CAUSE - REVIEW"
        else:
            status = "NO CANDIDATE FOUND"

        results.append({
            "correlation_group": group_id,
            "alert_count": len(group),
            "affected_services": ", ".join(services),
            "probable_root_cause": (
                top["probable_root_cause"] if top else "Unknown"
            ),
            "evidence_score": top["score"] if top else 0.0,
            "review_status": status,
            "explanation": (
                top["explanation"]
                if top
                else "No matching candidate found in the dependency map."
            ),
            "ranked_candidates_json": json.dumps(ranked),
        })

    return pd.DataFrame(results)


if __name__ == "__main__":
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Correlation results not found: {INPUT_PATH}\n"
            "Run python data/cross_service_correlation.py first."
        )

    correlated_alerts = pd.read_csv(INPUT_PATH)
    results = analyze_candidate_groups(correlated_alerts)

    results.to_csv(OUTPUT_PATH, index=False)

    print("\nSIGNALSAGE ROOT-CAUSE ANALYSIS")
    print("=" * 42)
    print("Candidate groups analyzed:", len(results))
    print("Results saved to:", OUTPUT_PATH)

    for _, row in results.iterrows():
        print(f"\nGroup: {row['correlation_group']}")
        print("Alerts:", row["alert_count"])
        print("Services:", row["affected_services"])
        print("Possible cause:", row["probable_root_cause"])
        print("Evidence score:", row["evidence_score"])
        print("Review status:", row["review_status"])
        print("Explanation:", row["explanation"])

    print(
        "\nReminder: evidence scores are heuristic dependency coverage, "
        "not probabilities or proof of causation. Human review is required."
    )