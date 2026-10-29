
from pathlib import Path
from collections import defaultdict
import pandas as pd

from dependency_map import get_dependencies, get_dependents

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_PATH = BASE_DIR / "data" / "realistic_alerts.csv"
OUTPUT_PATH = BASE_DIR / "data" / "cross_service_correlated_alerts.csv"

# Maximum time gap allowed between alerts in a candidate group.
WINDOW_MINUTES = 10


def related_services(service_a, service_b):
    """Return True if either service depends on the other."""
    try:
        deps_a = set(get_dependencies(service_a))
        deps_b = set(get_dependencies(service_b))
        dependents_a = set(get_dependents(service_a))
        dependents_b = set(get_dependents(service_b))

        return (
            service_b in deps_a
            or service_a in deps_b
            or service_b in dependents_a
            or service_a in dependents_b
        )
    except (KeyError, TypeError):
        return False


def alerts_are_related(row_a, row_b):
    """Check observable time and service-dependency evidence."""
    time_gap = abs(
        (row_a["timestamp"] - row_b["timestamp"]).total_seconds()
    ) / 60

    if time_gap > WINDOW_MINUTES:
        return False

    if row_a["service"] == row_b["service"]:
        return True

    return related_services(row_a["service"], row_b["service"])


def correlate_alerts(df):
    required = {"timestamp", "service", "alert_name", "severity"}
    missing = required - set(df.columns)

    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    data = df.copy()
    data["timestamp"] = pd.to_datetime(
        data["timestamp"], errors="coerce"
    )
    data = data.dropna(
        subset=["timestamp", "service", "alert_name"]
    ).sort_values("timestamp").reset_index(drop=True)

    # Do not use incident_id to form groups.
    # It is retained only for later evaluation.
    data["correlation_group"] = None
    data["correlation_reason"] = None

    # Each alert starts as its own candidate group.
    parent = list(range(len(data)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        root_a, root_b = find(a), find(b)
        if root_a != root_b:
            parent[root_b] = root_a

    # Compare alerts in the time window. Union related alerts.
    for i in range(len(data)):
        row_i = data.iloc[i]

        for j in range(i + 1, len(data)):
            row_j = data.iloc[j]
            gap = (
                row_j["timestamp"] - row_i["timestamp"]
            ).total_seconds() / 60

            if gap > WINDOW_MINUTES:
                break

            if alerts_are_related(row_i, row_j):
                union(i, j)

    # Assign stable-looking group names in chronological order.
    groups = defaultdict(list)
    for index in range(len(data)):
        groups[find(index)].append(index)

    ordered_groups = sorted(
        groups.values(),
        key=lambda indexes: data.loc[indexes, "timestamp"].min()
    )

    for number, indexes in enumerate(ordered_groups, start=1):
        group_id = f"CS-{number:03d}"
        data.loc[indexes, "correlation_group"] = group_id

        services = sorted(data.loc[indexes, "service"].unique())

        if len(indexes) == 1:
            reason = "Single alert; insufficient correlation evidence."
        elif len(services) == 1:
            reason = "Repeated alerts from the same service within the time window."
        else:
            reason = (
                "Alerts occurred within the time window and include "
                "services linked by the configured dependency map."
            )

        data.loc[indexes, "correlation_reason"] = reason

    return data


def evaluate_groups(grouped):
    if "incident_id" not in grouped.columns:
        print("No incident_id column available for evaluation.")
        return

    labelled = grouped[grouped["incident_id"].notna()].copy()

    if labelled.empty:
        print("No labelled alerts available for evaluation.")
        return

    groups_per_incident = (
        labelled.groupby("incident_id")["correlation_group"].nunique()
    )
    incidents_per_group = (
        labelled.groupby("correlation_group")["incident_id"].nunique()
    )

    total_incidents = labelled["incident_id"].nunique()
    intact = int((groups_per_incident == 1).sum())
    mixed = int((incidents_per_group > 1).sum())

    print("\nCROSS-SERVICE CORRELATION EVALUATION")
    print("=" * 42)
    print("Alerts processed:", len(grouped))
    print("Candidate groups:", grouped["correlation_group"].nunique())
    print("Labelled alerts:", len(labelled))
    print("Known incidents:", total_incidents)
    print(f"Incidents kept in one group: {intact}/{total_incidents}")
    print(f"Incident grouping recall: {intact / total_incidents:.1%}")
    print("Groups mixing different known incidents:", mixed)

    print("\nGroups per known incident:")
    print(groups_per_incident.to_string())

    print(
        "\nCaution: labels are used only for evaluation. "
        "This synthetic test does not establish production performance "
        "or prove causation."
    )


if __name__ == "__main__":
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {INPUT_PATH}"
        )

    alerts = pd.read_csv(INPUT_PATH)
    result = correlate_alerts(alerts)
    evaluate_groups(result)

    result.to_csv(OUTPUT_PATH, index=False)
    print(f"\nResults saved to: {OUTPUT_PATH}")