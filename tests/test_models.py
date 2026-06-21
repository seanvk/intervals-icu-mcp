"""Tests for Pydantic model field aliases.

Regression: the Intervals.icu Activity schema returns power as
``icu_average_watts`` / ``icu_weighted_avg_watts``. Without aliases these
fields stayed ``None``, silently dropping all power data.
"""

from intervals_icu_mcp.models import Activity, ActivitySummary

_BASE = {"id": "1", "start_date_local": "2025-10-14T07:00:00"}


class TestActivityWattsAliases:
    def test_summary_reads_icu_average_watts(self):
        a = ActivitySummary.model_validate({**_BASE, "icu_average_watts": 210})
        assert a.average_watts == 210

    def test_activity_reads_weighted_avg_watts(self):
        a = Activity.model_validate(
            {**_BASE, "icu_average_watts": 210, "icu_weighted_avg_watts": 225}
        )
        assert a.average_watts == 210
        assert a.weighted_average_watts == 225

    def test_field_name_still_accepted(self):
        # populate_by_name keeps the plain field name working (used by fixtures).
        a = ActivitySummary.model_validate({**_BASE, "average_watts": 200})
        assert a.average_watts == 200
