# Apartment Lights Engine v2

## Reference Freeze
Live salon behavior was frozen before the engine extraction and used as the
reference rollback point for:

- `automation.auto_lights_livingroom`
- `automation.livingroom_main_restore_window_arm`
- livingroom light entities, thresholds and restore-window helpers

## Goal
Extract the salon light logic into one deterministic decision engine that:

- takes one immutable snapshot of room state
- takes one explicit trigger cause
- returns one action plan
- executes side effects only after the plan is fully computed

The engine is designed to be reused in other rooms by only changing entity mappings.

## Deliberate Scope of v2
Included:

- `main_on`
- `main_off`
- `lux_bright_stable`
- `lux_dark_stable`
- `lux_changed`
- `motion_on`
- `motion_off`
- `door_open`
- `door_grace_finished`
- `auto_toggle`
- `thresholds_changed`
- quick return after no-presence off
- no-presence room off inside the engine
- door-open grace window when presence does not confirm entry

Not included in v2:

- `sleep_mode`
- room-specific scene logic outside the light decision itself

Those remain separate concerns for now.

## Snapshot Inputs
Each decision is based on:

- `auto_enabled`
- `presence_on`
- `lux`
- `lux_on_threshold`
- `lux_off_threshold`
- `main_on`
- `ambient_on`
- `room_on`
- `neighbor_main_on`
- `restore_window_active`
- `door_grace_window_active`
- `seconds_since_main_off`
- `main_off_window_seconds`
- `cause`

## Rule Priority
The engine evaluates rules in this exact order.

1. `auto_disabled`
2. `motion_on` cancels `door_grace_window` after entry confirmation
3. `motion_off` turns room off and starts restore window if `main_on`
4. `main_on` syncs the cluster and clears pending timers when needed
5. `main_off` while occupied and dark turns on ambient
6. `door_grace_finished` turns room off if presence never arrived
7. `ambient_on + bright` turns ambient off
8. `restore_window_active + motion_on/door_open + dark` restores `main`
9. `lux_changed` shortly after main-off restores ambient
10. `lux_dark_stable` or dark `thresholds_changed` chooses `main` vs `ambient`
11. dark `motion_on/door_open/auto_toggle/thresholds_changed` chooses `main` vs `ambient` only if both are currently off
12. otherwise `noop`

## Decision Table
| Cause | Required state | Decision |
| --- | --- | --- |
| `motion_on` | `door_grace_window_active and room_on` | `cancel_door_grace_window` |
| `motion_off` | `main_on and room_on` | `start_restore_window + turn_room_off` |
| `motion_off` | `room_on and main_off` | `turn_room_off` |
| `main_on` | `ambient_on` | `turn_main_on + turn_ambient_off` |
| `main_on` | `restore_window_active or door_grace_window_active` | `turn_main_on + clear_pending_timers` |
| `main_off` | `presence_on and dark and ambient_off` | `turn_ambient_on` |
| `door_grace_finished` | `room_on and not presence_on` | `turn_room_off` |
| `lux_bright_stable` | `ambient_on` | `turn_ambient_off` |
| `thresholds_changed` | `ambient_on and bright` | `turn_ambient_off` |
| `motion_on` | `restore_window_active and dark and main_off` | `turn_main_on + cancel_restore_window` |
| `door_open` | `restore_window_active and dark and main_off and no presence` | `turn_main_on + cancel_restore_window + start_door_grace_window` |
| `lux_changed` | `presence_on and dark and main_off and ambient_off and recent_main_off` | `turn_ambient_on` |
| `lux_dark_stable` | `presence_on and dark and main_off and ambient_off` | `turn_main_on` if neighbor main on, else `turn_ambient_on` |
| `thresholds_changed` | `presence_on and dark and main_off and ambient_off` | `turn_main_on` if neighbor main on, else `turn_ambient_on` |
| `motion_on`, `door_open`, `auto_toggle` | `dark and room demand present and main_off and ambient_off` | `turn_main_on` if neighbor main on, else `turn_ambient_on` |
| `door_open` | `dark and no presence and main_off and ambient_off` | `turn_light_on + start_door_grace_window` |

## 2026-04-05 Regression Note
The first salon cutover exposed a concrete bug:

- quick return correctly restored `main`
- the next `motion_on` still matched the generic dark-entry rule
- because that rule did not require `main_off`, it could add `ambient`

The engine now requires both `main_off` and `ambient_off` before the generic
entry rule can turn anything on.

## Room-Specific Configuration
`livingroom`

- `main_state_entity`: `light.raspberry_pi_light_controller_main_livingroom_light`
- `main_action_entities`:
  - `light.raspberry_pi_light_controller_main_livingroom_light`
  - `light.livingroom_wled_main`
- `ambient_entity`: `light.lights_group_livingroom_ambient`
- `neighbor_main_entities`:
  - `light.raspberry_pi_light_controller_main_corridor_light`
  - `light.raspberry_pi_light_controller_main_kitchen_light`

`bedroom`

- `main_state_entity`: `light.raspberry_pi_light_controller_main_bedroom_light`
- `main_action_entities`:
  - `light.raspberry_pi_light_controller_main_bedroom_light`
  - `light.bedroom_wled_main`
- `ambient_entity`: `light.lights_group_bedroom_ambient`
- `neighbor_main_entities`:
  - `light.raspberry_pi_light_controller_main_corridor_light`

## Technical Reason For The Refactor
The failed salon run on `2026-04-05` showed the defect clearly:

- old automation first executed `light.turn_on light.livingroom_wled_main`
- only after that it evaluated `choose`
- this mutated light-group state before the main decision finished

The new engine explicitly forbids that pattern:

- snapshot first
- decision second
- side effects last
