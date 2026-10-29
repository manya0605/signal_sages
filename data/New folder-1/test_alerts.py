from alert_analyzer import generate_test_alerts, analyze_alerts


def main():
    alerts = generate_test_alerts()
    results = analyze_alerts(alerts)

    detected = results[results["detected_incident"]]

    print("===== SIGNALSAGE ALERT ANALYZER TEST =====")
    print("Total alerts:", len(alerts))
    print("Detected incidents:", len(detected))

    print("\nDetected incident details:")
    print(
        detected[
            ["alert_id", "type", "value", "threshold", "priority"]
        ].to_string(index=False)
    )

    # Verify the expected test results.
    assert len(alerts) == 400, "Expected exactly 400 alerts."
    assert len(detected) == 3, "Expected exactly 3 detected alerts."
    assert detected["incident_id"].nunique() == 3, (
        "Expected 3 distinct incident IDs."
    )

    print("\nTEST PASSED: 400 alerts, 3 incidents detected.")


if __name__ == "__main__":
    main()