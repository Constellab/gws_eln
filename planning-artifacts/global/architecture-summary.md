# Architecture Summary v2 - ELN Inventory System

**Version:** 2.0  
**Date:** 2026-01-21  
**Status:** READY FOR IMPLEMENTATION ✅

## Quick Reference

This is a 1-page summary of the complete ELN architecture. For detailed information, refer to the modular documentation below.

## 🎯 Core Concept

**Unified inventory management system** for lab materials (chemicals, instruments, equipment, samples) with **5 core entities** and a **single is_consumable flag** to differentiate behavior.

## 📊 Data Model (5 Tables)

```
materials (catalog)
  ├── is_consumable (TRUE=chemicals/reagents/samples, FALSE=instruments/equipment)
  └── supplier_id (optional FK)

material_batches (physical inventory)
  ├── parent_batch_id (self-reference for aliquots with supplier inheritance)
  ├── quantity/unit_type (stored in base units: L, kg, m, units)
  └── location_id (FK)

suppliers (simple catalog)
  └── name, description

locations (simple catalog)
  └── name, description (default: "labo")

activities (audit log)
  └── activity_type: receive, move, consume, use, discard, aliquot, relabel
```

**Audit Fields (all tables):** `created_by_id`, `last_modified_by_id`, `created_at`, `last_modified_at`

## 🔑 Critical Decisions

1. **Single unified model**: No separate tables for samples, instruments, units, or aliquots
2. **is_consumable flag**: Determines if quantity decrements (`consume`) or just references (`use`)
3. **Base unit storage**: All quantities stored in L/kg/m/units; converted in application layer
4. **gws_project pattern**: MUST follow reference repository for backend and frontend structure
5. **Backend-first**: Phase 1 (all services + tests) must complete before Phase 2 (UI)

## 🏗️ Technology Stack

- **Framework**: Python Reflex (latest)
- **Database**: MariaDB (production & dev) via Peewee ORM
- **ORM**: `gws_core.Model` and `ModelWithUser`
- **Auth**: Constellab platform (via `CurrentUserService`)
- **Reference**: `gws_project` repository (backend/frontend patterns)

## 📁 Project Structure

```
src/gws_eln/
├── core/              # DB manager, base models
├── materials/         # material.py, material_batch.py, services (all types)
├── suppliers/         # supplier.py, supplier_service.py
├── locations/         # location.py, location_service.py
├── activities/        # activity.py, activity_service.py
├── utils/             # units.py (conversion), validators.py
└── project_app/       # Reflex UI (pages/states) - Phase 2 only
```

## 🎬 Implementation Sequence

**Phase 1: Backend (MUST complete first)**
1. Study `gws_project` backend structure
2. Define 5 entities + audit fields
3. Implement `utils/units.py` with tests
4. Implement all services (Material, MaterialBatch, Supplier, Location, Activity)
5. Write comprehensive tests for ALL material types
6. Validate: consumable/non-consumable behavior, supplier inheritance, lineage
7. Seed data (materials of all types, suppliers, default "labo" location)

**Phase 2: Frontend (After Phase 1 passes all tests)**
8. Study `gws_project` Reflex structure
9. Build pages/states following gws_project patterns
10. Implement UI components (quantity input, pickers, lineage viewer)
11. Wire UI to backend services
12. Integration testing

## 🔧 Key Patterns

**Naming:**
- Tables: `snake_case` plural (materials, material_batches)
- Columns: `snake_case` (created_by_id, last_modified_by_id)
- Components: `PascalCase` (InventoryList, LineageViewer)

**Activity Types:**
- `receive`: New batch from supplier
- `move`: Change location
- `consume`: Use consumable (decrements quantity)
- `use`: Use non-consumable (reference only)
- `discard`: Remove with reason
- `aliquot`: Create child batch (inherits supplier_id)
- `relabel`: Change label only

**Unit Conversion:**
- Input: user unit → `to_base_unit()` → storage (L/kg/m/units)
- Display: storage → `from_base_unit()` → user-friendly unit

## 📚 Full Documentation

- **Database schema**: [database-schema.md](database-schema.md) - Complete tables, relationships, indices
- **Implementation patterns**: [implementation-patterns.md](implementation-patterns.md) - Naming conventions, code patterns
- **Project structure**: [project-structure.md](project-structure.md) - Directory organization, domain boundaries
- **Development sequence**: [development-sequence.md](development-sequence.md) - Step-by-step implementation guide

## ⚠️ Critical Rules

1. **DO NOT** deviate from `gws_project` structure without justification
2. **DO NOT** start Phase 2 before Phase 1 tests pass
3. **DO NOT** use separate tables for samples/instruments
4. **DO** store quantities in base units (DECIMAL(20,12))
5. **DO** inherit supplier_id in aliquots from parent batch
6. **DO** use standardized audit fields on ALL tables

## 🚀 Start Command

```bash
gws reflex run bricks/gws_eln/src/gws_eln/project_app/_project_app/rxconfig.py
```

---
**For detailed information, consult the modular documentation files listed above.**
