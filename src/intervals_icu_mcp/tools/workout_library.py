"""Workout library tools for Intervals.icu MCP server."""

from typing import Annotated, Any

from fastmcp import Context

from ..auth import ICUConfig
from ..client import ICUAPIError, ICUClient
from ..response_builder import ResponseBuilder


def _workout_summary(workout: Any) -> dict[str, Any]:
    """Build a readable summary of a library workout for tool responses."""
    info: dict[str, Any] = {"id": workout.id, "name": workout.name}
    if workout.type:
        info["type"] = workout.type
    if workout.folder_id:
        info["folder_id"] = workout.folder_id
    if workout.description:
        info["description"] = workout.description

    metrics: dict[str, Any] = {}
    if workout.moving_time:
        metrics["duration_seconds"] = workout.moving_time
    if workout.distance:
        metrics["distance_meters"] = workout.distance
    if workout.icu_training_load:
        metrics["training_load"] = workout.icu_training_load
    if workout.icu_intensity:
        metrics["intensity_factor"] = workout.icu_intensity
    if metrics:
        info["metrics"] = metrics

    if workout.indoor is not None:
        info["indoor"] = workout.indoor
    if workout.color:
        info["color"] = workout.color
    if workout.tags:
        info["tags"] = workout.tags
    # The parsed structured steps (present once Intervals has parsed the description).
    if workout.workout_doc:
        info["workout_doc"] = workout.workout_doc
    return info


async def get_workout(
    workout_id: Annotated[int, "Workout ID to fetch"],
    ctx: Context | None = None,
) -> str:
    """Get a single library workout, including its structured steps (workout_doc).

    Args:
        workout_id: ID of the workout to fetch

    Returns:
        JSON string with the workout details and structure
    """
    assert ctx is not None
    config: ICUConfig = ctx.get_state("config")

    try:
        async with ICUClient(config) as client:
            workout = await client.get_workout(workout_id)
            return ResponseBuilder.build_response(
                data=_workout_summary(workout),
                query_type="get_workout",
            )
    except ICUAPIError as e:
        return ResponseBuilder.build_error_response(e.message, error_type="api_error")
    except Exception as e:
        return ResponseBuilder.build_error_response(
            f"Unexpected error: {str(e)}", error_type="internal_error"
        )


async def create_workout(
    folder_id: Annotated[int, "ID of the folder or training plan to create the workout in"],
    name: Annotated[str, "Workout name"],
    workout_type: Annotated[str, "Activity type (e.g., Run, Ride, Swim)"],
    description: Annotated[
        str | None,
        "Workout text with optional structured steps Intervals.icu parses server-side. "
        "Each step is a line '- <label> <duration> <target>'. Duration: 12m, 90s, 1h. "
        "Target: HR as '70-83% LTHR', power as '60-80%' (%FTP), pace, or a zone like 'Z2' "
        "(zones default to power when an FTP is set). Repeats: a BLANK LINE, then a line "
        "'Nx' (e.g. '5x'), then the '- ' step lines to repeat, then another BLANK LINE. "
        "The surrounding blank lines are required for the repeat to expand. "
        "HR example:\\n- Warm up 12m 65-83% LTHR\\n\\n5x\\n- Hard 3m 95-100% LTHR\\n"
        "- Easy 2m 65-70% LTHR\\n\\n- Cool Down 8m 65-70% LTHR",
    ] = None,
    duration_seconds: Annotated[int | None, "Planned duration in seconds"] = None,
    distance_meters: Annotated[float | None, "Planned distance in meters"] = None,
    training_load: Annotated[int | None, "Planned training load"] = None,
    indoor: Annotated[bool | None, "Whether this is an indoor workout"] = None,
    color: Annotated[str | None, "Display color (hex, e.g. '#00ff00')"] = None,
    tags: Annotated[list[str] | None, "Tags to apply to the workout"] = None,
    ctx: Context | None = None,
) -> str:
    """Create a structured workout in the athlete's library (a folder or plan).

    Structure comes from the description using Intervals.icu's step syntax (parsed
    server-side), so you don't build raw step JSON. The workout can then be dropped
    onto the calendar as a planned session that syncs to the athlete's device.

    Returns:
        JSON string with the created workout
    """
    assert ctx is not None
    config: ICUConfig = ctx.get_state("config")

    try:
        workout_data: dict[str, Any] = {
            "folder_id": folder_id,
            "name": name,
            "type": workout_type,
        }
        if description is not None:
            workout_data["description"] = description
        if duration_seconds is not None:
            workout_data["moving_time"] = duration_seconds
        if distance_meters is not None:
            workout_data["distance"] = distance_meters
        if training_load is not None:
            workout_data["icu_training_load"] = training_load
        if indoor is not None:
            workout_data["indoor"] = indoor
        if color is not None:
            workout_data["color"] = color
        if tags is not None:
            workout_data["tags"] = tags

        async with ICUClient(config) as client:
            workout = await client.create_workout(workout_data)
            return ResponseBuilder.build_response(
                data=_workout_summary(workout),
                query_type="create_workout",
                metadata={"message": f"Successfully created workout: {name}"},
            )
    except ICUAPIError as e:
        return ResponseBuilder.build_error_response(e.message, error_type="api_error")
    except Exception as e:
        return ResponseBuilder.build_error_response(
            f"Unexpected error: {str(e)}", error_type="internal_error"
        )


