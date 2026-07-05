# Apartment Lights Engine

Deterministic room-light decision engine for Home Assistant.

This integration extracts room lighting rules into one reusable backend service:

- one immutable snapshot of room state
- one explicit trigger cause
- one computed decision
- one executed action plan

Current scope:

- living room, bedroom, corridor and kitchen room mappings are defined in
  [custom_components/apartment_lights_engine/rooms.py](custom_components/apartment_lights_engine/rooms.py)
- each room mapping may also define an optional shutter/cover entity that lets
  `main_off` switch to ambient immediately when the shutter is closed
- each room mapping may define an optional sleep-mode switch; when it is `on`,
  automatic paths that would turn on main light use ambient instead
- each room may be marked as always dark; then lux and neighbor-main mappings
  are not used, and automatic entry turns on main plus ambient
- service response includes the snapshot and matched decision
- intended to replace large YAML `choose` automations with thin wrappers

## Service

Service name:

- `apartment_lights_engine.evaluate_room`

Parameters:

- `room`
- `cause`
- `dry_run` optional

When the caller requests a response, the service returns:

- `room`
- `cause`
- `snapshot`
- `decision`
- `dry_run`

## HAOS deployment

Recommended target path on Home Assistant OS:

- manual install: `/config/custom_components/apartment_lights_engine`
- HACS install: custom repository with this repo as category `Integration`

Detailed rollout notes are in
[docs/HAOS_DEPLOYMENT.md](docs/HAOS_DEPLOYMENT.md).

## Status

This repository is the source package intended for HAOS deployment, either:

- manually into `/config/custom_components/apartment_lights_engine`
- through HACS as a custom integration repository
