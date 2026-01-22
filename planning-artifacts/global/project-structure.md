# Project Structure - ELN Inventory System

**Version:** 2.0  
**Date:** 2026-01-21

## Overview

Complete directory structure with **domain-driven organization** following **gws_project** patterns.

---

## 📁 Complete Directory Tree

```
bricks/gws_eln/
├── README.md                       # Project overview, setup instructions
├── settings.json                   # Brick dependencies and configuration
│
├── src/
│   └── gws_eln/
│       ├── __init__.py
│       │
│       ├── core/                   # Core infrastructure
│       │   ├── __init__.py
│       │   ├── eln_db_manager.py   # Database manager (DatabaseProxy setup)
│       │   └── model_with_user.py  # Base model with audit fields
│       │
│       ├── materials/              # Material domain (ALL material types)
│       │   ├── __init__.py
│       │   ├── material.py         # Entity/Model (chemicals, instruments, samples, equipment)
│       │   ├── material_batch.py   # Entity/Model (batches, aliquots, instances)
│       │   ├── material_service.py       # Service (CRUD, consumable logic)
│       │   └── material_batch_service.py # Service (receive, consume, use, move, aliquot)
│       │
│       ├── suppliers/              # Supplier domain
│       │   ├── __init__.py
│       │   ├── supplier.py         # Entity/Model
│       │   └── supplier_service.py # Service (CRUD)
│       │
│       ├── locations/              # Location domain
│       │   ├── __init__.py
│       │   ├── location.py         # Entity/Model
│       │   └── location_service.py # Service (CRUD, default "labo")
│       │
│       ├── activities/             # Activity domain
│       │   ├── __init__.py
│       │   ├── activity.py         # Entity/Model
│       │   └── activity_service.py # Service (logging, lineage, note-linkage)
│       │
│       ├── utils/                  # Shared utilities
│       │   ├── __init__.py
│       │   ├── units.py            # Unit conversion (to_base_unit, from_base_unit)
│       │   └── validators.py       # Input validation helpers
│       │
│       ├── project_app/            # Reflex UI (Phase 2 only)
│       │   └── _project_app/
│       │       ├── assets/         # Static assets (images, CSS if needed)
│       │       ├── dev_config.json # Development configuration
│       │       ├── rxconfig.py     # Reflex configuration (GWS_REFLEX_API_URL)
│       │       │
│       │       └── project_app/    # Reflex application
│       │           ├── __init__.py
│       │           │
│       │           ├── common/     # Shared UI components
│       │           │   ├── __init__.py
│       │           │   ├── quantity_input.py     # Quantity + unit input with conversion
│       │           │   ├── lineage_viewer.py     # Parent-child lineage tree
│       │           │   ├── location_picker.py    # Location dropdown/selector
│       │           │   └── supplier_picker.py    # Supplier dropdown/selector
│       │           │
│       │           ├── inventory/  # Inventory list page
│       │           │   ├── __init__.py
│       │           │   ├── inventory_page.py     # Main inventory view
│       │           │   └── inventory_state.py    # State management
│       │           │
│       │           ├── material_detail/ # Material detail page
│       │           │   ├── __init__.py
│       │           │   ├── material_detail_page.py
│       │           │   └── material_detail_state.py
│       │           │
│       │           ├── note_tool/  # Note-linked tool
│       │           │   ├── __init__.py
│       │           │   ├── note_tool_page.py     # Embedded in Notes
│       │           │   └── note_tool_state.py    # Note-specific actions
│       │           │
│       │           └── project_app.py # Main app entry point
│       │
│       ├── migrations/             # Database migrations
│       │   ├── __init__.py
│       │   ├── migration_0001_initial.py    # Create all tables
│       │   └── migration_0002_seed_data.py  # Seed default location, examples
│       │
│       └── planning-artifacts/    # Architecture documentation
│           ├── architecture.md    # Original architecture
│           ├── architecture-summary.md # Quick reference
│           ├── database-schema.md # Detailed schema
│           ├── implementation-patterns.md # Patterns and conventions
│           ├── project-structure.md # This file
│           └── development-sequence.md # Implementation phases
│
├── tests/                          # Test suite (mirrors src structure)
│   ├── __init__.py
│   │
│   ├── materials/                  # Material domain tests
│   │   ├── __init__.py
│   │   ├── test_material_service.py      # All material types (consumables, non-consumables)
│   │   └── test_material_batch_service.py # Batch operations, lineage, supplier inheritance
│   │
│   ├── suppliers/
│   │   ├── __init__.py
│   │   └── test_supplier_service.py
│   │
│   ├── locations/
│   │   ├── __init__.py
│   │   └── test_location_service.py
│   │
│   ├── activities/
│   │   ├── __init__.py
│   │   └── test_activity_service.py
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   └── test_unit_converter.py # Unit conversion tests
│   │
│   └── fixtures/                   # Test data
│       ├── __init__.py
│       └── sample_data.json        # Example materials, suppliers, locations
│
└── .gitignore
```

---

## 🏗️ Domain-Driven Organization

### Why Domain-Driven?

**Benefits:**
- **High Cohesion**: Related models and services live together
- **Easy Discovery**: Find all material logic in `materials/`
- **Clear Boundaries**: Each domain has well-defined responsibilities
- **Scalability**: Easy to add new domains or split existing ones
- **Team Collaboration**: Teams can own specific domains

**vs. Layer-Based (NOT used):**
```
# ❌ DON'T: Layer-based structure
src/
├── models/         # All models mixed together
├── services/       # All services mixed together
└── views/          # All views mixed together
```

---

## 📦 Domain Breakdown

### Core Domain (`core/`)

**Purpose:** Shared infrastructure for all domains.

