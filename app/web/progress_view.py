"""Web rendering helpers for progress summary pages."""

from __future__ import annotations

from app.domain.models import ProgressReport


def trend_label_el(trend: str) -> str:
    labels = {
        "improving": "Βελτίωση",
        "stable": "Σταθερή πορεία",
        "declining": "Πτώση",
        "insufficient_data": "Ανεπαρκή δεδομένα",
    }
    return labels.get(trend, trend)


def report_context(report: ProgressReport) -> dict[str, object]:
    """Build a template context from a progress report payload."""
    return {
        "report": report,
        "overall_trend_label": trend_label_el(report.overall_trend),
        "narrative_warning": report.narrative_status == "degraded",
        "is_empty": report.worksheet_count == 0,
        "skill_rows": [
            {
                "micro_skill_id": row.micro_skill_id,
                "worksheet_count": row.worksheet_count,
                "avg_accuracy_pct": row.avg_accuracy_pct,
                "last_accuracy_pct": row.last_accuracy_pct,
                "trend": trend_label_el(row.trend),
            }
            for row in report.skill_progress
        ],
    }

