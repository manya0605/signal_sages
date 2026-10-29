
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "data" / "correlated_alerts.csv"


def evaluate_correlation(df):
    # Keep only alerts with known synthetic ground-truth labels.
    known = df[df["incident_id"].notna()].copy()

    if known.empty:
        print("No labelled incidents available for evaluation.")
        return

    # Each ground-truth incident should map to one predicted group.
    groups_per_incident = (
        known.groupby("incident_id")["correlation_group"].nunique()
    )

    # Count predicted groups that contain alerts from multiple
    # ground-truth incidents. This is a simple contamination check.
    incidents_per_group = (
        known.groupby("correlation_group")["incident_id"].nunique()
    )

    total_incidents = known["incident_id"].nunique()
    correctly_grouped = int((groups_per_incident == 1).sum())

    incident_recall = (
        correctly_grouped / total_incidents
        if total_incidents else 0
    )

    mixed_groups = int((incidents_per_group > 1).sum())

    print("SignalSage Correlation Evaluation")
    print("=" * 36)
    print("Labelled alerts:", len(known))
    print("Ground-truth incidents:", total_incidents)
    print("Incidents kept in one predicted group:", correctly_grouped)
    print(f"Incident grouping recall: {incident_recall:.1%}")
    print("Groups mixing different known incidents:", mixed_groups)

    print("\nPer-incident grouping:")
    print(groups_per_incident.to_string())

    print(
        "\nNote: this evaluation only uses labelled demo alerts. "
        "It does not measure detection delay or production performance."
    )


if __name__ == "__main__":
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"{CSV_PATH} not found. Run python data/correlation.py first."
        )

    data = pd.read_csv(CSV_PATH)
    evaluate_correlation(data)