**Files:**
- `eln_db_manager.py`: Database connection setup, `DatabaseProxy`
- `model_with_user.py`: Base model class with audit fields

**Dependencies:** None (used by all other domains)

---

### Materials Domain (`materials/`)

**Purpose:** Unified material catalog and physical inventory for ALL types.

**Handles:**
- Chemicals, reagents
- Instruments, equipment  
- Samples
- Consumable vs non-consumable logic

**Files:**
- `material.py`: Material entity (product catalog)
- `material_batch.py`: MaterialBatch entity (physical inventory)
- `material_service.py`: Material CRUD, consumable flag logic
- `material_batch_service.py`: Batch operations (receive, consume, use, move, aliquot, discard)

**Key Behavior:**
- `is_consumable` flag determines decrement vs reference
- Aliquots inherit supplier_id from parent batch
- Lineage tracked via `parent_batch_id`

---

### Suppliers Domain (`suppliers/`)

**Purpose:** Supplier catalog management.

**Files:**
- `supplier.py`: Supplier entity
- `supplier_service.py`: CRUD operations

**Relationships:**
- Referenced by `materials.supplier_id`
- Inherited by aliquots from parent material

---

### Locations Domain (`locations/`)

**Purpose:** Storage location management.

**Files:**
- `location.py`: Location entity (simplified: name, description)
- `location_service.py`: CRUD, default "labo" creation

**Key Behavior:**
- Default location "labo" created at startup
- Simple flat structure (no hierarchy in MVP)

---

### Activities Domain (`activities/`)

**Purpose:** Audit log and activity tracking.

**Files:**
- `activity.py`: Activity entity (7 activity types)
- `activity_service.py`: Logging, lineage tracking, note-linkage

**Activity Types:**
- `receive`, `move`, `consume`, `use`, `discard`, `aliquot`, `relabel`

**Key Behavior:**
- Logs all inventory changes
- Links to Constellab Notes via `note_id`
- Tracks lineage via `related_entity_id`

---

### Utils Domain (`utils/`)

**Purpose:** Shared utilities and helpers.

**Files:**
- `units.py`: Unit conversion logic (to_base_unit, from_base_unit)
- `validators.py`: Input validation helpers

**Key Behavior:**
- All conversions centralized in `units.py`
- Used by services AND UI components

---

### Frontend Domain (`project_app/`)

**Purpose:** Reflex UI (Phase 2 only, after backend complete).

**Structure:**
```
project_app/
└── _project_app/
    ├── rxconfig.py          # Reflex config
    └── project_app/
        ├── common/          # Shared components
        ├── inventory/       # Inventory list page
        ├── material_detail/ # Material detail page
        ├── note_tool/       # Note-linked tool
        └── project_app.py   # Main app
```

**Key Behavior:**
- Pages call services (NOT models directly)
- State management per page/feature
- Follow gws_project Reflex patterns

---

## 🔗 Architectural Boundaries

### API Boundaries

- **Internal only**: No public APIs
- **Authentication**: Constellab session (CurrentUserService)
- **Data access**: Via Peewee models and services

### Component Boundaries

```
Reflex Pages → States → Services → Models → Database
```

- Pages/States: UI logic, user interactions
- Services: Business logic, validations
- Models: Data access, ORM

### Service Boundaries

Each domain has its own services:
- `MaterialService` / `MaterialBatchService`: Material operations
- `SupplierService`: Supplier operations
- `LocationService`: Location operations
- `ActivityService`: Activity logging

**Cross-domain orchestration:**
- Via `ActivityService` for logging
- Via service-to-service calls (e.g., MaterialBatchService → ActivityService)

---

## 🧪 Test Organization

### Mirror Domain Structure

Tests organized identically to `src/`:

```
tests/
├── materials/
│   ├── test_material_service.py
│   └── test_material_batch_service.py
├── suppliers/
│   └── test_supplier_service.py
├── locations/
│   └── test_location_service.py
├── activities/
│   └── test_activity_service.py
└── utils/
    └── test_unit_converter.py
```

**Benefits:**
- Easy to find tests for specific domain
- Clear test coverage per domain
- Matches development mental model

### Test Fixtures

Located in `tests/fixtures/`:
- `sample_data.json`: Example materials (all types), suppliers, locations

**Coverage:**
- Consumable materials (chemicals, samples)
- Non-consumable materials (instruments, equipment)
- Supplier relationships
- Lineage scenarios

---

## 🚀 Development Workflow

### Phase 1: Backend (MUST complete first)

**Order:**
1. `core/`: DB manager, base models
2. `utils/`: Unit conversion (with tests)
3. `materials/`, `suppliers/`, `locations/`, `activities/`: Entities + services (with tests)
4. `migrations/`: Initial schema, seed data

**Tests MUST pass before Phase 2.**

### Phase 2: Frontend (After Phase 1 complete)

**Order:**
1. `project_app/common/`: Shared components
2. `project_app/inventory/`: Main inventory page
3. `project_app/material_detail/`: Detail page
4. `project_app/note_tool/`: Note-linked tool

**Study gws_project before starting Phase 2.**

---

## 📝 Configuration Files

### Brick Level
- `README.md`: Project overview
- `settings.json`: Brick dependencies
- `.gitignore`: Git exclusions

### App Level
- `rxconfig.py`: Reflex configuration (requires `GWS_REFLEX_API_URL`)
- `dev_config.json`: Development settings

### Environment
- `.env`: Managed by Constellab (not in repo)

---

## 🔍 Reference Implementation

**CRITICAL:** Study `gws_project` repository for:
- Backend structure (services/entities co-located)
- Frontend structure (Reflex pages/states)
- Testing patterns
- Configuration examples

**DO NOT deviate** from gws_project patterns without justification.

---

