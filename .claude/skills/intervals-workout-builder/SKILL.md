---
name: intervals-workout-builder
description: Build structured Intervals.icu workouts — the step/repeat text syntax the API parses server-side, and how to create, edit, and schedule them via this MCP server's tools. Use when creating, editing, or planning structured workouts (interval sets, threshold blocks, zone-based sessions) for Intervals.icu.
---

# Intervals.icu Workout Builder

Intervals.icu parses a workout's **description text** server-side into a structured
`workout_doc` (steps with power/HR/pace targets). You write the text; the API builds
the structure. This skill is the validated reference for that syntax plus the tool flow.

Official guide: https://forum.intervals.icu/t/workout-builder-syntax-quick-guide/123701

## Step syntax

Each step is a line: `- <label> <duration> <target> [cadence]`

- **Label** — optional cue text; any text before the first duration (e.g. `Warm up`, `Hard`).
- **Duration** — `m`=minutes, `s`=seconds, `h`=hours (`1h2m30s`, `30s`, `5'`, `30"`).
  ⚠️ Distance uses `mtr` / `km` / `mi`. **`m` is MINUTES, not meters.**
- **Target**:
  - HR: `65-83% LTHR` (% of threshold HR), `70% HR` (% of max), or `Z2 HR` (HR zone).
  - Power: `60-80%` (% FTP), `220w` / `200-240w`, `Z2` / `Z3-Z4`, `CZ1` (custom zones).
  - Pace: `78-82% Pace`, `Z2 Pace`, `5:00/km Pace`.
  - `ramp 50-75%` for a gradual change; `freeride` to disable ERG.
- **Cadence** (optional, after target): `90rpm`, `90-100rpm`.

> A bare `Z2` means **power** when an FTP is set. For HR-zone targets use `Z2 HR`
> (or an explicit `% LTHR` range).

## Repeats (intervals)

Put `Nx` (e.g. `5x`) on its own line, with the repeated `- ` steps under it.
**A blank line before AND after the repeat block is required** — without the leading
blank line the `Nx` is ignored and the steps do not multiply. (A header form also
works: `Main Set 4x` followed by steps.)

### Worked example (HR-based threshold session, ~45 min)

```
- Warm up 12m 65-83% LTHR

5x
- Hard 3m 95-100% LTHR
- Easy 2m 65-70% LTHR

- Cool Down 8m 65-70% LTHR
```

Parses to: warmup + a `reps:5` block of [3 min hard, 2 min easy] + cooldown.

## Creating and scheduling via the MCP tools

1. Find a target folder/plan: `get_workout_library` (folders), `get_workouts_in_folder`.
2. Create it: `create_workout(folder_id, name, workout_type, description=<step text>, ...)`.
   The `description` carries the step syntax above; the API returns the parsed `workout_doc`.
3. Inspect/verify: `get_workout(workout_id)` returns the structured steps.
4. Edit: `update_workout(workout_id, ...)` (only provided fields change).
5. Remove: `delete_workout(workout_id)`.

To put a session on the calendar as a planned workout, use `create_event` with
`category="WORKOUT"`, the activity `event_type`, and the same step syntax in the
description so it syncs to the athlete's device.

## Verify after creating

Always check the returned `workout_doc`: confirm repeat blocks show `reps: N` with
nested steps, and that HR steps show `units: "%lthr"` (not power) when you intended HR.
If reps didn't expand, you're missing a blank line around the `Nx` block.
