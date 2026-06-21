"""Tests for activity streams and histogram parsing.

Regression: the Intervals API returns streams as a list of {type, data} objects
and histograms as a bare list of bins, but the client did Model(**response),
which crashed ("argument after ** must be a mapping, not list").
"""

import json
from unittest.mock import MagicMock

from httpx import Response

from intervals_icu_mcp.models import ActivityStreams, Histogram
from intervals_icu_mcp.tools.activity_analysis import get_activity_streams, get_hr_histogram

# Real API shapes
STREAMS_LIST = [
    {"type": "heartrate", "data": [120, 130, 140], "valueType": "java.lang.Integer"},
    {"type": "velocity_smooth", "data": [2.0, 2.1, 2.2]},
    {"type": "some_future_type", "data": [1, 2, 3]},  # unknown -> ignored
]
HR_HISTOGRAM_LIST = [
    {"min": 100, "max": 104, "secs": 14},
    {"min": 104, "max": 108, "secs": 60},
    {"min": 108, "max": 112, "secs": 120},
]


def _ctx(mock_config):
    ctx = MagicMock()
    ctx.get_state.return_value = mock_config
    return ctx


class TestModelFromApi:
    def test_streams_from_list(self):
        s = ActivityStreams.from_api(STREAMS_LIST)
        assert s.heartrate == [120, 130, 140]
        assert s.velocity_smooth == [2.0, 2.1, 2.2]

    def test_histogram_from_list(self):
        h = Histogram.from_api(HR_HISTOGRAM_LIST)
        assert len(h.bins) == 3
        assert h.bins[0].min == 100
        assert h.bins[0].count is None  # API omits count
        assert h.total_secs == 14 + 60 + 120


class TestStreamsTool:
    async def test_returns_available_streams(self, mock_config, respx_mock):
        respx_mock.get("/activity/i1/streams").mock(return_value=Response(200, json=STREAMS_LIST))

        result = await get_activity_streams(activity_id="i1", ctx=_ctx(mock_config))

        data = json.loads(result)["data"]
        assert "heartrate" in data["available_streams"]
        assert data["stream_lengths"]["heartrate"] == 3


class TestHistogramTool:
    async def test_hr_histogram_bins(self, mock_config, respx_mock):
        respx_mock.get("/activity/i1/hr-histogram").mock(
            return_value=Response(200, json=HR_HISTOGRAM_LIST)
        )

        result = await get_hr_histogram(activity_id="i1", ctx=_ctx(mock_config))

        parsed = json.loads(result)
        assert "error" not in parsed
        data = parsed["data"]
        assert len(data["bins"]) == 3
        assert data["bins"][0]["time_seconds"] == 14
        assert data["total_time_seconds"] == 194
