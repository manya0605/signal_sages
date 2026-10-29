
from pathlib import Path
import sys
import json

import pandas as pd
from fastapi import FastAPI, HTTPException

# Resolve the data folder and make existing modules importable.
DATA_DIR = Path(__file__).resolve().parent
PROJECT_DIR = DATA_DIR.parent

if str(DATA_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_DIR))

from cross_service_correlation import correlate_alerts
from root_cause_integration import analyze_candidate_groups
from noise_analyzer import analyze_alert_noise
from tuning_recommender import generate_recommendations


ALERTS_FILE = DATA_DIR / "realistic_alerts.csv"
CORRELATED_FILE = DATA_DIR / "cross_service_correlated_alerts.csv"
ROOT_CAUSE_FILE = DATA_DIR / "root_cause_results.csv"
NOISE_FILE = DATA_DIR / "noise_analysis_results.csv"
TUNING_FILE = DATA_DIR / "tuning_recommendations.csv"

app = FastAPI(
    title="SignalSage AIOps API",
    description=(
        "Cross-service alert correlation, root-cause evidence, "
        "noise analysis, and human-reviewed tuning recommendations."
    ),
    version="1.0.0",
)


def dataframe_records(df):
    """Convert a DataFrame to JSON-safe records."""
    return json.loads(
        df.to_json(orient="records", date_format="iso")
    )


def read_alerts():
    if not ALERTS_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail="realistic_alerts.csv was not found in the data folder.",
        )

    return pd.read_csv(ALERTS_FILE)


@app.get("/")
def home():
    return {
        "project": "SignalSage AIOps",
        "status": "running",
        "docs": "/docs",
        "available_endpoints": [
            "/health",
            "/analyze",
            "/noise",
            "/tuning",
        ],
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "project": "SignalSage AIOps",
        "dataset_exists": ALERTS_FILE.exists(),
    }


@app.get("/analyze")
def analyze():
    """Correlate alerts and rank candidate root causes."""
    try:
        alerts = read_alerts()

        # Step 1: Group alerts without using incident_id.
        correlated = correlate_alerts(alerts)
        correlated.to_csv(CORRELATED_FILE, index=False)

        # Step 2: Use the resulting groups to rank root causes.
        root_causes = analyze_candidate_groups(correlated)
        root_causes.to_csv(ROOT_CAUSE_FILE, index=False)

        return {
            "status": "success",
            "alerts_processed": len(correlated),
            "candidate_groups": int(
                correlated["correlation_group"].nunique()
            ),
            "correlated_alerts": dataframe_records(correlated),
            "root_cause_analysis": dataframe_records(root_causes),
            "notice": (
                "Root-cause scores are heuristic evidence, "
                "not probabilities or proof of causation. "
                "Human review is required."
            ),
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Alert analysis failed: {str(exc)}",
        ) from exc


@app.get("/noise")
def noise():
    """Analyze repeated alert patterns."""
    try:
        if not ALERTS_FILE.exists():
            raise HTTPException(
                status_code=404,
                detail="realistic_alerts.csv was not found.",
            )

        summary = analyze_alert_noise(ALERTS_FILE)

        return {
            "status": "success",
            "patterns_analyzed": len(summary),
            "noise_analysis": dataframe_records(summary),
            "notice": (
                "Repeated or unlabelled alerts are investigation "
                "candidates, not automatically confirmed noise."
            ),
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Noise analysis failed: {str(exc)}",
        ) from exc


@app.get("/tuning")
def tuning():
    """Generate human-reviewed tuning recommendations."""
    try:
        if not ALERTS_FILE.exists():
            raise HTTPException(
                status_code=404,
                detail="realistic_alerts.csv was not found.",
            )

        # Refresh noise results before creating recommendations.
        analyze_alert_noise(ALERTS_FILE)
        recommendations = generate_recommendations()

        return {
            "status": "success",
            "recommendations_count": len(recommendations),
            "automatic_suppression": False,
            "human_approval_required": True,
            "recommendations": dataframe_records(recommendations),
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Tuning recommendation generation failed: {str(exc)}",
        ) from exc