# HAOS Deployment

## Goal

Deploy `apartment_lights_engine` to a Home Assistant OS installation as a real
custom integration, instead of keeping the logic only in runtime-created
scripts and automations.

## Manual install on HAOS

1. Get access to the HA config directory `/config`.
2. Copy this directory:

   - `custom_components/apartment_lights_engine`

   into:

   - `/config/custom_components/apartment_lights_engine`

3. Restart Home Assistant.
4. Open:

   - `Settings -> Devices & Services -> Add Integration`

5. Add:

   - `Apartment Lights Engine`

After the config entry exists, the integration registers the service:

- `apartment_lights_engine.evaluate_room`

## HACS install on HAOS

1. Publish this bundle as a dedicated GitHub repository.
2. In HACS add it as:

   - `Custom repositories`
   - category: `Integration`

3. Install from HACS.
4. Restart Home Assistant.
5. Add the integration from `Devices & Services`.

## Practical file access on HAOS

Common ways to place files into `/config` on HAOS:

- Studio Code Server add-on
- File Editor add-on
- Terminal & SSH add-on
- SMB / network share access

## Why this is better than runtime wrappers

- proper backend service with response payload
- easier testing and logging
- cleaner per-room wrappers
- less Jinja branching in automations
- better long-term reuse across rooms
