import random
from datetime import datetime, timedelta

import pandas as pd


def create_demo_alerts():
    random.seed(42)

    start_time = datetime(2026, 10, 28, 9, 0)
    alerts = []

    # Incident 1: Database slowdown
    for i in range(10):
        alerts.append({
            "timestamp": start_time + timedelta(minutes=i * 2),
            "service": "postgres-primary",
            "alert_name": "Database connections saturated",
            "severity": "critical",
            "message": "Database connection pool near maximum",
            "incident_id": "INC-001",
        })

    # Incident 2: Cache failure
    for i in range(10):
        alerts.append({
            "timestamp": start_time + timedelta(minutes=30 + i * 2),
            "service": "redis-cache",
            "alert_name": "Cache hit ratio collapsed",
            "severity": "high",
            "message": "Cache performance below expected level",
            "incident_id": "INC-002",
        })

    # Incident 3: Payment provider failure
    for i in range(10):
        alerts.append({
            "timestamp": start_time + timedelta(minutes=60 + i * 2),
            "service": "payment-gateway",
            "alert_name": "Payment provider rate limit",
            "severity": "critical",
            "message": "HTTP 429 responses received",
            "incident_id": "INC-003",
        })

    # Generate unrelated background alerts
    services = [
        "orders-api", "billing-api", "inventory-api",
        "catalog-api", "session-api", "checkout-api",
        "auth-api", "search-api", "email-worker",
    ]

    noise_names = [
        "CPU usage elevated",
        "Memory utilization warning",
        "Pod restarted",
        "Disk usage warning",
    ]

    for i in range(100):
        alerts.append({
            "timestamp": start_time + timedelta(
                minutes=random.randint(0, 120)
            ),
            "service": random.choice(services),
            "alert_name": random.choice(noise_names),
            "severity": random.choice(["low", "medium", "high"]),
            "message": "Background monitoring alert",
            "incident_id": None,
        })

    df = pd.DataFrame(alerts)
    df = df.sort_values("timestamp").reset_index(drop=True)

    return df


if __name__ == "__main__":
    df = create_demo_alerts()

    print("Total alerts:", len(df))
    print("Known incidents:", df["incident_id"].nunique())

    df.to_csv("data/demo_alerts.csv", index=False)

    print("Dataset saved to data/demo_alerts.csv")