stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
	- /lab/user/_bmad-output/planning-artifacts/prd.md
	- /lab/user/_bmad-output/planning-artifacts/product-brief-user-2026-01-20.md
	- /lab/user/bricks/gws_eln/planning-artifacts/architecture.md
workflowType: 'architecture'
project_name: 'user'
user_name: 'Nour'
date: '2026-01-21'
version: '2.0'

# Architecture Decision Document v2

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

**VERSION 2 CHANGES:**
- Introduced `material_types` table (product catalog) separate from `material_lots` (physical inventory)
- Unified `material_lots` to handle both received lots and aliquots via `parent_lot_id` self-reference
- Removed `aliquots` table (functionality merged into `material_lots`)
- Removed `units` table (replaced with `unit_type` ENUM and base unit storage)
- Quantities stored in base units (L, kg, m, units) with application-side conversion
- Maintained separate tables for `samples` and `instruments` (no single inheritance table)

## Project Context Analysis

### Requirements Overview

	- Inventory: register materials (supplier, lot/batch, expiry, packaging), receive deliveries, view/edit metadata, simple location assignment and movement, location-filtered views.
	- Aliquoting: create single-level aliquots, view lineage, relabel without breaking lineage.
	- Usage & Decrement: log usage with quantity/unit, discard/remove with reason, confirmations and updated stock.
	- Note-Linked Actions: open inventory tool from Notes, perform actions in-note, link actions (product, lot, aliquot chain, instrument, quantities, units), view linked actions from Notes.
	- Samples & Instruments: register samples with storage, sample aliquots and lineage, reference instruments and simple maintenance notes.
	- Constellab Integration: access via existing auth/session, app-managed simple location list.
	- Activity & Correction: chronological activity log, misassignment correction with retained history, manual reorder flagging.
	- Units: support common units (volume, mass, length, count); stored in base units, displayed with smart conversion.

	- Performance: responsive Reflex pages; typical actions complete without long blocking; views refresh post-action (no realtime websockets in MVP).
	- Reliability: atomic actions; consistent inventory and note linkages; simple concurrency checks to avoid conflicting updates.
	- Security: session-based access inside Constellab; HTTPS transport.
	- Accessibility: practical keyboard navigation and readable contrast; pragmatic WCAG AA alignment for forms.
	- Integration: reuse Constellab auth/session; embed inventory tool in Notes; stable interfaces for note actions.

### Scale & Complexity

Single lab instance; ~100-500 material types; ~1000-5000 active lots/samples; ~10-50 concurrent users; modest transaction volume.

### Technical Constraints & Dependencies

- Constellab platform (Reflex, Peewee, MariaDB production / SQLite dev)
- Python 3.11+
- Existing auth/session model
- gws_core.Model and gws_reflex_main patterns

### Cross-Cutting Concerns Identified

- Concurrency: optimistic locking via version/updated_at
- Audit: activity log for all changes
- Lineage: parent-child relationships in material_lots and samples
- Unit conversion: centralized conversion logic in application layer

## Starter Template Evaluation

### Primary Technology Domain

Web application based on project requirements analysis

### Starter Options Considered

	- Integrates Constellab Reflex base and main utilities, uses rxconfig with environment API URL, MVC separation, and Peewee via gws_core.Model.
	- Clear example available internally and maintained; aligns with Constellab architecture and session model.

	- Provides a vanilla Reflex app; would require adapting to Constellab integration and gws_core/gws_reflex_main patterns.

	- Build-from-scratch; higher overhead; not recommended given strong internal template.

### Selected Starter: Constellab Reflex App scaffold (gws_project pattern)

**Rationale for Selection:** Seamless alignment with service/entity/ORM architecture, proven example, immediate compatibility with Constellab tooling and session model.

**Initialization Command:**

```bash
gws reflex run bricks/gws_eln/src/gws_eln/project_app/_project_app/rxconfig.py
```

**Architectural Decisions Provided by Starter:**

- Language & Runtime: Python (Reflex), Constellab environment integration.
- Styling Solution: Reflex component library; no external CSS framework by default.
- Build Tooling: Reflex build/dev server; sitemap plugin configured in rxconfig.
- Testing Framework: Backend/services via pytest; UI tests optional post-MVP.
- Code Organization: MVC via core (DB manager, model base), entity/service packages, and project_app for UI pages/states.
- Development Experience: Hot reload, environment-driven API URL, session reuse via Constellab.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- Data store: Constellab-managed relational DB (MariaDB in production and dev), via Peewee `DatabaseProxy`.
- ORM and model base: Peewee via `gws_core.Model`, `ModelWithUser` stamping user IDs.
- Authentication: reuse Constellab session; no separate auth.
- Unit handling: ENUM `unit_type` with base unit storage (L, kg, m, units); conversions in application layer.

