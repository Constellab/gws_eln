# gws_eln Reflex App

This brick provides a minimal Reflex SPA embedded inside Constellab, using Peewee ORM and a simple MVC stack.

## Dev Run

Prereqs: Constellab environment with `gws_reflex_base` and `gws_reflex_main` available.

1. Export the API URL used by Reflex:

```bash
export GWS_REFLEX_API_URL="https://constellab.local/api"
```

2. Run the Reflex app in dev mode:

```bash
gws reflex run bricks/gws_eln/src/gws_eln/project_app/_project_app/rxconfig.py
```

The index page should render "Constellab ELN".

## Architecture Notes

- ORM: Peewee via `gws_core.Model` with `ModelWithUser` stamping user IDs.
- DB Manager: `ElnDbManager` mirrors `ProjectDbManager` (see gws_project).
- Reflex App: `rxconfig.py` pattern mirrors gws_project; uses `register_gws_reflex_app()`.
- Deployment/Auth: handled by Constellab; no custom auth code needed.
