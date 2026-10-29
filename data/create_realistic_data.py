
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_PATH = BASE_DIR / "data" / "realistic_alerts.csv"

rows = []


def add_alert(timestamp, service, alert_name, severity, message, incident_id=None):
    rows.append({
        "timestamp": timestamp,
        "service": service,
        "alert_name": alert_name,
        "severity": severity,
        "message": message,
        "incident_id": incident_id,
    })


# Incident 1: database slowdown affecting multiple services.
database_incident = [
    ("2026-10-28 09:00:00", "postgres-primary",
     "Database connections saturated", "critical"),
    ("2026-10-28 09:02:00", "orders-api",
     "Request latency high", "high"),
    ("2026-10-28 09:03:00", "billing-api",
     "Database query timeout", "critical"),
    ("2026-10-28 09:04:00", "inventory-api",
     "Database query latency high", "high"),
    ("2026-10-28 09:06:00", "orders-api",
     "Request latency high", "high"),
    ("2026-10-28 09:08:00", "postgres-primary",
     "Database connections saturated", "critical"),
]

for timestamp, service, alert_name, severity in database_incident:
    add_alert(
        timestamp, service, alert_name, severity,
        "Synthetic database slowdown scenario", "INC-001"
    )


# Incident 2: Redis/cache problem affecting multiple services.
cache_incident = [
    ("2026-10-28 09:30:00", "redis-cache",
     "Cache hit ratio collapsed", "high"),
    ("2026-10-28 09:32:00", "session-api",
     "Session lookup latency high", "high"),
    ("2026-10-28 09:34:00", "auth-api",
     "Authentication latency high", "high"),
    ("2026-10-28 09:36:00", "checkout-api",
     "Cache request timeout", "critical"),
    ("2026-10-28 09:38:00", "redis-cache",
     "Cache hit ratio collapsed", "high"),
]

for timestamp, service, alert_name, severity in cache_incident:
    add_alert(
        timestamp, service, alert_name, severity,
        "Synthetic cache degradation scenario", "INC-002"
    )


# Incident 3: payment provider rate limiting.
payment_incident = [
    ("2026-10-28 10:00:00", "payment-gateway",
     "Payment provider rate limit", "critical"),
    ("2026-10-28 10:02:00", "billing-api",
     "Payment request failed", "critical"),
    ("2026-10-28 10:04:00", "checkout-api",
     "Checkout payment timeout", "critical"),
    ("2026-10-28 10:06:00", "payment-gateway",
     "Payment provider rate limit", "critical"),
    ("2026-10-28 10:08:00", "orders-api",
     "Payment confirmation delayed", "high"),
]

for timestamp, service, alert_name, severity in payment_incident:
    add_alert(
        timestamp, service, alert_name, severity,
        "Synthetic payment provider incident", "INC-003"
    )


# Add unrelated background alerts.
noise_alerts = [
    ("2026-10-28 11:00:00", "search-api",
     "CPU usage high", "medium"),
    ("2026-10-28 11:03:00", "email-worker",
     "Memory usage high", "medium"),
    ("2026-10-28 11:06:00", "catalog-api",
     "Pod restarted", "low"),
    ("2026-10-28 11:09:00", "inventory-api",
     "Disk usage high", "medium"),
    ("2026-10-28 11:12:00", "auth-api",
     "CPU usage high", "medium"),
]

for timestamp, service, alert_name, severity in noise_alerts:
    add_alert(
        timestamp, service, alert_name, severity,
        "Synthetic background alert", None
    )


df = pd.DataFrame(rows)
df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.sort_values("timestamp").reset_index(drop=True)
df.to_csv(OUTPUT_PATH, index=False)

print("Realistic synthetic dataset created successfully.")
print("Total alerts:", len(df))
print("Known incidents:", df["incident_id"].nunique())
print("Labelled alerts:", df["incident_id"].notna().sum())
print("Services involved:", df["service"].nunique())
print("Saved to:", OUTPUT_PATH)