**Important Decisions (Shape Architecture):**
- Data modeling: normalized entities (MaterialType, MaterialLot with lineage, Location, Sample, Instrument, Activity) without separate Units or Aliquots tables.
- Material catalog vs inventory: `material_types` for product definitions, `material_lots` for physical inventory and aliquots.
- Concurrency: optimistic check per item on update (version/updated_at guard), user confirmation on conflicts.
- API pattern: service-layer REST-like functions consumed by Reflex states; no GraphQL; internal endpoints.
- Frontend state: Reflex state classes per page/flow; route-based pages; no global complex state in MVP.

**Deferred Decisions (Post-MVP):**
- Role-based access control (RBAC) and permissions.
- Real-time updates via websockets.
- Hierarchical locations and mixture provenance entity.
- Alerts/reporting, dashboards, automated reordering rules.
- Unit conversion with user-defined factors.

### Data Architecture

#### Database Schema v2

**Core Entities:**

```
material_types (Product Catalog)
├── id (PK)
├── name (e.g., "Éthanol 99%")
├── supplier (e.g., "Sigma-Aldrich")
├── catalog_number (e.g., "E7023")
├── description
├── category (e.g., "Solvent", "Enzyme", "Buffer")
├── packaging_info
├── default_unit_type (ENUM: 'volume', 'mass', 'length', 'count')
├── storage_conditions
├── safety_info
├── is_active
├── created_by_id (FK), created_at
├── updated_by_id (FK), updated_at

material_lots (Physical Inventory: Received Lots + Aliquots)
├── id (PK)
├── material_type_id (FK → material_types)
├── parent_lot_id (FK → material_lots, NULL if received lot)
├── lot_number (supplier lot, NULL for aliquots)
├── batch_number (NULL for aliquots)
├── label (aliquot label, NULL for received lots)
├── received_date (NULL for aliquots)
├── expiry_date
├── initial_quantity (for received lots)
├── quantity (DECIMAL(20,12) - in base unit)
├── unit_type (ENUM: 'volume', 'mass', 'length', 'count')
├── location_id (FK → locations)
├── status (ENUM: 'active', 'depleted', 'expired', 'discarded')
├── qc_status (ENUM: 'pending', 'passed', 'failed')
├── generation (0 for received lot, 1+ for aliquots)
├── notes
├── created_by_id (FK), created_at
├── updated_by_id (FK), updated_at
├── version (for optimistic locking)

samples (Biological/Experimental Samples)
├── id (PK)
├── name
├── sample_type
├── description
├── source
├── parent_sample_id (FK → samples, NULL if original)
├── quantity (DECIMAL(20,12) - in base unit)
├── unit_type (ENUM: 'volume', 'mass', 'length', 'count')
├── location_id (FK → locations)
├── status (ENUM: 'active', 'depleted', 'discarded')
├── storage_conditions
├── generation (0 for original, 1+ for aliquots)
├── created_by_id (FK), created_at
├── updated_by_id (FK), updated_at
├── version

instruments (Lab Equipment)
├── id (PK)
├── name
├── model
├── serial_number
├── description
├── location_id (FK → locations)
├── status (ENUM: 'operational', 'maintenance', 'out_of_service')
├── last_maintenance
├── maintenance_notes
├── created_by_id (FK), created_at
├── updated_by_id (FK), updated_at

locations (Storage Locations)
├── id (PK)
├── name
├── code
├── description
├── location_type
├── is_active
├── created_by_id (FK), created_at
├── updated_by_id (FK), updated_at

activities (Audit Log)
├── id (PK)
├── activity_type (ENUM: 'receive', 'move', 'use', 'discard', 'aliquot', 'relabel', 'correct')
├── entity_type (ENUM: 'material_lot', 'sample', 'instrument')
├── entity_id (references id in respective table)
├── related_entity_id (for lineage, e.g., child aliquot)
├── quantity (DECIMAL(20,12), NULL for non-quantity actions)
├── unit_type (ENUM, NULL for non-quantity actions)
├── from_location_id (FK → locations, NULL if not move)
├── to_location_id (FK → locations, NULL if not move)
├── reason
├── notes
├── note_id (Constellab Note link)
├── instrument_id (FK → instruments, if action involves instrument)
├── correction_flag (BOOLEAN)
├── corrected_activity_id (FK → activities, if this corrects another)
├── performed_by_id (FK)
├── performed_at
├── metadata (JSON)
```

**Relationships:**
- material_types 1:N material_lots
- material_lots 1:N material_lots (parent_lot_id self-reference for lineage)
- samples 1:N samples (parent_sample_id self-reference for lineage)
- locations 1:N material_lots, samples, instruments
- activities references material_lots, samples, instruments via entity_type/entity_id

