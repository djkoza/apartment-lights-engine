# Apartment Lights Engine

Deterministic room-light decision engine for Home Assistant.

This integration extracts room lighting rules into one reusable backend service:

- one immutable snapshot of room state
- one explicit trigger cause
- one computed decision
- one executed action plan

Current scope:

- living room and bedroom room mappings are defined in
  [custom_components/apartment_lights_engine/rooms.py](custom_components/apartment_lights_engine/rooms.py)
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
