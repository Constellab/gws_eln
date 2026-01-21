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

**📄 Quick Navigation:**
- **1-Page Summary**: [architecture-summary-v2.md](architecture-summary-v2.md) - Start here for quick reference
- **Database Schema**: [database-schema-v2.md](database-schema-v2.md) - Complete schema with all tables and relationships
- **Implementation Patterns**: [implementation-patterns.md](implementation-patterns.md) - Naming, structure, and format conventions
- **Project Structure**: [project-structure.md](project-structure.md) - Complete directory organization and domain boundaries
- **Development Sequence**: [development-sequence.md](development-sequence.md) - Step-by-step implementation guide with time estimates

_This document is the complete architecture reference. For focused information, use the modular documents above._

**VERSION 2 CHANGES:**
- Renamed: `material_types` → `materials` (product catalog), `material_lots` → `material_batches` (physical inventory)
- Added dedicated `suppliers` table with full CRUD operations
- **Unified data model: removed `samples` and `instruments` tables - everything managed via `materials` and `material_batches`**
- `materials.is_consumable` flag differentiates consumables (chemicals, reagents) from non-consumables (instruments, equipment)
- Simplified `materials`: added `is_consumable` flag; removed category, packaging_info, storage_conditions, safety_info, is_active
- Simplified `material_batches`: removed lot_number (kept batch_number only), received_date, initial_quantity, status, qc_status, generation, version
- Simplified `locations`: removed code, location_type, is_active fields
- Simplified `activities`: removed correction_flag, corrected_activity_id, performed_by_id, performed_at, metadata fields; removed 'correct' activity_type
- Separated activity types: 'consume' for consumables (decrements quantity), 'use' for non-consumables (reference only)
- Removed optimistic locking (version fields) - not needed for MVP
- Unified `material_batches` to handle both received batches and aliquots via `parent_batch_id` self-reference
- Removed `aliquots` table (functionality merged into `material_batches`)
- Removed `units` table (replaced with `unit_type` ENUM and base unit storage)
- Quantities stored in base units (L, kg, m, units) with application-side conversion
- Aliquots automatically inherit supplier_id from parent batch
- Standardized audit fields: all tables use `created_by_id`, `last_modified_by_id`, `created_at`, `last_modified_at`

## Project Context Analysis

### Requirements Overview

	- Inventory: register materials (consumable and non-consumable), supplier, batch, expiry; receive deliveries, view/edit metadata, simple location assignment and movement, location-filtered views.
	- Aliquoting: create multi-level aliquots, view lineage, relabel without breaking lineage.
	- Usage & Decrement: log 'consume' with quantity decrement for consumables, log 'use' as reference for non-consumables; discard/remove with reason, confirmations and updated stock.
	- Note-Linked Actions: open inventory tool from Notes, perform actions in-note, link actions (material, batch, aliquot chain, quantities, units), view linked actions from Notes.
	- Constellab Integration: access via existing auth/session, app-managed simple location list.
	- Activity Log: chronological activity log with full audit trail.
	- Units: support common units (volume, mass, length, count); stored in base units, displayed with smart conversion.

	- Performance: responsive Reflex pages; typical actions complete without long blocking; views refresh post-action (no realtime websockets in MVP).
	- Reliability: atomic actions; consistent inventory and note linkages; simple concurrency checks to avoid conflicting updates.
	- Security: session-based access inside Constellab; HTTPS transport.
	- Accessibility: practical keyboard navigation and readable contrast; pragmatic WCAG AA alignment for forms.
	- Integration: reuse Constellab auth/session; embed inventory tool in Notes; stable interfaces for note actions.

### Scale & Complexity

Single lab instance; ~100-500 materials (consumables + non-consumables); ~1000-5000 active batches; ~10-50 concurrent users; modest transaction volume.

### Technical Constraints & Dependencies

- Constellab platform (Reflex, Peewee, MariaDB production / SQLite dev)
- Python 3.11+
- Existing auth/session model
- gws_core.Model and gws_reflex_main patterns

### Cross-Cutting Concerns Identified