**Indices:**
```sql
CREATE INDEX idx_material_lots_type ON material_lots(material_type_id);
CREATE INDEX idx_material_lots_parent ON material_lots(parent_lot_id);
CREATE INDEX idx_material_lots_location ON material_lots(location_id);
CREATE INDEX idx_material_lots_status ON material_lots(status);
CREATE INDEX idx_material_lots_lot_number ON material_lots(lot_number);

CREATE INDEX idx_samples_parent ON samples(parent_sample_id);
CREATE INDEX idx_samples_location ON samples(location_id);

CREATE INDEX idx_activities_entity ON activities(entity_type, entity_id);
CREATE INDEX idx_activities_performed_at ON activities(performed_at DESC);
CREATE INDEX idx_activities_type ON activities(activity_type);
CREATE INDEX idx_activities_note ON activities(note_id);
```

#### Base Unit Storage Strategy

**Principle:** All quantities stored in base SI/standard units; conversions handled at application layer.

**Base Units:**
- Volume: Liters (L)
- Mass: Kilograms (kg)
- Length: Meters (m)
- Count: units (dimensionless)

**Storage:**
- Use DECIMAL(20,12) for high precision
- Store unit_type as ENUM
- No separate units table

**Conversion Logic:**
- Centralized in `utils/units.py`
- Conversion on input (user → base unit)
- Conversion on display (base unit → user-friendly unit)
- Example: 500 mL input → 0.5 L stored → display as "500 mL" if < 1 L

**Example Conversions:**
```python
# Volume
1 L = 1
1 mL = 0.001 L
1 µL = 0.000001 L

# Mass
1 kg = 1
1 g = 0.001 kg
1 mg = 0.000001 kg
1 µg = 0.000000001 kg

# Length
1 m = 1
1 cm = 0.01 m
1 mm = 0.001 m

# Count
1 unit = 1
```

#### Data Modeling Details

- Database: MariaDB (Constellab production and development environments) behind Peewee `DatabaseProxy` and `ElnDbManager`-style manager.
- Modeling: normalized tables with foreign keys; lineage tracked via parent-child self-references in material_lots and samples; activity log table for movements and corrections.
- Validation: service-layer input validation (quantities/units presence, non-negative stock, location existence, unit_type consistency) before model operations.
- Migrations: migration scripts aligned with `gws_project` pattern (versioned migration modules); schema evolution tracked in brick.
- Caching: none for MVP; rely on DB queries; consider simple in-memory caching for static lists (locations, material_types) if needed later.

### Authentication & Security

- Authentication & User Management: **Completely managed by Constellab platform**. App trusts inbound session and user context via `CurrentUserService`. No user management, authentication, or authorization logic in ELN.
- Security middleware: rely on Constellab; enforce HTTPS; sanitize inputs at service layer.
- Data encryption: at-rest handled by Constellab DB; in-transit via HTTPS.
- API security: internal-only endpoints scoped to Constellab; no public exposure.

### API & Communication Patterns

- Design: REST-like service methods exposed through Constellab integration; no GraphQL.
- Documentation: lightweight docstrings and README usage; internal team context.
- Error handling: standardized service exceptions mapped to user-facing messages; confirmations on stock changes.
- Rate limiting: not required in single lab MVP.
- Inter-service communication: none external; integration within Constellab Notes and reflex app.

### Frontend Architecture

- State management: Reflex `State` classes per page/feature; actions trigger service calls and refresh views.
- Components: reusable form components for quantity/unit input with conversion, location picker, lineage viewer; page components for inventory, note-linked tool.
- Routing: route-per-page via `@rx.page`; index lists inventory grouped by material_type; dedicated pages for detail and note tool entry.
- Performance: avoid heavy client state; server roundtrips for actions; no websockets in MVP.
- Bundle: default Reflex bundling; defer optimization until needed.

### Infrastructure & Deployment

- Hosting: Constellab-managed; no custom deploy logic.
- CI/CD: Constellab pipeline standards; tests for services when added.
- Environment config: `GWS_REFLEX_API_URL` required by `rxconfig.py`; brick `settings.json` for dependencies.
- Monitoring/logging: Constellab logs; activity log table for user-facing audit.
- Scaling: single lab instance; vertical scaling sufficient.

### Decision Impact Analysis

**Implementation Sequence:**
1. Define entity schemas (MaterialType, MaterialLot, Location, Sample, Instrument, Activity).
2. Implement unit conversion utilities in `utils/units.py`.
3. Implement service-layer operations (receive/add material_lots, move, aliquot via parent_lot_id, use/decrement, note-linkage hooks).
4. Wire Reflex states/pages to call services and refresh views with display conversions.
5. Add concurrency checks and user confirmations on updates.
6. Populate initial material_types, locations; finalize activity logging.

**Cross-Component Dependencies:**
- Lineage touches material_lots (via parent_lot_id) and samples (via parent_sample_id); activity log depends on all action services.
- Unit conversion utilities used by all services and UI components dealing with quantities.
- Location list used across all inventory views.
- Concurrency checks rely on model timestamps/versions and service enforcement.

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Critical Conflict Points Identified:** 20+ areas where AI agents could make different choices (naming, structure, format, communication, process)

### Naming Patterns

