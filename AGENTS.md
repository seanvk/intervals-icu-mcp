# AGENTS.md

Operating guide for AI agents working on this fork (`seanvk/intervals-icu-mcp`).
For project architecture, the tool pattern, and dev commands, see
[CLAUDE.md](CLAUDE.md). This file captures the things that have actually bitten
us: the runtime version constraint, deployment, and known API quirks.

## Runtime constraint: FastMCP 2.x

The deployed image pins **FastMCP 2.12.x** (see `uv.lock`). Tool functions read
config with **synchronous** `ctx.get_state("config")`.

- Do **NOT** change these to `await ctx.get_state(...)`. That is FastMCP 3.x only
  and will break the running server. (Upstream PR #4 makes this change wholesale —
  do not port it without also bumping FastMCP across the project and the image.)
- A local `pip install -e .` may resolve FastMCP 3.x. Tests still pass because they
  call the tool functions directly with a mocked `ctx`, so they are framework-agnostic.
  When validating registration, do it inside the built image, not the local venv.

## Testing & lint

- `.venv/bin/python -m pytest -q` (or `make test`). The repo `.venv` has pytest + respx.
- `make lint` (ruff + pyright), `make format`. Ruff line-length is 100.
- Test pattern: mock `ctx` with `MagicMock()` and `ctx.get_state.return_value = mock_config`;
  mock HTTP with `respx`; for write tools, assert the **outgoing request body**. See
  `tests/test_event_management.py`, `tests/test_sport_settings.py`, `tests/test_workout_library.py`.
- `openapi-spec.json` is the source of truth for endpoints, HTTP methods, and field
  names. Check it before adding or changing a client call.

## Deployment (Asustor NAS)

The server runs in Docker on the NAS, registered in Claude Code at user scope as
`intervals-icu` via `docker run -i` over SSH. **Git is not installed on the NAS** —
source is streamed from the Mac. After merging to `main`:

```bash
cd ~/dev/intervals-icu-mcp
COPYFILE_DISABLE=1 tar czf - \
  --exclude='.git' --exclude='__pycache__' --exclude='*.egg-info' \
  --exclude='.pytest_cache' --exclude='.ruff_cache' --exclude='.venv' --exclude='.DS_Store' . \
| ssh Sean@192.168.4.57 'tar xzf - -C /volume1/Docker/intervals-icu/src \
  && docker build -q -t intervals-icu-mcp:latest /volume1/Docker/intervals-icu/src'
```

- A rebuild does **not** affect the running session's container. **Restart Claude Code**
  to reconnect to the new image.
- Verify a build with a throwaway container, e.g.
  `docker run --rm --entrypoint python intervals-icu-mcp:latest -c "..."`.
- Credentials live only on the NAS (`/volume1/Docker/intervals-icu/*.env`, mounted to
  `/app/.env`); never commit them.

**Workflow norm:** branch → test + ruff → commit → `git merge --ff-only` to `main` →
push → deploy → restart.

## Known API quirks (do not reintroduce)

Intervals.icu field and method names often differ from the obvious. These were all
real bugs fixed in this fork:

- **Event `start_date_local`** needs a full datetime (`...T00:00:00`), not a bare date
  (else HTTP 422). When reading events, parse with `datetime.fromisoformat` — events
  carry a time component.
- **Event categories**: `RACE_A` / `RACE_B` / `RACE_C`, `TARGET`, `NOTE`, etc. — NOT
  `RACE` / `GOAL` (else HTTP 400).
- **Activity power** comes back as `icu_average_watts` / `icu_weighted_avg_watts`
  (aliased on the model with `populate_by_name=True`).
- **Sport settings** use `types` (list), `lthr`, `max_hr`, `threshold_pace`
  (**meters/second**), `pace_units`, and `hr_zones` / `power_zones` / `pace_zones` —
  NOT `type` / `fthr` / `pace_threshold`. The `apply` endpoint is **PUT**, not POST.
- **Listing workouts in a folder**: `GET /folders/{id}/workouts` is **PUT-only** (405 on
  GET). List `GET /workouts` and filter by `folder_id`.
- **Structured workout text syntax** (what the API parses server-side from a
  description) is non-obvious — see the `intervals-workout-builder` skill at
  [.claude/skills/intervals-workout-builder/SKILL.md](.claude/skills/intervals-workout-builder/SKILL.md).