- Concurrency: simple timestamp checks via last_modified_at (no optimistic locking in MVP)
- Audit: activity log for all changes; standardized audit fields (created_by_id, last_modified_by_id, created_at, last_modified_at) on all tables
- Lineage: parent-child relationships in material_batches via parent_batch_id
- Unit conversion: centralized conversion logic in application layer
- Consumable vs non-consumable: differentiated behavior via materials.is_consumable flag

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

**CRITICAL: Follow gws_project Repository Pattern**
- **Backend structure**: Services and entities co-located by domain (as in gws_project)
- **Frontend structure**: Reflex application with pages and states (as in gws_project)
- **Reference repository**: `gws_project` contains the complete reference implementation for both backend and frontend patterns
- **Do NOT deviate** from gws_project structure without explicit justification

**Initialization Command:**

```bash
gws reflex run bricks/gws_eln/src/gws_eln/project_app/_project_app/rxconfig.py
```

**Architectural Decisions Provided by Starter:**

- Language & Runtime: Python (Reflex), Constellab environment integration.
- Styling Solution: Reflex component library; no external CSS framework by default.
- Build Tooling: Reflex build/dev server; sitemap plugin configured in rxconfig.
- Testing Framework: Backend/services via pytest; UI tests optional post-MVP.
- Code Organization: MVC via core (DB manager, model base), entity/service packages, and project_app for UI pages/states. **FOLLOW gws_project repository structure exactly** - it demonstrates the complete backend (services/entities) and frontend (Reflex app) pattern.
- Development Experience: Hot reload, environment-driven API URL, session reuse via Constellab.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- Data store: Constellab-managed relational DB (MariaDB in production and dev), via Peewee `DatabaseProxy`.
- ORM and model base: Peewee via `gws_core.Model`, `ModelWithUser` stamping user IDs.
- Authentication: reuse Constellab session; no separate auth.
- Unit handling: ENUM `unit_type` with base unit storage (L, kg, m, units); conversions in application layer.

**Important Decisions (Shape Architecture):**
- Data modeling: unified entities (Material, MaterialBatch with lineage, Supplier, Location, Activity) - no separate Samples, Instruments, Units, or Aliquots tables.
- Material catalog vs inventory: `materials` for product definitions (with is_consumable flag), `material_batches` for physical inventory and aliquots.
- Consumable differentiation: `is_consumable` flag in materials determines batch behavior (decrement vs reference usage).
- Concurrency: simple timestamp checks (updated_at) for MVP; no optimistic locking (version field).
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
materials (Unified Product Catalog - Chemicals, Instruments, Equipment, Samples)
├── id (PK)
├── name (e.g., "Éthanol 99%", "Spectrophotomètre UV-Vis", "Échantillon Sang")
├── description
├── supplier_id (FK → suppliers, optional)
├── catalog_number (e.g., "E7023", optional)
├── is_consumable (BOOLEAN - TRUE: quantity decrements on use, FALSE: usage reference only)
├── default_unit_type (ENUM: 'volume', 'mass', 'length', 'count')
├── created_by_id (FK), last_modified_by_id (FK)
├── created_at, last_modified_at

material_batches (Unified Physical Inventory: Batches, Aliquots, Instrument Instances, Sample Instances)
├── id (PK)
├── material_id (FK → materials)
├── parent_batch_id (FK → material_batches, NULL if original batch/instance)
├── batch_number (for received batches, NULL for aliquots)
├── label (for aliquots or custom identification)
├── expiry_date (optional)
├── quantity (DECIMAL(20,12) - in base unit; NULL for non-quantifiable items)
├── unit_type (ENUM: 'volume', 'mass', 'length', 'count'; NULL if not applicable)
├── location_id (FK → locations)
├── notes
├── created_by_id (FK), last_modified_by_id (FK)
├── created_at, last_modified_at

suppliers (Material Suppliers)
├── id (PK)
├── name
├── contact_info
├── created_by_id (FK), last_modified_by_id (FK)
├── created_at, last_modified_at

