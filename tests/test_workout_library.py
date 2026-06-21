"""Tests for structured workout-library CRUD tools."""

import json
from unittest.mock import MagicMock

from httpx import Response

from intervals_icu_mcp.tools.workout_library import (
    create_workout,
    delete_workout,
    get_workout,
    update_workout,
)

WORKOUT = {
    "id": 42,
    "name": "Threshold 5x3",
    "type": "Run",
    "folder_id": 10,
    "description": "- 12m Z2\n- 5x3m Z4 2m Z1\n- 8m Z1",
    "moving_time": 2700,
    "icu_training_load": 55,
    "workout_doc": {"steps": [{"duration": 720, "zone": "Z2"}]},
}


def _ctx(mock_config):
    ctx = MagicMock()
    ctx.get_state.return_value = mock_config
    return ctx


class TestGetWorkout:
    async def test_returns_structure(self, mock_config, respx_mock):
        respx_mock.get("/athlete/i123456/workouts/42").mock(
            return_value=Response(200, json=WORKOUT)
        )

        result = await get_workout(workout_id=42, ctx=_ctx(mock_config))

        data = json.loads(result)["data"]
        assert data["id"] == 42
        assert data["workout_doc"]["steps"][0]["zone"] == "Z2"
        assert data["metrics"]["training_load"] == 55


class TestCreateWorkout:
    async def test_posts_expected_body(self, mock_config, respx_mock):
        route = respx_mock.post("/athlete/i123456/workouts").mock(
            return_value=Response(200, json=WORKOUT)
        )

        await create_workout(
            folder_id=10,
            name="Threshold 5x3",
            workout_type="Run",
            description="- 12m Z2\n- 5x3m Z4 2m Z1\n- 8m Z1",
            duration_seconds=2700,
            training_load=55,
            ctx=_ctx(mock_config),
        )

        body = json.loads(route.calls.last.request.content)
        assert body["folder_id"] == 10
        assert body["type"] == "Run"
        assert body["name"] == "Threshold 5x3"
        assert "Z4" in body["description"]
        assert body["moving_time"] == 2700
        assert body["icu_training_load"] == 55


class TestUpdateWorkout:
    async def test_puts_only_provided_fields(self, mock_config, respx_mock):
        route = respx_mock.put("/athlete/i123456/workouts/42").mock(
            return_value=Response(200, json=WORKOUT)
        )

        await update_workout(workout_id=42, name="Renamed", ctx=_ctx(mock_config))

        body = json.loads(route.calls.last.request.content)
        assert body == {"name": "Renamed"}

    async def test_no_fields_is_validation_error(self, mock_config, respx_mock):
        route = respx_mock.put("/athlete/i123456/workouts/42").mock(
            return_value=Response(200, json=WORKOUT)
        )

        result = await update_workout(workout_id=42, ctx=_ctx(mock_config))

        assert not route.called
        assert json.loads(result)["error"]["type"] == "validation_error"


class TestDeleteWorkout:
    async def test_deletes(self, mock_config, respx_mock):
        route = respx_mock.delete("/athlete/i123456/workouts/42").mock(return_value=Response(200))

        result = await delete_workout(workout_id=42, ctx=_ctx(mock_config))

        assert route.called
        assert json.loads(result)["data"]["deleted"] is True