**Database Naming Conventions:**
- Tables: snake_case plural (e.g., `material_types`, `material_lots`, `locations`, `samples`, `instruments`, `activities`).
- Columns: snake_case (e.g., `created_by_id`, `updated_at`, `parent_lot_id`, `unit_type`).
- Foreign keys: `<entity>_id` (e.g., `material_type_id`, `location_id`, `parent_lot_id`).
- Indices: `idx_<table>_<column>` (e.g., `idx_material_lots_type`, `idx_samples_parent`).

**API Naming Conventions:**
- REST endpoints: plural nouns (e.g., `/material_types`, `/material_lots`, `/samples`, `/locations`).
- Route params: `/:id` (numeric/UUID) with lowercase names (e.g., `/material_lots/:id`).
- Query params: snake_case (e.g., `location_id`, `parent_lot_id`, `material_type_id`).
- Headers: standard plus `X-Constellab-*` when needed.

**Code Naming Conventions:**
- Components: PascalCase (e.g., `InventoryList`, `LineageViewer`, `QuantityInput`).
- Files: snake_case for Python modules (e.g., `material_lot_service.py`, `unit_converter.py`), consistent within Reflex.
- Functions/variables: snake_case in Python (e.g., `get_material_lots`, `to_base_unit`, `current_user_id`).
- Constants: UPPER_SNAKE_CASE (e.g., `BASE_UNITS`, `CONVERSION_FACTORS`).

### Structure Patterns

**Project Organization:**
- **Domain-driven directories**: Each domain (`materials/`, `samples/`, `instruments/`, `locations/`, `activities/`) contains its models and services together.
- Core infrastructure: `core/` for DB manager and base models.
- Frontend: `project_app/` for Reflex UI.
- Shared utilities: `utils/` for conversion logic, helpers.
- Tests: mirror domain structure under `tests/` (e.g., `tests/materials/`, `tests/samples/`).
- Pattern: `<domain>/<entity>.py` (model) + `<domain>/<entity>_service.py` (service) co-located.

**File Structure Patterns:**
- Config: `rxconfig.py` in `project_app/_project_app/`.
- Static assets: `assets/` under app.
- Docs: README at brick root; dev notes under `planning-artifacts/` or `docs/`.
- Environment: `.env` managed by Constellab; app reads `GWS_REFLEX_API_URL` only.

### Format Patterns

**API Response Formats:**
- Success: direct payload `{data: <payload>}` consistently for services.
- Errors: `{error: {code, message}}` with optional `details`.
- Dates: ISO-8601 strings in JSON; UTC.
- Quantities: always include `quantity`, `unit` (display), and optionally `quantity_base`, `unit_type` for debugging.

**Data Exchange Formats:**
- JSON fields: snake_case.
- Booleans: true/false.
- Nulls: explicit `null` where applicable; avoid sentinel values.
- Single items: object; lists: arrays.
- Unit display: `{quantity: 500, unit: "mL"}` (user-friendly) vs storage `{quantity: 0.5, unit_type: "volume"}`.

### Communication Patterns

**Event System Patterns:**
- Event names: dot.notation (e.g., `inventory.material_lot.used`, `inventory.aliquot.created`).
- Payload: `{id, ts, actor_id, context, data}` with version `v1`.
- Versioning: include `schema_version: 1` in payload.
- Async handling: queued if later adopted; MVP synchronous logging only.

**State Management Patterns:**
- Reflex state updates: immutable-by-convention (return new derived data) or direct methods per Reflex; ensure predictable refresh after service calls.
- Actions: verb-noun names (e.g., `use_material_lot`, `move_sample`, `create_aliquot`).
- Selectors: helper methods in state classes for derived views (e.g., total quantity per material_type).
- Organization: state per page/feature.

### Process Patterns

**Error Handling Patterns:**
- Global: map service exceptions to user messages; log technical detail separately.
- Error boundary: page-level messages; form-level inline validation.
- Distinguish: operation failure vs validation error.
- Unit conversion errors: catch and display clear messages ("Invalid unit 'xyz' for volume").

**Loading State Patterns:**
- Naming: `is_loading_<action>` flags.
- Scope: local to page/state; no global spinner.
- Persistence: short-lived; clear on completion/failure.
- UI: disable submit during loading; show concise progress.

### Enforcement Guidelines

**All AI Agents MUST:**
- Use snake_case plural table names and snake_case JSON fields.
- Follow feature-based folder structure mirroring `gws_project`.
- Return errors in `{error: {code, message}}` format and dates as ISO-8601 UTC.
- Store quantities in base units (L, kg, m, units) using DECIMAL(20,12).
- Use `unit_type` ENUM; perform conversions in application layer via `utils/units.py`.

**Pattern Enforcement:**
- Code reviews against this document.
- Linting/formatting via project standards; validate endpoints in integration tests.
- Track violations in README or `docs/patterns.md` with resolution notes.

### Pattern Examples