locations (Storage Locations)
├── id (PK)
├── name
├── description
├── created_by_id (FK), last_modified_by_id (FK)
├── created_at, last_modified_at

activities (Audit Log)
├── id (PK)
├── activity_type (ENUM: 'receive', 'move', 'consume', 'use', 'discard', 'aliquot', 'relabel')
├── entity_type (ENUM: 'material_batch')
├── entity_id (FK → material_batches)
├── related_entity_id (for lineage, e.g., child aliquot or related batch)
├── quantity (DECIMAL(20,12), NULL for non-quantity actions)
├── unit_type (ENUM, NULL for non-quantity actions)
├── from_location_id (FK → locations, NULL if not move)
├── to_location_id (FK → locations, NULL if not move)
├── reason
├── notes
├── note_id (Constellab Note link)
├── created_by_id (FK), last_modified_by_id (FK)
├── created_at, last_modified_at
```

**Relationships:**
- suppliers 1:N materials (optional)
- materials 1:N material_batches
- material_batches 1:N material_batches (parent_batch_id self-reference for lineage; aliquots inherit supplier_id from parent)
- locations 1:N material_batches
- activities references material_batches via entity_type='material_batch' and entity_id

**Indices:**
```sql
CREATE INDEX idx_materials_supplier ON materials(supplier_id);
CREATE INDEX idx_materials_consumable ON materials(is_consumable);

CREATE INDEX idx_material_batches_material ON material_batches(material_id);
CREATE INDEX idx_material_batches_parent ON material_batches(parent_batch_id);
CREATE INDEX idx_material_batches_location ON material_batches(location_id);
CREATE INDEX idx_material_batches_batch_number ON material_batches(batch_number);

CREATE INDEX idx_activities_entity ON activities(entity_id);
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


#### Data Modeling Details

- Database: MariaDB (Constellab production and development environments) behind Peewee `DatabaseProxy` and `ElnDbManager`-style manager.
- Modeling: normalized tables with foreign keys; lineage tracked via parent-child self-references in material_batches; activity log table for all changes; standardized audit fields on all tables.
- Audit Fields: All tables include `created_by_id`, `last_modified_by_id`, `created_at`, `last_modified_at` for complete change tracking.
- Validation: service-layer input validation (quantities/units presence for consumables, non-negative stock, location existence, unit_type consistency, supplier existence, is_consumable consistency) before model operations.
- Migrations: migration scripts aligned with `gws_project` pattern (versioned migration modules); schema evolution tracked in brick.
- Caching: none for MVP; rely on DB queries; consider simple in-memory caching for static lists (locations, materials, suppliers) if needed later.

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
- Components: reusable form components for quantity/unit input with conversion, location picker, supplier picker, lineage viewer, consumable/non-consumable indicator; page components for inventory, note-linked tool.
- Routing: route-per-page via `@rx.page`; index lists inventory grouped by material with consumable/non-consumable filters; dedicated pages for detail and note tool entry.
- Performance: avoid heavy client state; server roundtrips for actions; no websockets in MVP.
- Bundle: default Reflex bundling; defer optimization until needed.

### Infrastructure & Deployment

- Hosting: Constellab-managed; no custom deploy logic.
- CI/CD: Constellab pipeline standards; tests for services when added.
- Environment config: `GWS_REFLEX_API_URL` required by `rxconfig.py`; brick `settings.json` for dependencies.
- Monitoring/logging: Constellab logs; activity log table for user-facing audit.
- Scaling: single lab instance; vertical scaling sufficient.

### Decision Impact Analysis

**Implementation Sequence (Backend-First Approach):**

**Phase 1: Backend Foundation (Complete before UI)**
1. Define entity schemas (Material, MaterialBatch, Supplier, Location, Activity)
2. Implement unit conversion utilities in `utils/units.py` with comprehensive tests
3. Implement all service-layer operations:
   - MaterialService: CRUD, consumable flag logic, handle all material types (chemicals, instruments, equipment, samples)
   - MaterialBatchService: receive, aliquot (via parent_batch_id with supplier inheritance), move, use/decrement for consumables, usage reference for non-consumables
   - SupplierService: CRUD operations
   - LocationService: CRUD, default "labo" creation
   - ActivityService: logging, lineage tracking, note-linkage hooks
