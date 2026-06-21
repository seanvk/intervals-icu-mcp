"""Tests for event-reading tools (calendar / upcoming).

Regression: events created via the API carry a full datetime
``start_date_local`` (e.g. ``2025-10-14T07:00:00``). The date-grouping logic
must not assume a bare ``YYYY-MM-DD`` or it raises ``ValueError`` on real data.
"""

import json
from unittest.mock import MagicMock

from httpx import Response

from intervals_icu_mcp.tools.events import get_calendar_events, get_upcoming_workouts


class TestGetCalendarEvents:
    async def test_handles_datetime_start_date_local(
        self, mock_config, respx_mock, mock_event_data
    ):
        mock_ctx = MagicMock()
        mock_ctx.get_state.return_value = mock_config

        event = {**mock_event_data, "start_date_local": "2025-10-14T07:00:00"}
        respx_mock.get("/athlete/i123456/events").mock(return_value=Response(200, json=[event]))

        result = await get_calendar_events(days_ahead=7, days_back=0, ctx=mock_ctx)

        response = json.loads(result)
        assert "error" not in response
        assert response["data"]["summary"]["total_events"] == 1


class TestGetUpcomingWorkouts:
    async def test_handles_datetime_start_date_local(
        self, mock_config, respx_mock, mock_event_data
    ):
        mock_ctx = MagicMock()
        mock_ctx.get_state.return_value = mock_config

        workout = {
            **mock_event_data,
            "category": "WORKOUT",
            "start_date_local": "2025-10-14T07:00:00",
        }
        respx_mock.get("/athlete/i123456/events").mock(return_value=Response(200, json=[workout]))

        result = await get_upcoming_workouts(ctx=mock_ctx)

        response = json.loads(result)
        assert "error" not in response