**Good Examples:**
- Endpoint: `POST /material_lots/{id}/use` → body `{quantity: 10, unit: "mL"}` → response `{data: {remaining_quantity: 490, unit: "mL", quantity_base: 0.49, unit_type: "volume"}}`.
- DB: table `material_lots` with columns `id`, `material_type_id`, `quantity` (DECIMAL), `unit_type` (ENUM), `parent_lot_id`.
- Service call: `to_base_unit(500, "mL", "volume")` returns `Decimal('0.5')`.

**Anti-Patterns:**
- Mixed casing in JSON (`userId`, `created_at`) within same payload.
- Singular table names (`material_type`) alongside plural (`locations`).
- Storing quantities in user-selected units (e.g., "500 mL" as string).
- Using FLOAT for quantities (precision loss).

## Project Structure & Boundaries

### Complete Project Directory Structure

**Domain-Driven Organization:** Project is structured by domain/subdomain rather than by layer (entity/service). Each domain contains its models, services, and business logic together.

```
bricks/gws_eln/
├── README.md
├── settings.json
├── src/
│   └── gws_eln/
│       ├── __init__.py
│       ├── core/
│       │   ├── eln_db_manager.py
│       │   └── model_with_user.py
│       ├── materials/
│       │   ├── __init__.py
│       │   ├── material_type.py          # Entity/Model
│       │   ├── material_lot.py           # Entity/Model
│       │   ├── material_type_service.py  # Service
│       │   └── material_lot_service.py   # Service
│       ├── samples/
│       │   ├── __init__.py
│       │   ├── sample.py                 # Entity/Model
│       │   └── sample_service.py         # Service
│       ├── instruments/
│       │   ├── __init__.py
│       │   ├── instrument.py             # Entity/Model
│       │   └── instrument_service.py     # Service
│       ├── locations/
│       │   ├── __init__.py
│       │   ├── location.py               # Entity/Model
│       │   └── location_service.py       # Service
│       ├── activities/
│       │   ├── __init__.py
│       │   ├── activity.py               # Entity/Model
│       │   └── activity_service.py       # Service
│       ├── utils/
│       │   ├── units.py
│       │   └── validators.py
│       ├── project_app/
│       │   └── _project_app/
│       │       ├── assets/
│       │       ├── dev_config.json
│       │       ├── rxconfig.py
│       │       └── project_app/
│       │           ├── __init__.py
│       │           ├── common/
│       │           │   ├── quantity_input.py
│       │           │   ├── lineage_viewer.py
│       │           │   └── location_picker.py
│       │           ├── inventory/
│       │           │   ├── inventory_page.py
│       │           │   └── inventory_state.py
│       │           ├── material_detail/
│       │           │   ├── material_detail_page.py
│       │           │   └── material_detail_state.py
│       │           ├── note_tool/
│       │           │   ├── note_tool_page.py
│       │           │   └── note_tool_state.py
│       │           └── project_app.py
│       ├── migrations/
│       │   ├── migration_0001_initial.py
│       │   └── migration_0002_seed_data.py
│       └── planning-artifacts/
│           ├── architecture.md
│           ├── architecture-v2.md
│           └── database-schema-v2.md
├── tests/
│   ├── materials/
│   │   ├── test_material_type_service.py
│   │   └── test_material_lot_service.py
│   ├── samples/
│   │   └── test_sample_service.py
│   ├── instruments/
│   │   └── test_instrument_service.py
│   ├── locations/
│   │   └── test_location_service.py
│   ├── activities/
│   │   └── test_activity_service.py
│   ├── utils/
│   │   └── test_unit_converter.py
│   └── fixtures/
│       └── sample_data.json
└── .gitignore
```

### Architectural Boundaries

**API Boundaries:**
- Internal service endpoints exposed via Constellab integration; no public APIs.
- Authentication boundary handled by Constellab session; services assume `CurrentUserService` context.
- Data access boundary via Peewee models and `ElnDbManager`.

**Component Boundaries:**
- Reflex pages call state methods; states call services; services call models.
- Shared UI components under `common/`; feature pages under `inventory/`, `material_detail/`, `note_tool/`.
- Unit conversion logic isolated in `utils/units.py`; used by services and UI.

**Service Boundaries:**
- Each domain has dedicated models and services co-located (e.g., `materials/` contains MaterialType, MaterialLot, and their services).
- Cross-domain operations orchestrated via activity service in `activities/` domain.
- Note-linked actions integrate through `note_tool_state` invoking corresponding domain services.
- Clear domain boundaries: `materials/` (catalog + inventory), `samples/` (biological specimens), `instruments/` (equipment), `locations/` (storage), `activities/` (audit log).

**Data Boundaries:**
- Entities encapsulate DB schema and relations; lineage defined via `parent_lot_id` in MaterialLot and `parent_sample_id` in Sample.
- Locations are global catalogs used across features.
- Activities table polymorphically references material_lots, samples, instruments via entity_type/entity_id.