4. Write comprehensive unit tests for all services and entities
5. Validate data integrity, lineage tracking, and supplier inheritance
6. Test consumable vs non-consumable behavior across all material types
7. Populate seed data (initial materials - consumables and non-consumables, suppliers, default location "labo")

**Phase 2: Frontend Implementation (After backend is stable)**
8. Wire Reflex states/pages to call services and refresh views with display conversions
9. Implement UI components (quantity input, location picker, supplier picker, lineage viewer, consumable/non-consumable indicator)
10. Build inventory pages with filters (consumable/non-consumable), material detail, note-linked tool
11. Add user confirmations on critical operations
12. Integration testing between UI and services

**Cross-Component Dependencies:**
- Lineage tracked via material_batches.parent_batch_id self-reference with supplier inheritance from parent.
- Activity log depends on MaterialBatchService for all batch operations.
- Unit conversion utilities used by all services and UI components dealing with quantities (only for consumables and quantifiable items).
- Supplier references used in materials; inherited by aliquots from parent batch.
- Location list used across all inventory views; default "labo" location created at startup.
- Consumable flag (materials.is_consumable) determines batch operation behavior throughout services and UI.
- Concurrency checks rely on model timestamps (updated_at) and service enforcement (no optimistic locking in MVP).

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Critical Conflict Points Identified:** 20+ areas where AI agents could make different choices (naming, structure, format, communication, process)

### Naming Patterns

**Database Naming Conventions:**
- Tables: snake_case plural (e.g., `materials`, `material_batches`, `suppliers`, `locations`, `activities`).
- Columns: snake_case (e.g., `created_by_id`, `last_modified_by_id`, `last_modified_at`, `parent_batch_id`, `unit_type`, `is_consumable`).
- Foreign keys: `<entity>_id` (e.g., `material_id`, `supplier_id`, `location_id`, `parent_batch_id`).
- Indices: `idx_<table>_<column>` (e.g., `idx_material_batches_material`, `idx_material_batches_parent`).
- Audit fields: All tables include `created_by_id`, `last_modified_by_id`, `created_at`, `last_modified_at`.

**API Naming Conventions:**
- REST endpoints: plural nouns (e.g., `/materials`, `/material_batches`, `/suppliers`, `/locations`).
- Route params: `/:id` (numeric/UUID) with lowercase names (e.g., `/material_batches/:id`).
- Query params: snake_case (e.g., `location_id`, `parent_batch_id`, `material_id`, `supplier_id`, `is_consumable`).
- Headers: standard plus `X-Constellab-*` when needed.

**Code Naming Conventions:**
- Components: PascalCase (e.g., `InventoryList`, `LineageViewer`, `QuantityInput`).
- Files: snake_case for Python modules (e.g., `material_lot_service.py`, `unit_converter.py`), consistent within Reflex.
- Functions/variables: snake_case in Python (e.g., `get_material_lots`, `to_base_unit`, `current_user_id`).
- Constants: UPPER_SNAKE_CASE (e.g., `BASE_UNITS`, `CONVERSION_FACTORS`).

### Structure Patterns

**Project Organization:**
- **Domain-driven directories**: Each domain (`materials/`, `suppliers/`, `locations/`, `activities/`) contains its models and services together.
- Core infrastructure: `core/` for DB manager and base models.
- Frontend: `project_app/` for Reflex UI (developed after backend is stable).
- Shared utilities: `utils/` for conversion logic, helpers.
- Tests: mirror domain structure under `tests/` (e.g., `tests/materials/`, `tests/suppliers/`, `tests/locations/`).
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
- Endpoint: `POST /material_batches/{id}/consume` → body `{quantity: 10, unit: "mL"}` → response `{data: {remaining_quantity: 490, unit: "mL", quantity_base: 0.49, unit_type: "volume"}}` (for consumables).
- Endpoint: `POST /material_batches/{id}/use` → body `{}` → response `{data: {message: "Usage recorded"}}` (for non-consumables).
- DB: table `material_batches` with columns `id`, `material_id`, `quantity` (DECIMAL), `unit_type` (ENUM), `parent_batch_id`, `created_by_id`, `last_modified_by_id`, `created_at`, `last_modified_at`.
- Service call: `to_base_unit(500, "mL", "volume")` returns `Decimal('0.5')`.
- Aliquot creation: child batch inherits `supplier_id` from parent batch automatically.
- Activity types: 'receive', 'move', 'consume' (for consumables), 'use' (for non-consumables), 'discard', 'aliquot', 'relabel'.

