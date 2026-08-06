# Dependencies

This document lists the dependencies of the `gws_eln` brick: the Constellab bricks it requires.

## Constellab bricks

Declared in [`settings.json`](./settings.json):

| Brick | Version |
|---|---|
| `gws_core` | >= 0.23.9 |

`settings.json` declares no pip or git packages.

## Known issue found while documenting

`gws_reflex_base` and `gws_reflex_main` are required at runtime (imported across `eln_app/_eln_app/`, e.g. `eln_app/_eln_app/rxconfig.py`) and are explicitly listed as prerequisites in the brick's original dev-run instructions, but **neither is declared in `settings.json`**. Worth adding them to `environment.bricks` so the dependency is installed automatically rather than assumed to already be present in the environment.
