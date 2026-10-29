import random
from datetime import datetime, timedelta

import pandas as pd


def generate_test_alerts():
    """Generate 397 routine alerts and 3 critical test alerts."""
    alerts = []
    now = datetime.now()

    # Generate 397 routine alerts.
    for i in range(397):
        alerts.append({
            "alert_id": f"ALT-{i + 1:03d}",
            "time": now - timedelta(seconds=i),
            "type": random.choice([
                "CPU Warning",
                "Memory Warning",
                "Latency Warning",
                "Service Check",
            ]),
            "metric": "General",
            "value": random.randint(10, 75),
            "threshold": 85,
            "severity": "Warning",
            "incident_id": "None",
        })

    # Add 3 deliberately designed critical test alerts.
    incidents = [
        {
            "alert_id": "ALT-398",
            "type": "CPU Overload",
            "metric": "CPU",
            "value": 96,
            "threshold": 85,
            "incident_id": "INC-001",
        },
        {
            "alert_id": "ALT-399",
            "type": "Memory Critical",
            "metric": "Memory",
            "value": 97,
            "threshold": 90,
            "incident_id": "INC-002",
        },
        {
            "alert_id": "ALT-400",
            "type": "High Latency",
            "metric": "Latency",
            "value": 950,
            "threshold": 500,
            "incident_id": "INC-003",
        },
    ]

    for incident in incidents:
        incident.update({
            "time": now,
            "severity": "Critical",
        })
        alerts.append(incident)

    random.shuffle(alerts)
    return pd.DataFrame(alerts)


def analyze_alerts(alerts):
    """Flag CPU, memory, and latency threshold violations."""
    results = alerts.copy()

    results["detected_incident"] = (
        results["metric"].isin(["CPU", "Memory", "Latency"])
        & (results["value"] > results["threshold"])
    )

    results["priority"] = results["detected_incident"].map({
        True: "Critical",
        False: "Routine",
    })

    return results.sort_values(
        by="detected_incident",
        ascending=False,
    )