**Anti-Patterns:**
- Mixed casing in JSON (`userId`, `created_at`) within same payload.
- Singular table names (`material`) alongside plural (`locations`).
- Storing quantities in user-selected units (e.g., "500 mL" as string).
- Using FLOAT for quantities (precision loss).
- Not inheriting supplier_id when creating aliquots from parent batches.

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
│       │   ├── material.py               # Entity/Model (unified: chemicals, instruments, samples, equipment)
│       │   ├── material_batch.py         # Entity/Model (unified: batches, aliquots, instances)
│       │   ├── material_service.py       # Service (manages all material types)
│       │   └── material_batch_service.py # Service (manages all batch operations)
│       ├── suppliers/
│       │   ├── __init__.py
│       │   ├── supplier.py               # Entity/Model
│       │   └── supplier_service.py       # Service
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
│   │   ├── test_material_service.py         # Tests for all material types (consumables, non-consumables)
│   │   └── test_material_batch_service.py   # Tests for all batch operations
│   ├── suppliers/
│   │   └── test_supplier_service.py
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
- Each domain has dedicated models and services co-located:
  - `materials/` contains Material, MaterialBatch, and their services - handles ALL material types (chemicals, instruments, equipment, samples) with consumable/non-consumable differentiation
  - `suppliers/` contains Supplier and SupplierService
  - `locations/` contains Location and LocationService
  - `activities/` contains Activity and ActivityService
- Cross-domain operations orchestrated via activity service in `activities/` domain.
- Note-linked actions integrate through `note_tool_state` invoking MaterialBatchService.
- Clear domain boundaries: `materials/` (unified catalog + inventory with consumable logic for all types), `suppliers/` (supplier management), `locations/` (storage), `activities/` (audit log).

**Data Boundaries:**
- Entities encapsulate DB schema and relations; lineage defined via `parent_batch_id` in MaterialBatch (with supplier inheritance).
- Suppliers and Locations are global catalogs used across features.
- Activities table references material_batches via entity_type='material_batch' and entity_id.
- Consumable flag in Material determines decrement behavior in MaterialBatch operations:
  - is_consumable=TRUE: chemicals, reagents, samples → quantity decrements on use
  - is_consumable=FALSE: instruments, equipment → usage reference only, no quantity decrement.

### Requirements to Structure Mapping

**Feature/Epic Mapping:**
- Material Management (FR1–FR4, all types): `materials/` domain (material.py for chemicals, instruments, samples, equipment; material_service.py handles all types with is_consumable differentiation).
- Supplier Management (FR23–FR26): `suppliers/` domain (supplier.py, supplier_service.py).
- Batch Operations (FR5–FR10): `materials/material_batch_service.py` with consumable logic from Material.is_consumable for all material types.
- Aliquoting & Lineage (FR11–FR13): `materials/material_batch.py` with `parent_batch_id` and supplier inheritance, `materials/material_batch_service.py` (aliquot creation for all material types), lineage viewer in `project_app/common/lineage_viewer.py`.
- Consumption & Usage (FR14–FR16, FR19–FR22): `materials/material_batch_service.py` creates 'consume' activities for consumables (with quantity decrement) and 'use' activities for non-consumables (reference only) based on Material.is_consumable.
- Note-Linked Actions (FR17–FR18): `project_app/note_tool/*` states/pages with calls to MaterialBatchService; activity linkage via `activities/activity_service.py`.
- Location Management (FR27–FR31): `locations/` domain (location.py, location_service.py) with simplified schema (name, description only) and default "labo" creation.
- Activity Log: `activities/` domain (activity.py, activity_service.py), simplified audit trail without correction tracking; inventory pages display activity history for all material types.
- Units & Consistency (FR34–FR36): `utils/units.py` for conversion logic; used by forms, validations, and display components for quantifiable materials.

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
- Supplier → Material catalog (materials with is_consumable flag for all types: chemicals, instruments, samples, equipment) → material batches (received with supplier_id) → material batches (aliquots via parent_batch_id inheriting supplier_id).
- Material batches flow through MaterialBatchService for receive/use/move/aliquot operations; activity records appended; lineage updated consistently.
- Consumable vs non-consumable behavior determined by Material.is_consumable; enforced in MaterialBatchService:
  - Consumable materials: quantity decrements on use
  - Non-consumable materials: usage referenced without quantity change