async def update_workout(
    workout_id: Annotated[int, "Workout ID to update"],
    name: Annotated[str | None, "Updated workout name"] = None,
    description: Annotated[
        str | None,
        "Updated description. Same step syntax as create_workout: steps like "
        "'- 12m 70-83% LTHR'; repeats via an 'Nx' line followed by '- ' steps.",
    ] = None,
    workout_type: Annotated[str | None, "Updated activity type"] = None,
    duration_seconds: Annotated[int | None, "Updated duration in seconds"] = None,
    distance_meters: Annotated[float | None, "Updated distance in meters"] = None,
    training_load: Annotated[int | None, "Updated training load"] = None,
    indoor: Annotated[bool | None, "Updated indoor flag"] = None,
    color: Annotated[str | None, "Updated display color (hex)"] = None,
    tags: Annotated[list[str] | None, "Updated tags"] = None,
    ctx: Context | None = None,
) -> str:
    """Update an existing library workout. Only provided fields are changed.

    Returns:
        JSON string with the updated workout
    """
    assert ctx is not None
    config: ICUConfig = ctx.get_state("config")

    workout_data: dict[str, Any] = {}
    if name is not None:
        workout_data["name"] = name
    if description is not None:
        workout_data["description"] = description
    if workout_type is not None:
        workout_data["type"] = workout_type
    if duration_seconds is not None:
        workout_data["moving_time"] = duration_seconds
    if distance_meters is not None:
        workout_data["distance"] = distance_meters
    if training_load is not None:
        workout_data["icu_training_load"] = training_load
    if indoor is not None:
        workout_data["indoor"] = indoor
    if color is not None:
        workout_data["color"] = color
    if tags is not None:
        workout_data["tags"] = tags

    if not workout_data:
        return ResponseBuilder.build_error_response(
            "No fields provided to update. Specify at least one field to change.",
            error_type="validation_error",
        )

    try:
        async with ICUClient(config) as client:
            workout = await client.update_workout(workout_id, workout_data)
            return ResponseBuilder.build_response(
                data=_workout_summary(workout),
                query_type="update_workout",
                metadata={"message": f"Successfully updated workout {workout_id}"},
            )
    except ICUAPIError as e:
        return ResponseBuilder.build_error_response(e.message, error_type="api_error")
    except Exception as e:
        return ResponseBuilder.build_error_response(
            f"Unexpected error: {str(e)}", error_type="internal_error"
        )


async def delete_workout(
    workout_id: Annotated[int, "Workout ID to delete"],
    ctx: Context | None = None,
) -> str:
    """Delete a library workout. This cannot be undone.

    Returns:
        JSON string with deletion confirmation
    """
    assert ctx is not None
    config: ICUConfig = ctx.get_state("config")

    try:
        async with ICUClient(config) as client:
            await client.delete_workout(workout_id)
            return ResponseBuilder.build_response(
                data={"workout_id": workout_id, "deleted": True},
                query_type="delete_workout",
                metadata={"message": f"Successfully deleted workout {workout_id}"},
            )
    except ICUAPIError as e:
        return ResponseBuilder.build_error_response(e.message, error_type="api_error")
    except Exception as e:
        return ResponseBuilder.build_error_response(
            f"Unexpected error: {str(e)}", error_type="internal_error"
        )