### Requirements to Structure Mapping

**Feature/Epic Mapping:**
- Inventory Management (FR1–FR7, FR12–FR14): `materials/` domain (material_type.py, material_lot.py, services), `locations/` domain, `project_app/inventory/*`.
- Aliquoting & Lineage (FR8–FR11): `materials/material_lot.py` with `parent_lot_id`, `materials/material_lot_service.py` (aliquot creation), lineage viewer in `project_app/common/lineage_viewer.py`.
- Note-Linked Actions (FR15–FR18): `project_app/note_tool/*` states/pages with calls to domain services; activity linkage via `activities/activity_service.py`.
- Samples & Instruments (FR19–FR22): `samples/` domain (sample.py, sample_service.py), `instruments/` domain (instrument.py, instrument_service.py).
- Activity & Correction (FR25–FR27): `activities/` domain (activity.py, activity_service.py), inventory pages display activity history.
- Units & Consistency (FR28–FR29): `utils/units.py` for conversion logic; used by forms, validations, and display components.

**Cross-Cutting Concerns:**
- Concurrency checks and confirmations implemented in services; surfaced in states/pages.
- Audit views read from `activity` entity; used across inventory and note tool.
- Unit conversion centralized; consistency enforced via base unit storage and utility functions.

### Integration Points

**Internal Communication:**
- Reflex state → service (function calls) → model (ORM) → DB; responses rehydrate state and re-render.
- Unit conversions: user input → `to_base_unit()` → storage; storage → `from_base_unit()` → display.

**External Integrations:**
- Constellab Notes integration via state hooks; actions create links using provided Constellab APIs.

**Data Flow:**
- Material catalog (material_types) → material lots (received) → material lots (aliquots via parent_lot_id).
- Material lots and samples flow through services for receive/use/move/aliquot; activity records appended; lineage updated consistently.
- Quantities converted on input/output; stored uniformly in base units.

### File Organization Patterns

**Domain-Driven Organization Benefits:**
- **Cohesion**: Related models and services co-located (e.g., all material logic in `materials/`).
- **Discoverability**: Easy to find all code related to a domain.
- **Bounded Contexts**: Clear boundaries between domains reduce coupling.
- **Scalability**: Easy to add new domains or split domains as they grow.
- **Team Collaboration**: Teams can own specific domains without conflicts.

**Configuration Files:**
- `rxconfig.py` under app; `settings.json` for brick dependencies; `.env` handled by Constellab.

**Source Organization:**
- **Domain-based** with clear boundaries; each domain directory (`materials/`, `samples/`, `instruments/`, `locations/`, `activities/`) contains related models and services.
- `core/` for DB manager and base model classes.
- `utils/` for shared logic like unit conversion.
- `project_app/` for UI layer (Reflex pages/states).

**Test Organization:**
- Tests mirror domain structure: `tests/materials/`, `tests/samples/`, `tests/instruments/`, `tests/locations/`, `tests/activities/`.
- Unit tests per service co-located with domain tests.
- Unit tests for conversion utilities in `tests/utils/`.
- Fixtures in `tests/fixtures`; integration tests optional post-MVP.

**Asset Organization:**
- UI assets under `assets/`; no external static hosting needed.

### Development Workflow Integration

**Development Server Structure:**
- Run via `gws reflex run` on `rxconfig.py`; hot reload keeps state consistent with services.

**Build Process Structure:**
- Reflex build output managed by Constellab tooling; project structure supports clear feature boundaries.

**Deployment Structure:**
- Constellab-managed deployment; ensure environment variable `GWS_REFLEX_API_URL` set.

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**
- Technology choices (Reflex, Peewee, MariaDB, Constellab session) are compatible and align with internal patterns.
- Patterns (naming, structure, formats, unit handling) support the chosen stack; no contradictions identified.
- Unit conversion strategy (base unit storage, application-layer conversion) is consistent with data architecture.

**Pattern Consistency:**
- Naming conventions and response formats are consistent and enforceable.
- Structure patterns align with feature-based organization and Constellab integration.
- Unit handling patterns centralized and testable.

**Structure Alignment:**
- Directory tree supports decisions, with clear boundaries and integration points.
- Project structure enables implementation of patterns, services, and unit conversion utilities.

### Requirements Coverage Validation ✅

**Feature Coverage:**
- Inventory, Aliquoting & Lineage (via parent_lot_id), Note-Linked Actions, Samples & Instruments, Activity & Correction, Units (via unit_type and utils) are all mapped to specific entities, services, and pages/states.

**Functional Requirements Coverage:**
- All FRs in PRD are architecturally supported via entities and services with Reflex pages/states.
- Unit requirements met with base unit storage and smart conversion/display.