- Quantities converted on input/output; stored uniformly in base units (for quantifiable materials).
- Default location "labo" created at Constellab startup.

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
- **Domain-based** with clear boundaries; each domain directory (`materials/`, `suppliers/`, `locations/`, `activities/`) contains related models and services.
- `materials/` is unified domain handling all material types (chemicals, instruments, samples, equipment) via is_consumable flag.
- `core/` for DB manager and base model classes.
- `utils/` for shared logic like unit conversion.
- `project_app/` for UI layer (Reflex pages/states) - developed after backend is stable.

**Test Organization:**
- Tests mirror domain structure: `tests/materials/`, `tests/suppliers/`, `tests/locations/`, `tests/activities/`.
- Unit tests per service co-located with domain tests.
- Material tests cover ALL material types (consumables: chemicals, reagents, samples; non-consumables: instruments, equipment).
- Unit tests for conversion utilities in `tests/utils/`.
- Test supplier inheritance in aliquot creation for all material types.
- Test consumable vs non-consumable behavior across different material types.
- Fixtures in `tests/fixtures` with examples of all material types; integration tests optional post-MVP.
- **All backend tests must pass before starting frontend development.**

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
- Inventory (all material types unified), Supplier Management, Aliquoting & Lineage (via parent_batch_id with supplier inheritance), Note-Linked Actions, Consumable vs Non-Consumable Logic (chemicals/samples vs instruments/equipment), Activity & Correction, Units (via unit_type and utils for quantifiable materials) are all mapped to specific entities, services, and pages/states.

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
- Confirm initial materials catalog (covering all types: consumables and non-consumables), suppliers list, and location list seed data.
- Document unit conversion examples in `utils/units.py` docstrings.
- Ensure default location "labo" is created via Constellab startup code.
- Define clear guidelines for categorizing new materials as consumable vs non-consumable.

**Nice-to-Have Gaps:**
- Add integration tests for note-linked actions.
- Expand activity audit views post-MVP.
- Consider user-defined unit conversions post-MVP.

### Validation Issues Addressed

- Database selection updated to MariaDB and reflected across decisions.
- Renamed tables: material_types → materials, material_lots → material_batches.
- **Unified data model: removed separate `samples` and `instruments` tables - all managed via `materials` with is_consumable flag.**
- Added dedicated suppliers table with full CRUD.
- Simplified schemas: removed category, packaging_info, storage_conditions, safety_info, status fields, qc_status, generation, version fields.
- Added is_consumable flag to materials for consumption behavior (TRUE for chemicals/samples, FALSE for instruments/equipment).
- Unified material_batches table with parent_batch_id for aliquot lineage with supplier inheritance.
- Removed optimistic locking (version fields) for MVP simplicity.
- Removed separate units and aliquots tables; unit handling via ENUM and conversion utilities.
- Simplified entity_type in activities to just 'material_batch'.

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
- **Fully unified data model: single `materials` and `material_batches` schema handles all types (chemicals, instruments, equipment, samples).**
- Clear separation between material catalog (materials with is_consumable) and physical inventory (material_batches).
- Consumable/non-consumable differentiation via simple boolean flag eliminates need for separate entity types.
- Dedicated suppliers table with CRUD operations; supplier_id inherited by aliquots from parent batch.
- Maximally simplified schemas focused on MVP essentials; removed unnecessary fields and entire tables.
- Unified material_batches table handles received batches and aliquots via parent_batch_id, simplifying lineage.
- No separate units, samples, instruments, or aliquots tables; minimal table count (4 core entities).
- No optimistic locking for MVP; simple timestamp-based concurrency.
- Strong Constellab alignment for session and deployment.
- Backend-first development approach ensures solid foundation before UI work.
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
- **CRITICAL: Use gws_project repository as reference** for both backend structure (services/entities co-located by domain) and frontend structure (Reflex pages/states).

