
"""
SignalSage AIOps - Root Cause Ranking

Uses service dependencies, direct alert evidence, and symptom
keywords to rank possible root causes.

This is an explainable heuristic, not a trained ML model
or proof of causation.
"""

from dependency_map import (
    SERVICE_DEPENDENCIES,
    get_upstream_dependencies,
)


SYMPTOM_KEYWORDS = {
    "postgres-primary": [
        "database",
        "postgres",
        "sql query",
        "query latency",
        "query timeout",
        "connections saturated",
        "database slowdown",
    ],
    "redis-cache": [
        "redis",
        "cache",
        "cache hit ratio",
        "session lookup",
    ],
    "payment-gateway": [
        "payment",
        "provider rate limit",
        "payment request",
        "payment timeout",
        "payment confirmation",
        "transaction",
    ],
}


def rank_root_causes(alert_group):
    """Return candidate root causes ranked by supporting evidence."""

    if alert_group.empty:
        return []

    affected_services = set(
        alert_group["service"].dropna().astype(str)
    )

    if not affected_services:
        return []

    # Combine alert names and messages for symptom matching.
    text_columns = [
        column
        for column in ["alert_name", "message"]
        if column in alert_group.columns
    ]

    alert_text = " ".join(
        str(value)
        for column in text_columns
        for value in alert_group[column].dropna().tolist()
    ).lower()

    results = []

    for candidate in SERVICE_DEPENDENCIES:
        upstream_services = set(
            get_upstream_dependencies(candidate)
        )

        # Affected services that report the candidate directly
        # or depend on it according to the configured demo map.
        supporting_services = sorted(
            service
            for service in affected_services
            if service == candidate
            or candidate in get_upstream_dependencies(service)
        )

        dependency_coverage = (
            len(supporting_services) / len(affected_services)
        )

        direct_alert = candidate in affected_services

        keywords = SYMPTOM_KEYWORDS.get(candidate, [])
        matched_keywords = [
            keyword for keyword in keywords
            if keyword in alert_text
        ]
        symptom_match = bool(matched_keywords)

        # Transparent weighted score:
        # dependency coverage: 45%
        # direct alert evidence: 30%
        # symptom keyword match: 25%
        score = (
            0.45 * dependency_coverage
            + 0.30 * float(direct_alert)
            + 0.25 * float(symptom_match)
        )

        if score <= 0:
            continue

        evidence = []

        if supporting_services:
            evidence.append(
                f"{len(supporting_services)} of "
                f"{len(affected_services)} affected services "
                "report or depend on this candidate"
            )

        if direct_alert:
            evidence.append("the candidate has a direct alert")

        if matched_keywords:
            evidence.append(
                "matching symptoms: "
                + ", ".join(matched_keywords)
            )

        results.append({
            "probable_root_cause": candidate,
            "score": round(score, 4),
            "dependency_coverage": round(
                dependency_coverage, 4
            ),
            "direct_alert_evidence": direct_alert,
            "matched_keywords": matched_keywords,
            "supporting_services": supporting_services,
            "explanation": "; ".join(evidence),
        })

    results.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return results


if __name__ == "__main__":
    import pandas as pd

    demo_group = pd.DataFrame([
        {
            "service": "payment-gateway",
            "alert_name": "Payment provider rate limit",
            "message": "Payment requests are being rate limited",
        },
        {
            "service": "billing-api",
            "alert_name": "Payment timeout",
            "message": "Payment request timed out",
        },
        {
            "service": "checkout-api",
            "alert_name": "Payment confirmation delayed",
            "message": "Payment confirmation is delayed",
        },
        {
            "service": "orders-api",
            "alert_name": "Payment request failed",
            "message": "Transaction failed",
        },
    ])

    for result in rank_root_causes(demo_group)[:5]:
        print(
            f"{result['probable_root_cause']}: "
            f"score={result['score']:.4f}"
        )
        print(f"  Evidence: {result['explanation']}")