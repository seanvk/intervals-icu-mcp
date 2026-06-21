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


class TestPaceConversion:
    def test_min_per_km_to_m_s(self):
        # 6:40 /km == 4.0 min/km -> 1000 / (4 * 60) == ~4.167 m/s
        assert ss._pace_per_km_to_m_s(4.0) == 1000 / 240

    def test_min_per_100m_to_m_s(self):
        # 1:30 /100m == 1.5 min/100m -> 100 / (1.5 * 60) == ~1.111 m/s
        assert ss._pace_per_100m_to_m_s(1.5) == 100 / 90

    def test_none_and_zero(self):
        assert ss._pace_per_km_to_m_s(None) is None
        assert ss._pace_per_km_to_m_s(0) is None
        assert ss._pace_per_100m_to_m_s(None) is None
        assert ss._pace_per_100m_to_m_s(0) is None


class TestUpdateSportSettings:
    async def test_writes_lthr_and_threshold_pace_in_m_s(self, mock_config, respx_mock):
        route = respx_mock.put("/athlete/i123456/sport-settings/796623").mock(
            return_value=Response(200, json=RUN_SETTINGS)
        )

        with (
            patch.object(ss, "load_config", return_value=mock_config),
            patch.object(ss, "validate_credentials", return_value=True),
        ):
            await ss.update_sport_settings(
                sport_id=796623, ftp=221, fthr=168, pace_threshold=4.0
            )

        body = json.loads(route.calls.last.request.content)
        # Friendly params must map to the real API keys, not fthr/pace_threshold.
        assert "fthr" not in body
        assert "pace_threshold" not in body
        assert body["ftp"] == 221
        assert body["lthr"] == 168
        assert body["threshold_pace"] == 1000 / 240  # 4:00 /km in m/s

    async def test_swim_threshold_maps_to_threshold_pace_in_m_s(
        self, mock_config, respx_mock
    ):
        route = respx_mock.put("/athlete/i123456/sport-settings/796625").mock(
            return_value=Response(200, json=RUN_SETTINGS)
        )

        with (
            patch.object(ss, "load_config", return_value=mock_config),
            patch.object(ss, "validate_credentials", return_value=True),
        ):
            await ss.update_sport_settings(sport_id=796625, swim_threshold=1.5)

        body = json.loads(route.calls.last.request.content)
        assert "swim_threshold" not in body
        assert body["threshold_pace"] == 100 / 90  # 1:30 /100m in m/s


class TestCreateSportSettings:
    async def test_writes_types_array_and_real_keys(self, mock_config, respx_mock):
        route = respx_mock.post("/athlete/i123456/sport-settings").mock(
            return_value=Response(200, json=RUN_SETTINGS)
        )

        with (
            patch.object(ss, "load_config", return_value=mock_config),
            patch.object(ss, "validate_credentials", return_value=True),
        ):
            await ss.create_sport_settings(
                sport_type="Run", ftp=221, fthr=168, pace_threshold=4.0
            )

        body = json.loads(route.calls.last.request.content)
        assert body["types"] == ["Run"]
        assert "type" not in body
        assert "fthr" not in body
        assert "pace_threshold" not in body
        assert body["lthr"] == 168
        assert body["threshold_pace"] == 1000 / 240
