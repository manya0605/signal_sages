
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "data" / "realistic_alerts.csv"
OUTPUT_PATH = BASE_DIR / "data" / "blind_correlated_alerts.csv"

WINDOW_MINUTES = 10


def group_alerts_without_labels(df):
    required = {"timestamp", "service", "alert_name"}
    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    data = df.copy()
    data["timestamp"] = pd.to_datetime(
        data["timestamp"], errors="coerce"
    )
    data = data.dropna(
        subset=["timestamp", "service", "alert_name"]
    ).copy()
    data = data.sort_values("timestamp").reset_index(drop=True)
    data["correlation_group"] = None

    next_group_number = 1

    # Grouping uses observable fields only.
    # incident_id is NOT used here.
    for _, group in data.groupby(
        ["service", "alert_name"], sort=False
    ):
        group = group.sort_values("timestamp")
        current_group = []
        previous_time = None

        for index, row in group.iterrows():
            current_time = row["timestamp"]

            if (
                previous_time is None
                or (current_time - previous_time).total_seconds()
                <= WINDOW_MINUTES * 60
            ):
                current_group.append(index)
            else:
                group_id = f"BLIND-{next_group_number:03d}"
                data.loc[current_group, "correlation_group"] = group_id
                next_group_number += 1
                current_group = [index]

            previous_time = current_time

        if current_group:
            group_id = f"BLIND-{next_group_number:03d}"
            data.loc[current_group, "correlation_group"] = group_id
            next_group_number += 1

    return data


def evaluate_groups(grouped):
    print("\nSIGNALSAGE BLIND EVALUATION")
    print("=" * 42)

    print("Alerts processed:", len(grouped))
    print(
        "Predicted groups:",
        grouped["correlation_group"].nunique()
    )

    if "incident_id" not in grouped.columns:
        print("No incident_id column; evaluation unavailable.")
        return

    # Ground-truth labels are used only AFTER grouping.
    labelled = grouped[
        grouped["incident_id"].notna()
    ].copy()

    unlabelled_count = int(
        grouped["incident_id"].isna().sum()
    )

    print("Labelled alerts:", len(labelled))
    print("Unlabelled alerts:", unlabelled_count)

    if labelled.empty:
        print("No labelled alerts available for evaluation.")
        return

    # Each labelled alert pair has a known incident relationship.
    true_positive_pairs = 0
    predicted_positive_pairs = 0
    actual_positive_pairs = 0

    records = labelled[
        ["incident_id", "correlation_group"]
    ].to_dict("records")

    for i in range(len(records)):
        for j in range(i + 1, len(records)):
            same_incident = (
                records[i]["incident_id"]
                == records[j]["incident_id"]
            )
            same_group = (
                records[i]["correlation_group"]
                == records[j]["correlation_group"]
            )

            if same_group:
                predicted_positive_pairs += 1

            if same_incident:
                actual_positive_pairs += 1

            if same_incident and same_group:
                true_positive_pairs += 1

    false_positive_pairs = (
        predicted_positive_pairs - true_positive_pairs
    )
    false_negative_pairs = (
        actual_positive_pairs - true_positive_pairs
    )

    precision = (
        true_positive_pairs / predicted_positive_pairs
        if predicted_positive_pairs else 0.0
    )
    recall = (
        true_positive_pairs / actual_positive_pairs
        if actual_positive_pairs else 0.0
    )

    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall else 0.0
    )

    # Incident-level recall: incident alerts all in one group.
    groups_per_incident = (
        labelled.groupby("incident_id")["correlation_group"]
        .nunique()
    )
    total_incidents = len(groups_per_incident)
    intact_incidents = int(
        (groups_per_incident == 1).sum()
    )
    incident_recall = (
        intact_incidents / total_incidents
        if total_incidents else 0.0
    )

    # Purity: for each predicted group, count the
    # largest single-incident label group.
    group_label_counts = labelled.groupby(
        ["correlation_group", "incident_id"]
    ).size()

    largest_counts = group_label_counts.groupby(
        level=0
    ).max()

    purity = (
        largest_counts.sum() / len(labelled)
        if len(labelled) else 0.0
    )

    # A mixed group contains alerts from multiple known incidents.
    incidents_per_group = (
        labelled.groupby("correlation_group")["incident_id"]
        .nunique()
    )

    mixed_groups = int((incidents_per_group > 1).sum())
    labelled_groups = len(incidents_per_group)

    false_mixing_rate = (
        mixed_groups / labelled_groups
        if labelled_groups else 0.0
    )

    print("\nPAIRWISE METRICS")
    print("-" * 30)
    print(f"Pairwise precision: {precision:.1%}")
    print(f"Pairwise recall:    {recall:.1%}")
    print(f"Pairwise F1 score:  {f1:.1%}")
    print("Correctly grouped same-incident pairs:", true_positive_pairs)
    print("Incorrectly grouped different-incident pairs:", false_positive_pairs)
    print("Missed same-incident pairs:", false_negative_pairs)

    print("\nINCIDENT-LEVEL METRICS")
    print("-" * 30)
    print(
        f"Incidents kept in one group: "
        f"{intact_incidents}/{total_incidents}"
    )
    print(f"Incident grouping recall: {incident_recall:.1%}")
    print(f"Group purity: {purity:.1%}")
    print(f"Groups mixing different incidents: {mixed_groups}")
    print(f"False-mixing rate: {false_mixing_rate:.1%}")

    print("\nPER-INCIDENT GROUP COUNTS")
    print(groups_per_incident.to_string())

    print("\nIMPORTANT LIMITATIONS")
    print("-" * 30)
    print(
        "This is a simple service-and-alert-name baseline, "
        "not a trained AI model."
    )
    print(
        "Unlabelled alerts are excluded from labelled-incident "
        "pairwise metrics."
    )
    print(
        "Synthetic results do not establish production accuracy "
        "or prove root cause."
    )


if __name__ == "__main__":
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"{CSV_PATH} not found. Generate the dataset first."
        )

    alerts = pd.read_csv(CSV_PATH)
    result = group_alerts_without_labels(alerts)
    evaluate_groups(result)

    result.to_csv(OUTPUT_PATH, index=False)
    print(f"\nBlind grouping results saved to: {OUTPUT_PATH}")