**Non-Functional Requirements Coverage:**
- Performance: page-refresh model with responsive actions; no websockets in MVP; DECIMAL precision for calculations.
- Security: Constellab session reuse and HTTPS; internal-only endpoints.
- Reliability: atomic actions, simple concurrency checks, and precise quantity handling.
- Accessibility: Reflex components support pragmatic WCAG AA alignment.

### Implementation Readiness Validation ✅

**Decision Completeness:**
- Critical decisions documented; MariaDB choice, ORM patterns, and unit handling specified.
- Patterns comprehensive; consistency rules defined with examples.

**Structure Completeness:**
- Directory structure complete and specific; integration points and boundaries documented.
- Unit conversion utilities planned with clear module location.

**Pattern Completeness:**
- Conflict points addressed across naming, structure, formats, communication, process, and unit handling.

### Gap Analysis Results

**Critical Gaps:**
- None blocking MVP implementation.

**Important Gaps:**
- Define concrete migration scripts and versioning standards in `migrations/` before first release.
- Confirm initial material_types catalog and location list seed data.
- Document unit conversion examples in `utils/units.py` docstrings.

**Nice-to-Have Gaps:**
- Add integration tests for note-linked actions.
- Expand activity audit views post-MVP.
- Consider user-defined unit conversions post-MVP.

### Validation Issues Addressed

- Database selection updated to MariaDB and reflected across decisions.
- Unified material_lots table with parent_lot_id for aliquot lineage.
- Removed separate units and aliquots tables; unit handling via ENUM and conversion utilities.

### Architecture Completeness Checklist

**✅ Requirements Analysis**
- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed
- [x] Technical constraints identified
- [x] Cross-cutting concerns mapped

**✅ Architectural Decisions**
- [x] Critical decisions documented with versions
- [x] Technology stack fully specified
- [x] Integration patterns defined
- [x] Performance considerations addressed
- [x] Unit handling strategy defined

**✅ Implementation Patterns**
- [x] Naming conventions established
- [x] Structure patterns defined
- [x] Communication patterns specified
- [x] Process patterns documented
- [x] Unit conversion patterns specified

**✅ Project Structure**
- [x] Complete directory structure defined
- [x] Component boundaries established
- [x] Integration points mapped
- [x] Requirements to structure mapping complete

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** high based on validation results and simplified unit handling

**Key Strengths:**
- Clear separation between material catalog (material_types) and physical inventory (material_lots).
- Unified material_lots table handles received lots and aliquots via parent_lot_id, simplifying lineage.
- No separate units table; base unit storage with application-layer conversion is pragmatic and performant.
- Strong Constellab alignment for session and deployment.
- Enforced patterns avoiding agent inconsistencies.

**Areas for Future Enhancement:**
- RBAC, dashboards, and hierarchical locations post-MVP.
- User-defined unit conversions if non-standard units needed.

### Implementation Handoff

**AI Agent Guidelines:**
- Follow architectural decisions exactly.
- Apply implementation patterns consistently.
- Respect project structure and boundaries.
- Use this document for all architectural questions.
- Implement unit conversions via `utils/units.py` with tests.

**First Implementation Priority:**
```bash
gws reflex run bricks/gws_eln/src/gws_eln/project_app/_project_app/rxconfig.py
```

## Architecture Completion Summary

### Workflow Completion

**Architecture Decision Workflow:** COMPLETED ✅
**Version:** 2.0
**Total Steps Completed:** 8
**Date Completed:** 2026-01-21
**Document Location:** /lab/user/bricks/gws_eln/planning-artifacts/architecture-v2.md

### Final Architecture Deliverables

**📋 Complete Architecture Document v2**

- All architectural decisions documented with specific versions
- Simplified data model: material_types + material_lots (with lineage), samples, instruments, activities, locations
- No separate aliquots or units tables
- Base unit storage (L, kg, m, units) with application-layer conversion
- Implementation patterns ensuring AI agent consistency
- Complete project structure with all files and directories
- Requirements to architecture mapping
- Validation confirming coherence and completeness

**🏗️ Implementation Ready Foundation**

- 20+ architectural decisions made
- Comprehensive implementation patterns defined
- 6 core entities specified (MaterialType, MaterialLot, Sample, Instrument, Location, Activity)
- All PRD requirements supported with simplified unit handling

**📚 AI Agent Implementation Guide**

- Technology stack with verified versions
- Consistency rules that prevent implementation conflicts
- Project structure with clear boundaries
- Integration patterns and communication standards
- Unit conversion utilities specification

### Implementation Handoff

**For AI Agents:**
This architecture document v2 is your complete guide for implementing gws_eln. Follow all decisions, patterns, and structures exactly as documented.

**First Implementation Priority:**
gws reflex run bricks/gws_eln/src/gws_eln/project_app/_project_app/rxconfig.py

**Development Sequence:**

1. Initialize project using documented starter template
2. Set up development environment per architecture
3. Implement core architectural foundations (entities: material_type, material_lot, location, sample, instrument, activity)
4. Implement unit conversion utilities (`utils/units.py`) with tests
5. Build services using entities and conversion utilities
6. Build Reflex pages/states following established patterns
7. Maintain consistency with documented rules