async def get_workout_library(
    ctx: Context | None = None,
) -> str:
    """Get workout library folders and training plans.

    Returns all workout folders and training plans available to you, including
    your personal workouts, shared workouts, and any training plans you follow.

    Each folder contains structured workouts that can be applied to your calendar.

    Returns:
        JSON string with workout folders/plans
    """
    assert ctx is not None
    config: ICUConfig = ctx.get_state("config")

    try:
        async with ICUClient(config) as client:
            folders = await client.get_workout_folders()

            if not folders:
                return ResponseBuilder.build_response(
                    data={"folders": [], "count": 0},
                    metadata={
                        "message": "No workout folders found. Create folders in Intervals.icu to organize your workouts."
                    },
                )

            folders_data: list[dict[str, Any]] = []
            for folder in folders:
                folder_item: dict[str, Any] = {
                    "id": folder.id,
                    "name": folder.name,
                }

                if folder.description:
                    folder_item["description"] = folder.description
                if folder.num_workouts:
                    folder_item["num_workouts"] = folder.num_workouts

                # Training plan info
                if folder.start_date_local:
                    folder_item["start_date"] = folder.start_date_local
                if folder.duration_weeks:
                    folder_item["duration_weeks"] = folder.duration_weeks
                if folder.hours_per_week_min or folder.hours_per_week_max:
                    folder_item["hours_per_week"] = {
                        "min": folder.hours_per_week_min,
                        "max": folder.hours_per_week_max,
                    }

                folders_data.append(folder_item)

            # Categorize folders
            training_plans = [f for f in folders if f.duration_weeks is not None]
            regular_folders = [f for f in folders if f.duration_weeks is None]

            summary = {
                "total_folders": len(folders),
                "training_plans": len(training_plans),
                "regular_folders": len(regular_folders),
                "total_workouts": sum(f.num_workouts or 0 for f in folders),
            }

            result_data = {
                "folders": folders_data,
                "summary": summary,
            }

            return ResponseBuilder.build_response(
                data=result_data,
                query_type="workout_library",
            )

    except ICUAPIError as e:
        return ResponseBuilder.build_error_response(e.message, error_type="api_error")
    except Exception as e:
        return ResponseBuilder.build_error_response(
            f"Unexpected error: {str(e)}", error_type="internal_error"
        )


async def get_workouts_in_folder(
    folder_id: Annotated[int, "Folder ID to get workouts from"],
    ctx: Context | None = None,
) -> str:
    """Get all workouts in a specific folder or training plan.

    Returns detailed information about all workouts stored in a folder,
    including their structure, intensity, and training load.

    Args:
        folder_id: ID of the folder to browse

    Returns:
        JSON string with workout details
    """
    assert ctx is not None
    config: ICUConfig = ctx.get_state("config")

    try:
        async with ICUClient(config) as client:
            workouts = await client.get_workouts_in_folder(folder_id)

            if not workouts:
                return ResponseBuilder.build_response(
                    data={"workouts": [], "count": 0, "folder_id": folder_id},
                    metadata={"message": f"No workouts found in folder {folder_id}"},
                )

            workouts_data: list[dict[str, Any]] = []
            for workout in workouts:
                workout_item: dict[str, Any] = {
                    "id": workout.id,
                    "name": workout.name,
                }

                if workout.description:
                    workout_item["description"] = workout.description
                if workout.type:
                    workout_item["type"] = workout.type

                # Workout metrics
                metrics: dict[str, Any] = {}
                if workout.moving_time:
                    metrics["duration_seconds"] = workout.moving_time
                if workout.distance:
                    metrics["distance_meters"] = workout.distance
                if workout.icu_training_load:
                    metrics["training_load"] = workout.icu_training_load
                if workout.icu_intensity:
                    metrics["intensity_factor"] = workout.icu_intensity
                if workout.joules:
                    metrics["joules"] = workout.joules
                if workout.joules_above_ftp:
                    metrics["joules_above_ftp"] = workout.joules_above_ftp

                if metrics:
                    workout_item["metrics"] = metrics

                # Other properties
                if workout.indoor is not None:
                    workout_item["indoor"] = workout.indoor
                if workout.color:
                    workout_item["color"] = workout.color

                workouts_data.append(workout_item)

            # Calculate summary
            total_duration = sum(w.moving_time or 0 for w in workouts)
            total_load = sum(w.icu_training_load or 0 for w in workouts)
            indoor_count = sum(1 for w in workouts if w.indoor)

            summary = {
                "total_workouts": len(workouts),
                "total_duration_seconds": total_duration,
                "total_training_load": total_load,
                "indoor_workouts": indoor_count,
            }

            result_data = {
                "folder_id": folder_id,
                "workouts": workouts_data,
                "summary": summary,
            }

            return ResponseBuilder.build_response(
                data=result_data,
                query_type="folder_workouts",
            )

    except ICUAPIError as e:
        return ResponseBuilder.build_error_response(e.message, error_type="api_error")
    except Exception as e:
        return ResponseBuilder.build_error_response(
            f"Unexpected error: {str(e)}", error_type="internal_error"
        )