**First Implementation Priority:**
```bash
gws reflex run bricks/gws_eln/src/gws_eln/project_app/_project_app/rxconfig.py
```

**Reference Repository:**
- Study `gws_project` for complete backend and frontend patterns
- Backend: domain-driven structure with co-located services and entities
- Frontend: Reflex application with page components and state management

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
- **Maximally simplified unified data model: materials (with is_consumable for all types) + material_batches (with lineage & supplier inheritance), suppliers, locations, activities**
- **No separate samples, instruments, aliquots, or units tables**
- No optimistic locking (version fields) for MVP
- Base unit storage (L, kg, m, units) with application-layer conversion
- Backend-first development approach mandated
- Implementation patterns ensuring AI agent consistency
- Complete project structure with all files and directories
- Requirements to architecture mapping
- Validation confirming coherence and completeness

**🏗️ Implementation Ready Foundation**

- 20+ architectural decisions made
- Comprehensive implementation patterns defined
- **5 core entities (Material, MaterialBatch, Supplier, Location, Activity) - unified model handles all material types**
- All PRD requirements supported with maximally simplified schemas and unit handling
- Clear backend-first development sequence

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

**CRITICAL: Backend-First Approach - Complete Phase 1 before Phase 2**

**Phase 1: Backend Development (Must be 100% complete with passing tests)**
1. **Study gws_project repository structure** - understand the backend pattern (services/entities co-located by domain)
2. Initialize project using documented starter template
3. Set up development environment per architecture
3. Implement core architectural foundations (entities: material, material_batch, supplier, location, activity) - **only 5 core entities**
4. Implement unit conversion utilities (`utils/units.py`) with comprehensive tests
5. Build all domain services with full functionality:
   - MaterialService with is_consumable logic handling ALL material types (chemicals, instruments, equipment, samples)
   - MaterialBatchService with supplier inheritance on aliquot creation for all material types
   - SupplierService with CRUD
   - LocationService with default "labo" creation
   - ActivityService for unified audit logging
6. Write and validate all unit tests for services and entities
7. Test critical behaviors across ALL material types:
   - Consumable materials (chemicals, reagents, samples): quantity decrement on use
   - Non-consumable materials (instruments, equipment): usage reference without decrement
   - Supplier inheritance in aliquots for all types
   - Lineage tracking across all material types
   - Unit conversions for quantifiable materials
   - Activity logging for all operations
8. Seed initial data (materials of all types, suppliers, default location "labo")

**Phase 2: Frontend Development (Only after Phase 1 complete)**
9. **Study gws_project Reflex application structure** - understand page/state pattern
10. Build Reflex pages/states following gws_project patterns
11. Implement UI components (quantity input, supplier picker, location picker, lineage viewer)
11. Wire UI to backend services
12. Integration testing
13. Maintain consistency with documented rules

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

**� Reference Implementation**
gws_project repository provides complete working example of backend (services/entities) and frontend (Reflex) structure.

**�🔢 Simplified Unit Handling**
Base unit storage with application-layer conversion balances simplicity and flexibility.

---

**Architecture Status:** READY FOR IMPLEMENTATION ✅

**Next Phase:** Begin implementation using the architectural decisions and patterns documented herein.

**Document Maintenance:** Update this architecture when major technical decisions are made during implementation.

---


**End of Architecture Document v2**
