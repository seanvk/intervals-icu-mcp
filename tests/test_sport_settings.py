"""Tests for sport-settings reading.

Regression: the SportSettings model used wrong field names (type/fthr/
pace_threshold) so get_sport_settings dropped threshold HR, max HR, pace and
all zones — only FTP survived. The model now matches the API (types/lthr/
max_hr/threshold_pace + zone arrays).
"""

import json
from unittest.mock import MagicMock, patch

from httpx import Response

from intervals_icu_mcp.tools import sport_settings as ss

# Real shape of a Run sport-settings entry (trimmed) from the Intervals API.
RUN_SETTINGS = {
    "id": 796623,
    "types": ["Run", "VirtualRun", "TrailRun"],
    "ftp": 221,
    "lthr": 168,
    "max_hr": 200,
    "threshold_pace": 2.5,  # meters/second == 6:40 /km
    "pace_units": "MINS_KM",
    "hr_zones": [136, 151, 159, 167, 171, 177, 200],
    "hr_zone_names": ["Z1", "Z2", "Zone X", "Z3", "Zone Y", "Z4", "Z5"],
    "pace_zones": [76.0, 87.0, 93.0, 100.0, 102.0, 115.0, 999.0],
}


class TestGetSportSettings:
    async def test_surfaces_thresholds_and_zones(self, mock_config, respx_mock):
        mock_ctx = MagicMock()

        respx_mock.get("/athlete/i123456/sport-settings").mock(
            return_value=Response(200, json=[RUN_SETTINGS])
        )

        with (
            patch.object(ss, "load_config", return_value=mock_config),
            patch.object(ss, "validate_credentials", return_value=True),
        ):
            result = await ss.get_sport_settings(ctx=mock_ctx)

        response = json.loads(result)
        entry = response["data"]["sport_settings"][0]

        assert entry["types"] == ["Run", "VirtualRun", "TrailRun"]
        assert entry["lthr_bpm"] == 168
        assert entry["max_hr_bpm"] == 200
        assert entry["ftp_watts"] == 221
        assert entry["threshold_pace"] == "6:40 /km"
        assert entry["hr_zones_bpm"] == [136, 151, 159, 167, 171, 177, 200]
        assert entry["pace_zones_pct"][0] == 76.0


class TestPaceFormatter:
    def test_meters_per_second_to_min_per_km(self):
        assert ss._format_pace_per_km(2.5) == "6:40 /km"

    def test_none_and_zero(self):
        assert ss._format_pace_per_km(None) is None
        assert ss._format_pace_per_km(0) is None
