"""Tests for event/calendar management tools.

Focus: the date-normalization regression. The Intervals ``start_date_local``
field requires a full datetime; the tools accept a bare ``YYYY-MM-DD`` from
callers and must append a time component before sending, otherwise the API
returns HTTP 422.
"""

import json
from unittest.mock import MagicMock

import pytest
from httpx import Response

from intervals_icu_mcp.tools.event_management import (
    _normalize_event_date,
    bulk_create_events,
    create_event,
    update_event,
)


class TestNormalizeEventDate:
    """Unit tests for the _normalize_event_date helper."""

    def test_bare_date_gets_midnight_appended(self):
        assert _normalize_event_date("2025-10-14") == "2025-10-14T00:00:00"

    def test_full_datetime_is_preserved(self):
        assert _normalize_event_date("2025-10-14T07:30:00") == "2025-10-14T07:30:00"

    def test_datetime_with_offset_is_normalized(self):
        # Offset is dropped; the local wall-clock time is kept.
        assert _normalize_event_date("2025-10-14T07:30:00+02:00") == "2025-10-14T07:30:00"

    @pytest.mark.parametrize("bad", ["not-a-date", "2025-13-01", "10/14/2025", ""])
    def test_invalid_input_raises(self, bad):
        with pytest.raises(ValueError):
            _normalize_event_date(bad)


class TestCreateEvent:
    """The outgoing request must carry a normalized datetime."""

    async def test_create_event_normalizes_bare_date(
        self, mock_config, respx_mock, mock_event_data
    ):
        mock_ctx = MagicMock()
        mock_ctx.get_state.return_value = mock_config

        route = respx_mock.post("/athlete/i123456/events").mock(
            return_value=Response(200, json=mock_event_data)
        )

        result = await create_event(
            start_date="2025-10-14",
            name="Threshold Intervals",
            category="WORKOUT",
            ctx=mock_ctx,
        )

        assert route.called
        sent = json.loads(route.calls.last.request.content)
        assert sent["start_date_local"] == "2025-10-14T00:00:00"

        response = json.loads(result)
        assert "data" in response

    async def test_create_event_rejects_bad_date_without_calling_api(self, mock_config, respx_mock):
        mock_ctx = MagicMock()
        mock_ctx.get_state.return_value = mock_config

        route = respx_mock.post("/athlete/i123456/events").mock(return_value=Response(200, json={}))

        result = await create_event(
            start_date="14-10-2025",
            name="Bad",
            category="WORKOUT",
            ctx=mock_ctx,
        )

        assert not route.called
        response = json.loads(result)
        assert response["error"]["type"] == "validation_error"


class TestEventCategories:
    """The API enum uses RACE_A/B/C and TARGET, not RACE/GOAL."""

    async def test_accepts_race_a(self, mock_config, respx_mock, mock_event_data):
        mock_ctx = MagicMock()
        mock_ctx.get_state.return_value = mock_config

        route = respx_mock.post("/athlete/i123456/events").mock(
            return_value=Response(200, json={**mock_event_data, "category": "RACE_A"})
        )

        await create_event(
            start_date="2025-10-14",
            name="Goal Race",
            category="RACE_A",
            ctx=mock_ctx,
        )

        assert route.called
        sent = json.loads(route.calls.last.request.content)
        assert sent["category"] == "RACE_A"

    async def test_rejects_legacy_race_and_goal(self, mock_config, respx_mock):
        mock_ctx = MagicMock()
        mock_ctx.get_state.return_value = mock_config

        route = respx_mock.post("/athlete/i123456/events").mock(return_value=Response(200, json={}))

        for bad in ("RACE", "GOAL"):
            result = await create_event(
                start_date="2025-10-14",
                name="X",
                category=bad,
                ctx=mock_ctx,
            )
            assert not route.called
            assert json.loads(result)["error"]["type"] == "validation_error"


class TestUpdateEvent:
    async def test_update_event_normalizes_start_date(
        self, mock_config, respx_mock, mock_event_data
    ):
        mock_ctx = MagicMock()
        mock_ctx.get_state.return_value = mock_config

        route = respx_mock.put("/athlete/i123456/events/1001").mock(
            return_value=Response(200, json=mock_event_data)
        )

        await update_event(
            event_id=1001,
            start_date="2025-10-14",
            ctx=mock_ctx,
        )

        assert route.called
        sent = json.loads(route.calls.last.request.content)
        assert sent["start_date_local"] == "2025-10-14T00:00:00"


class TestBulkCreateEvents:
    async def test_bulk_create_normalizes_each_date(self, mock_config, respx_mock, mock_event_data):
        mock_ctx = MagicMock()
        mock_ctx.get_state.return_value = mock_config

        route = respx_mock.post("/athlete/i123456/events/bulk").mock(
            return_value=Response(200, json=[mock_event_data])
        )

        events = json.dumps(
            [
                {
                    "start_date_local": "2025-10-14",
                    "name": "Run A",
                    "category": "WORKOUT",
                },
                {
                    "start_date_local": "2025-10-15T06:00:00",
                    "name": "Run B",
                    "category": "WORKOUT",
                },
            ]
        )

        await bulk_create_events(events=events, ctx=mock_ctx)

        assert route.called
        sent = json.loads(route.calls.last.request.content)
        assert sent[0]["start_date_local"] == "2025-10-14T00:00:00"
        assert sent[1]["start_date_local"] == "2025-10-15T06:00:00"
