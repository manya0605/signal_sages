import pandas as pd


def correlate_alerts(df):
    """
    Group alerts into incident-level views.

    Known incident IDs are used here to validate our synthetic
    demo dataset. Unlabelled alerts are grouped by service,
    alert type, and time proximity.

    Do not use ground-truth IDs as input in a real live system.
    """

    alerts = df.copy()
    alerts["timestamp"] = pd.to_datetime(alerts["timestamp"])
    alerts = alerts.sort_values("timestamp").reset_index(drop=True)

    alerts["correlation_group"] = None
    alerts["correlation_reason"] = None
    alerts["probable_root_cause"] = None
    alerts["confidence"] = 0.0

    # Demo validation: known labels identify the same incident
    known_mask = alerts["incident_id"].notna()

    for incident_id, group in alerts[known_mask].groupby("incident_id"):
        group_id = f"INCIDENT-{incident_id}"

        alerts.loc[group.index, "correlation_group"] = group_id

        services = sorted(group["service"].unique())
        alert_types = sorted(group["alert_name"].unique())

        alerts.loc[group.index, "correlation_reason"] = (
            f"Shared demo incident label {incident_id}; "
            f"{len(services)} service(s), "
            f"{len(alert_types)} alert type(s)"
        )

        # Select a probable cause using the incident's dominant service.
        root_service = group["service"].mode().iloc[0]
        alerts.loc[group.index, "probable_root_cause"] = root_service
        alerts.loc[group.index, "confidence"] = 1.0

    # Baseline grouping for alerts without known incident labels
    noise = alerts[~known_mask]

    next_group_number = 1

    for (service, alert_name), group in noise.groupby(
        ["service", "alert_name"], sort=False
    ):
        current_group = []
        previous_time = None

        for index in group.index:
            current_time = alerts.loc[index, "timestamp"]

            if (
                previous_time is not None
                and (current_time - previous_time).total_seconds() > 600
            ):
                group_id = f"NOISE-{next_group_number:03d}"
                alerts.loc[current_group, "correlation_group"] = group_id
                alerts.loc[current_group, "correlation_reason"] = (
                    f"Same service ({service}) and alert type "
                    f"({alert_name}) within 10 minutes; "
                    "no known incident label"
                )
                alerts.loc[current_group, "probable_root_cause"] = service
                alerts.loc[current_group, "confidence"] = 0.5

                next_group_number += 1
                current_group = []

            current_group.append(index)
            previous_time = current_time

        if current_group:
            group_id = f"NOISE-{next_group_number:03d}"
            alerts.loc[current_group, "correlation_group"] = group_id
            alerts.loc[current_group, "correlation_reason"] = (
                f"Same service ({service}) and alert type "
                f"({alert_name}) within 10 minutes; "
                "no known incident label"
            )
            alerts.loc[current_group, "probable_root_cause"] = service
            alerts.loc[current_group, "confidence"] = 0.5

            next_group_number += 1

    return alerts


if __name__ == "__main__":
    from data_engine import create_demo_alerts

    df = create_demo_alerts()
    result = correlate_alerts(df)

    print("Total alerts:", len(result))
    print(
        "Incident-level groups:",
        result["correlation_group"].nunique(),
    )

    print("\nKnown incident summaries:")
    known = result[result["incident_id"].notna()]

    print(
        known.groupby("correlation_group").agg(
            alerts=("alert_name", "size"),
            services=("service", "nunique"),
            root_cause=("probable_root_cause", "first"),
        ).to_string()
    )

    result.to_csv("data/correlated_alerts.csv", index=False)
    print("\nSaved to data/correlated_alerts.csv")