### Quality Assurance Checklist

**✅ Architecture Coherence**

- [x] All decisions work together without conflicts
- [x] Technology choices are compatible
- [x] Patterns support the architectural decisions
- [x] Structure aligns with all choices
- [x] Unit handling is consistent across layers

**✅ Requirements Coverage**

- [x] All functional requirements are supported
- [x] All non-functional requirements are addressed
- [x] Cross-cutting concerns are handled
- [x] Integration points are defined
- [x] Unit conversion requirements met

**✅ Implementation Readiness**

- [x] Decisions are specific and actionable
- [x] Patterns prevent agent conflicts
- [x] Structure is complete and unambiguous
- [x] Examples are provided for clarity
- [x] Unit conversion logic is specified

### Project Success Factors

**🎯 Clear Decision Framework**
Collaborative decisions with clear rationale ensure shared understanding.

**🔧 Consistency Guarantee**
Patterns and rules ensure agents produce compatible code.

**📋 Complete Coverage**
Requirements are mapped from business needs to technical implementation.

**🏗️ Solid Foundation**
Starter and patterns provide production-ready baseline.

**🔢 Simplified Unit Handling**
Base unit storage with application-layer conversion balances simplicity and flexibility.

---

**Architecture Status:** READY FOR IMPLEMENTATION ✅

**Next Phase:** Begin implementation using the architectural decisions and patterns documented herein.

**Document Maintenance:** Update this architecture when major technical decisions are made during implementation.

---

## Appendix: Key Architectural Changes v1 → v2

### Major Changes

1. **Material Catalog Separation**
   - v1: Single `materials` table with lot_number
   - v2: `material_types` (catalog) + `material_lots` (inventory)
   - Benefit: No duplication; easier reordering; cleaner lot tracking

2. **Aliquot Handling**
   - v1: Separate `aliquots` table
   - v2: Unified in `material_lots` via `parent_lot_id` self-reference
   - Benefit: Simpler queries; consistent operations; same interface for lots and aliquots

3. **Unit Storage**
   - v1: Separate `units` table with foreign keys
   - v2: `unit_type` ENUM + base unit storage (L, kg, m, units) + `utils/units.py` for conversion
   - Benefit: No joins for units; direct calculations; smart display conversion

4. **Entity Structure**
   - v1: materials, aliquots, samples, instruments, activities, units, locations
   - v2: material_types, material_lots, samples, instruments, activities, locations
   - Result: 6 core entities instead of 7; clearer separation of concerns

### Impact on Implementation

**Services:**
- `MaterialTypeService`: manage product catalog (in `materials/` domain)
- `MaterialLotService`: manage physical inventory (lots + aliquots, in `materials/` domain)
- No `AliquotService` or `UnitService` needed

**Utilities:**
- New `utils/units.py` module for conversion logic
- Centralized, testable, reusable across all quantity operations

**Database:**
- MariaDB in both production AND development (Constellab environment)
- Fewer tables, fewer joins
- Lineage via self-reference (more SQL-standard pattern)
- Base unit storage enables direct aggregation queries

**Project Structure:**
- **Domain-driven organization** instead of layered (entity/service separation)
- Each domain is self-contained with models + services
- Benefits: better cohesion, discoverability, and team collaboration

**Authentication:**
- **Completely managed by Constellab** - no user management in ELN
- App relies on Constellab session and `CurrentUserService`

**UI:**
- Quantity inputs use conversion utilities
- Display logic converts base units to user-friendly units
- Inventory grouped by material_type with expandable lots

### Migration Path (if v1 existed)

```sql
-- Conceptual migration from v1 to v2
-- 1. Create material_types from unique materials
INSERT INTO material_types (name, supplier, catalog_number, ...)
SELECT DISTINCT name, supplier, catalog_number, ...
FROM materials;

-- 2. Migrate materials to material_lots
INSERT INTO material_lots (material_type_id, lot_number, quantity, unit_type, ...)
SELECT mt.id, m.lot_number, m.quantity, 'volume', ...
FROM materials m
JOIN material_types mt ON m.name = mt.name AND m.supplier = mt.supplier;

-- 3. Migrate aliquots to material_lots with parent_lot_id
INSERT INTO material_lots (material_type_id, parent_lot_id, label, quantity, unit_type, ...)
SELECT ml.material_type_id, ml.id, a.label, a.quantity, ml.unit_type, ...
FROM aliquots a
JOIN material_lots ml ON a.material_id = ml.id;

-- 4. Convert quantities to base units
UPDATE material_lots SET quantity = quantity * 0.001 WHERE unit_type = 'volume' AND <stored as mL>;
-- Repeat for all unit conversions

-- 5. Drop old tables
DROP TABLE aliquots;
DROP TABLE units;
DROP TABLE materials;
```

---

**End of Architecture Document v2**
