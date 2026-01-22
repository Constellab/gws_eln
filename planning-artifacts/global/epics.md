---
stepsCompleted: ["step-01-validate-prerequisites", "step-02-design-epics", "step-03-create-stories", "step-04-final-validation"]
inputDocuments:
	- /lab/user/bricks/gws_eln/planning-artifacts/prd.md
	- /lab/user/bricks/gws_eln/planning-artifacts/architecture-summary.md
	- /lab/user/bricks/gws_eln/planning-artifacts/database-schema.md
lastEdited: 2026-01-21
editHistory:
	- date: 2026-01-21
	  editor: Ben
	  changes: "Complete rewrite: backend-first approach with 12 epics (7 backend, 5 frontend); aligned with unified Material/Material_Batch model; separated Phase 1 (backend+tests) from Phase 2 (UI)"
---

# gws_eln - Epic Breakdown v2

## Overview

Complete epic and story breakdown for **gws_eln** (ELN Inventory System), decomposed following **backend-first** implementation strategy with unified data model (Material, Material_Batch).

**Critical Implementation Rule:** ALL Phase 1 epics (1-7) MUST be completed with passing tests BEFORE starting Phase 2 epics (8-12).

---

## 🎯 Epic Summary

### PHASE 1: BACKEND (Epics 1-7) — MUST COMPLETE FIRST

**Epic 1:** Core Infrastructure & Database Entities  
**Epic 2:** Units System & Validators  
**Epic 3:** Service Layer - Suppliers & Locations  
**Epic 4:** Service Layer - Materials  
**Epic 5:** Service Layer - Material Batches  
**Epic 6:** Service Layer - Aliquots & Lineage  
**Epic 7:** Activity Service & Audit Log

### PHASE 2: FRONTEND (Epics 8-12) — AFTER PHASE 1 TESTS PASS

**Epic 8:** Reflex UI Foundation  
**Epic 9:** Material & Batch Management UI  
**Epic 10:** Suppliers & Locations UI  
**Epic 11:** Aliquots & Lineage UI  
**Epic 12:** Activity Log & Note Integration

---

---

## Requirements Inventory

### Functional Requirements (from PRD)

**Material Management:**
- FR1: Create material with name, description, consumable flag
- FR2: Edit material metadata
- FR3: View material catalog
- FR4: Delete unused material definitions

**Batch Management:**
- FR5: Create batch with material, optional supplier, location assignment (default: "labo")
- FR6: View batch details (material, batch_number, supplier, location, quantity, parent_batch_id)
- FR7: Increment batch quantity (receive stock)
- FR8: Decrement consumable batch quantity
- FR9: Move batch between locations
- FR10: Delete empty/obsolete batches

**Aliquot Creation:**
- FR11: Create aliquot from parent batch with quantity/unit
- FR12: Create multi-level aliquots (aliquot from aliquot, no depth limit)
- FR13: Aliquot inherits material reference, maintains independent quantity/location

**Consumption & Usage:**
- FR14: Decrement consumable batch from batch management interface
- FR15: View confirmation and updated quantity after actions
- FR16: Non-consumable usage references captured ONLY in Note-linked actions

**Note-Linked Actions:**
- FR17: Open inventory tool from Constellab Note
- FR18: Select batch from inventory within Note context
- FR19: Perform consumption action on consumable batch (decrement)
- FR20: Perform usage reference on non-consumable batch (no decrement)
- FR21: Link action to Note with batch details
- FR22: Note captures traceability (material, batch, parent chain, quantities, units)

**Supplier Management:**
- FR23: Create supplier with name, contact info
- FR24: Edit supplier details
- FR25: View supplier list
- FR26: Delete unused suppliers

**Location Management:**
- FR27: Create location with name, description
- FR28: Edit location details
- FR29: View location list
- FR30: Delete unused locations
- FR31: System assigns default "labo" location if not specified

**Integration:**
- FR32: Access app via Constellab auth/session
- FR33: Inventory tool embeds in Constellab Notes

**Units & Consistency:**
- FR34: Select quantities in supported units (volume, mass, length, count)
- FR35: Display units on all quantities (no auto-conversion in MVP)
- FR36: Enforce referential integrity (batch→material, batch→location, aliquot→parent)

### Non-Functional Requirements

**Performance:**
- NFR1: Typical actions (add/move/aliquot/consume) complete without long blocking
- NFR2: Views refresh after actions; no realtime websockets in MVP

**Reliability:**
- NFR3: Actions apply atomically; inventory and Note linkages remain consistent
- NFR4: Simple concurrency checks prevent conflicting updates
- NFR5: Referential integrity enforced at database level

**Integration:**
- NFR6: Reuse Constellab auth/session via CurrentUserService
- NFR7: Embed inventory tool within Notes seamlessly
- NFR8: Follow gws_project backend/frontend patterns strictly

**Testing:**
- NFR9: Service-layer tests via pytest for ALL operations
- NFR10: Backend tests MUST pass before frontend development starts

**Data Management:**
- NFR11: Store quantities in base units (L, kg, m, units) with DECIMAL(20,12) precision
- NFR12: Convert units at application layer via utils/units.py
- NFR13: Audit fields on ALL tables (created_by_id, last_modified_by_id, timestamps)

---

## Technology Stack

- **Framework:** Python Reflex (latest)
- **Database:** MariaDB (production), SQLite (dev) via Peewee ORM
- **ORM:** `gws_core.Model` and `ModelWithUser`
- **Auth:** Constellab platform (`CurrentUserService`)
- **Reference:** `gws_project` repository (MUST follow patterns)
- **Testing:** pytest with service-layer focus

---

# PHASE 1: BACKEND EPICS (1-7)

---

## Epic 1: Core Infrastructure & Database Entities

**Goal:** Establish database schema with 5 core entities following gws_project patterns.

**Dependencies:** None (starting point)

**Definition of Done:**
- All 5 entities defined as Peewee models
- Audit fields on ALL tables
- Database initialization working
- Default "labo" location seeded
- All models tested for basic CRUD

### Story 1.1: Study gws_project Backend Structure

**As a** developer  
**I want to** study the gws_project repository backend patterns  
**So that** I follow established conventions for entities and services

**Acceptance Criteria:**
- Review gws_project entity definitions (Model, ModelWithUser)
- Document naming conventions (snake_case tables, columns)
- Identify service patterns (CRUD operations)
- Understand test structure
- Create reference notes for team

**Technical Notes:**
- Reference: `gws_project` repository
- Focus on: entity structure, service layer, testing patterns

---

### Story 1.2: Define Material Entity

**As a** developer  
**I want to** create the Material entity with all required fields  
**So that** we can catalog all lab materials (chemicals, instruments, samples)

**Acceptance Criteria:**
- Create `src/gws_eln/materials/material.py`
- Fields: id, name, description, supplier_id (FK), is_consumable, default_unit_type
- Audit fields: created_by_id, last_modified_by_id, created_at, last_modified_at
- Indices: supplier_id, is_consumable, name
- Model extends `gws_core.ModelWithUser`
- Unit test for entity creation

**Technical Notes:**
- Table name: `materials` (plural, snake_case)
- is_consumable: Boolean (TRUE=consumable, FALSE=non-consumable)
- default_unit_type: ENUM('volume', 'mass', 'length', 'count')

---

### Story 1.3: Define Material_Batch Entity

**As a** developer  
**I want to** create the Material_Batch entity  
**So that** we can track physical instances and aliquots

**Acceptance Criteria:**
- Create `src/gws_eln/materials/material_batch.py`
- Fields: id, material_id (FK), parent_batch_id (self-FK), batch_number, label, expiry_date, quantity, unit_type, location_id (FK), notes
- Audit fields included
- Indices: material_id, parent_batch_id, location_id, batch_number, expiry_date
- Self-reference constraint for aliquots
- Unit test for batch creation and parent linkage

**Technical Notes:**
- Table name: `material_batches` (plural, snake_case)
- quantity: DECIMAL(20,12) stored in base units
- parent_batch_id NULL = original batch; NOT NULL = aliquot

---

### Story 1.4: Define Supplier Entity

**As a** developer  
**I want to** create the Supplier entity  
**So that** we can manage material suppliers

**Acceptance Criteria:**
- Create `src/gws_eln/suppliers/supplier.py`
- Fields: id, name (UNIQUE), description
- Audit fields included
- Index: name (unique)
- Unit test for supplier creation

**Technical Notes:**
- Table name: `suppliers` (plural, snake_case)

---

### Story 1.5: Define Location Entity

**As a** developer  
**I want to** create the Location entity  
**So that** we can manage storage locations

**Acceptance Criteria:**
- Create `src/gws_eln/locations/location.py`
- Fields: id, name (UNIQUE), description
- Audit fields included
- Index: name (unique)
- Unit test for location creation

**Technical Notes:**
- Table name: `locations` (plural, snake_case)
- Default location "labo" must be seeded

---

### Story 1.6: Define Activity Entity

**As a** developer  
**I want to** create the Activity entity  
**So that** we can log all inventory actions for audit trail

**Acceptance Criteria:**
- Create `src/gws_eln/activities/activity.py`
- Fields: id, activity_type (ENUM), entity_type, entity_id (FK), related_entity_id, quantity, unit_type, from_location_id (FK), to_location_id (FK), reason, notes, note_id
- Audit fields included
- Indices: entity_id, created_at DESC, activity_type, note_id, related_entity_id
- Unit test for activity creation

**Technical Notes:**
- Table name: `activities` (plural, snake_case)
- activity_type ENUM: 'receive', 'move', 'consume', 'use', 'discard', 'aliquot', 'relabel'
- entity_type: always 'material_batch' in MVP

---

### Story 1.7: Seed Default Data

**As a** developer  
**I want to** seed default location and example data  
**So that** the system is ready for development

**Acceptance Criteria:**
- Create seed script: `src/gws_eln/core/seed_data.py`
- Seed default location "labo"
- Seed 3 example suppliers
- Seed 5 example materials (mix of consumable/non-consumable)
- Seed 2 example batches
- Script is idempotent (can run multiple times safely)

**Technical Notes:**
- Run via: `gws server test` or startup hook

---

## Epic 2: Units System & Validators

**Goal:** Implement base unit conversion and validation logic.

**Dependencies:** Epic 1 (entities defined)

**Definition of Done:**
- utils/units.py with full conversion logic
- All unit types supported (volume, mass, length, count)
- Validators for quantity/unit constraints
- 100% test coverage for conversions

### Story 2.1: Implement Base Unit Conversion

**As a** developer  
**I want to** implement unit conversion functions  
**So that** quantities are stored in base units (L, kg, m, units)

**Acceptance Criteria:**
- Create `src/gws_eln/utils/units.py`
- Function: `to_base_unit(value, from_unit, unit_type)` → base unit value
- Function: `from_base_unit(value, to_unit, unit_type)` → user-friendly unit
- Support volume: L, mL, µL
- Support mass: kg, g, mg, µg
- Support length: m, cm, mm
- Support count: units (1:1)
- Return DECIMAL precision (20,12)

**Technical Notes:**
- Conversion examples:
  - 1 mL → 0.001 L
  - 1 g → 0.001 kg
  - 1 cm → 0.01 m

---

### Story 2.2: Unit Conversion Tests

**As a** developer  
**I want to** write comprehensive tests for unit conversions  
**So that** conversion accuracy is guaranteed

**Acceptance Criteria:**
- Create `tests/test_units.py`
- Test all volume conversions (L ↔ mL ↔ µL)
- Test all mass conversions (kg ↔ g ↔ mg ↔ µg)
- Test all length conversions (m ↔ cm ↔ mm)
- Test count (1:1 pass-through)
- Test precision edge cases
- Test invalid unit handling
- 100% coverage on units.py

---

### Story 2.3: Quantity & Unit Validators

**As a** developer  
**I want to** create validators for quantity and unit inputs  
**So that** invalid data is rejected early

**Acceptance Criteria:**
- Create `src/gws_eln/utils/validators.py`
- Validator: `validate_quantity(value)` → positive numbers only
- Validator: `validate_unit_type(unit_type, unit)` → unit matches type
- Validator: `validate_batch_operation(batch, quantity, operation)` → prevent negative stock
- Unit tests for all validators

**Technical Notes:**
- Reject: negative quantities, zero decrements, invalid unit/type combos

---

## Epic 3: Service Layer - Suppliers & Locations

**Goal:** Implement CRUD services for Suppliers and Locations.

**Dependencies:** Epic 1 (entities), Epic 2 (validators)

**Definition of Done:**
- SupplierService with full CRUD
- LocationService with full CRUD
- Default "labo" location enforcement
- All service methods tested

### Story 3.1: Supplier Service Implementation

**As a** developer  
**I want to** implement SupplierService with CRUD operations  
**So that** suppliers can be managed programmatically

**Acceptance Criteria:**
- Create `src/gws_eln/suppliers/supplier_service.py`
- Method: `create_supplier(name, description, user_id)` → Supplier
- Method: `get_supplier(supplier_id)` → Supplier
- Method: `list_suppliers()` → List[Supplier]
- Method: `update_supplier(supplier_id, name, description, user_id)` → Supplier
- Method: `delete_supplier(supplier_id, user_id)` → bool (prevent if referenced)
- Enforce unique name constraint
- Track created_by_id, last_modified_by_id

**Technical Notes:**
- Follow gws_project service patterns
- Delete only if no materials reference supplier

---

### Story 3.2: Supplier Service Tests

**As a** developer  
**I want to** write tests for SupplierService  
**So that** all operations are validated

**Acceptance Criteria:**
- Create `tests/test_supplier_service.py`
- Test: create supplier with valid data
- Test: create supplier with duplicate name (fails)
- Test: update supplier
- Test: delete unused supplier (succeeds)
- Test: delete referenced supplier (fails)
- Test: list all suppliers

---

### Story 3.3: Location Service Implementation

**As a** developer  
**I want to** implement LocationService with CRUD operations  
**So that** locations can be managed programmatically

**Acceptance Criteria:**
- Create `src/gws_eln/locations/location_service.py`
- Method: `create_location(name, description, user_id)` → Location
- Method: `get_location(location_id)` → Location
- Method: `get_default_location()` → Location (returns "labo")
- Method: `list_locations()` → List[Location]
- Method: `update_location(location_id, name, description, user_id)` → Location
- Method: `delete_location(location_id, user_id)` → bool (prevent if referenced)
- Enforce unique name constraint
- Ensure "labo" location exists on startup

**Technical Notes:**
- Default location "labo" cannot be deleted
- Delete only if no batches reference location

---

### Story 3.4: Location Service Tests

**As a** developer  
**I want to** write tests for LocationService  
**So that** all operations are validated

**Acceptance Criteria:**
- Create `tests/test_location_service.py`
- Test: create location with valid data
- Test: create location with duplicate name (fails)
- Test: get default "labo" location
- Test: update location
- Test: delete unused location (succeeds)
- Test: delete referenced location (fails)
- Test: delete "labo" location (fails)
- Test: list all locations

---

## Epic 4: Service Layer - Materials

**Goal:** Implement CRUD service for Materials with consumable/non-consumable logic.

**Dependencies:** Epic 3 (Supplier service for FK validation)

**Definition of Done:**
- MaterialService with full CRUD
- Support for all material types (chemicals, instruments, samples)
- Consumable flag logic working
- All operations tested

### Story 4.1: Material Service Implementation

**As a** developer  
**I want to** implement MaterialService with CRUD operations  
**So that** materials can be managed programmatically

**Acceptance Criteria:**
- Create `src/gws_eln/materials/material_service.py`
- Method: `create_material(name, description, supplier_id, is_consumable, default_unit_type, user_id)` → Material
- Method: `get_material(material_id)` → Material
- Method: `list_materials(filter_consumable=None)` → List[Material]
- Method: `update_material(material_id, name, description, supplier_id, is_consumable, default_unit_type, user_id)` → Material
- Method: `delete_material(material_id, user_id)` → bool (prevent if batches exist)
- Validate supplier_id exists if provided
- Track audit fields

**Technical Notes:**
- is_consumable: TRUE (chemicals/reagents/samples), FALSE (instruments/equipment)
- Delete only if no batches reference material

---

### Story 4.2: Material Service Tests

**As a** developer  
**I want to** write tests for MaterialService  
**So that** all operations are validated

**Acceptance Criteria:**
- Create `tests/test_material_service.py`
- Test: create consumable material (chemical)
- Test: create non-consumable material (instrument)
- Test: create material with supplier reference
- Test: create material with invalid supplier (fails)
- Test: update material metadata
- Test: list materials with consumable filter
- Test: delete unused material (succeeds)
- Test: delete material with batches (fails)

---

## Epic 5: Service Layer - Material Batches

**Goal:** Implement batch management: create, receive, increment, decrement, move.

**Dependencies:** Epic 4 (Material service), Epic 3 (Location service)

**Definition of Done:**
- MaterialBatchService with full operations
- Quantity tracking (increment/decrement for consumables)
- Location assignment and movement
- All operations tested

### Story 5.1: Material Batch Service - Create & Receive

**As a** developer  
**I want to** implement batch creation and receive operations  
**So that** physical inventory can be tracked

**Acceptance Criteria:**
- Create `src/gws_eln/materials/material_batch_service.py`
- Method: `create_batch(material_id, batch_number, quantity, unit_type, location_id, expiry_date, notes, user_id)` → Material_Batch
- Method: `receive_batch(batch_id, quantity, unit_type, user_id)` → Material_Batch (increments quantity)
- Validate: material_id exists
- Validate: location_id exists (default to "labo" if NULL)
- Convert quantity to base units before storage
- Create 'receive' activity entry
- Track audit fields

**Technical Notes:**
- parent_batch_id is NULL for original batches
- Use utils/units.py for conversion

---

### Story 5.2: Material Batch Service - Increment/Decrement

**As a** developer  
**I want to** implement increment and decrement operations  
**So that** stock levels can be adjusted

**Acceptance Criteria:**
- Method: `increment_quantity(batch_id, quantity, unit_type, reason, user_id)` → Material_Batch
- Method: `decrement_quantity(batch_id, quantity, unit_type, reason, user_id)` → Material_Batch
- Validate: batch exists and is consumable
- Validate: quantity is positive
- Validate: decrement doesn't result in negative stock
- Convert to base units
- Create 'consume' activity for decrement
- Return updated batch with new quantity

**Technical Notes:**
- Decrement only allowed for consumable materials (is_consumable=TRUE)
- Non-consumables cannot be decremented

---

### Story 5.3: Material Batch Service - Move Location

**As a** developer  
**I want to** implement batch movement between locations  
**So that** inventory can be reorganized

**Acceptance Criteria:**
- Method: `move_batch(batch_id, to_location_id, user_id)` → Material_Batch
- Validate: batch exists
- Validate: to_location_id exists
- Update batch.location_id
- Create 'move' activity with from_location_id and to_location_id
- Track audit fields

---

### Story 5.4: Material Batch Service - View & Delete

**As a** developer  
**I want to** implement view and delete operations  
**So that** batch lifecycle is complete

**Acceptance Criteria:**
- Method: `get_batch(batch_id)` → Material_Batch (with material, supplier, location joins)
- Method: `list_batches(material_id=None, location_id=None)` → List[Material_Batch]
- Method: `delete_batch(batch_id, reason, user_id)` → bool
- Delete: prevent if batch has child aliquots
- Delete: create 'discard' activity with reason
- Return batch with full details (material name, supplier name, location name)

**Technical Notes:**
- Delete only if no child aliquots (parent_batch_id references)

---

### Story 5.5: Material Batch Service Tests

**As a** developer  
**I want to** write comprehensive tests for MaterialBatchService  
**So that** all operations are validated

**Acceptance Criteria:**
- Create `tests/test_material_batch_service.py`
- Test: create batch with valid material and location
- Test: create batch with default "labo" location
- Test: receive batch (increment quantity)
- Test: increment consumable batch
- Test: decrement consumable batch (valid)
- Test: decrement non-consumable batch (fails)
- Test: decrement below zero (fails)
- Test: move batch to new location
- Test: delete batch without children (succeeds)
- Test: delete batch with aliquots (fails)
- Test: list batches by material
- Test: list batches by location

---

## Epic 6: Service Layer - Aliquots & Lineage

**Goal:** Implement multi-level aliquot creation with supplier inheritance and lineage tracking.

**Dependencies:** Epic 5 (Batch service)

**Definition of Done:**
- Aliquot creation working (multi-level)
- Supplier inheritance from parent batch
- Lineage queries functional
- Relabel without breaking lineage
- All operations tested

### Story 6.1: Aliquot Creation Service

**As a** developer  
**I want to** implement aliquot creation from parent batches  
**So that** derived samples can be tracked with lineage

**Acceptance Criteria:**
- Add to MaterialBatchService:
- Method: `create_aliquot(parent_batch_id, quantity, unit_type, label, location_id, user_id)` → Material_Batch
- Validate: parent batch exists
- Create new batch with parent_batch_id set
- Inherit material_id from parent
- Inherit supplier_id from parent's material
- If parent is consumable: decrement parent quantity
- Set location_id (or default to parent location)
- Create 'aliquot' activity linking parent and child
- Support multi-level: aliquot can itself be parent

**Technical Notes:**
- parent_batch_id → child_batch.parent_batch_id
- Supplier inheritance: child inherits from parent's material.supplier_id
- No depth limit for aliquots

---

### Story 6.2: Lineage Query Service

**As a** developer  
**I want to** implement lineage tracking queries  
**So that** parent-child chains can be visualized

**Acceptance Criteria:**
- Add to MaterialBatchService:
- Method: `get_lineage(batch_id)` → dict with 'ancestors' and 'descendants'
- Query ancestors: traverse parent_batch_id recursively
- Query descendants: find all batches with parent_batch_id = batch_id recursively
- Return full chain with batch details (label, quantity, location)
- Include activity history for lineage events

**Technical Notes:**
- Recursive SQL or iterative traversal
- Return format: `{'ancestors': [...], 'descendants': [...]}`

---

### Story 6.3: Relabel Batch Without Breaking Lineage

**As a** developer  
**I want to** implement batch relabeling  
**So that** labels can be updated without losing lineage

**Acceptance Criteria:**
- Add to MaterialBatchService:
- Method: `relabel_batch(batch_id, new_label, user_id)` → Material_Batch
- Update batch.label
- parent_batch_id remains unchanged
- Create 'relabel' activity
- Track audit fields

---

### Story 6.4: Aliquot Service Tests

**As a** developer  
**I want to** write tests for aliquot operations  
**So that** lineage integrity is validated

**Acceptance Criteria:**
- Create `tests/test_aliquot_service.py`
- Test: create aliquot from parent batch
- Test: create multi-level aliquot (aliquot from aliquot)
- Test: supplier inheritance in aliquots
- Test: parent quantity decrements if consumable
- Test: parent quantity unchanged if non-consumable
- Test: get lineage for batch with ancestors
- Test: get lineage for batch with descendants
- Test: relabel batch preserves parent_batch_id
- Test: create aliquot with invalid parent (fails)

---

## Epic 7: Activity Service & Audit Log

**Goal:** Implement activity logging and history queries with Note integration.

**Dependencies:** Epic 6 (all batch operations complete)

**Definition of Done:**
- ActivityService with logging for all 7 activity types
- Note linkage (note_id) working
- History queries functional
- All operations tested

### Story 7.1: Activity Service Implementation

**As a** developer  
**I want to** implement ActivityService for logging all inventory actions  
**So that** complete audit trail is maintained

**Acceptance Criteria:**
- Create `src/gws_eln/activities/activity_service.py`
- Method: `log_activity(activity_type, entity_id, quantity, unit_type, from_location_id, to_location_id, reason, notes, note_id, related_entity_id, user_id)` → Activity
- Support all 7 types: receive, move, consume, use, discard, aliquot, relabel
- Convert quantity to base units
- Track audit fields
- Note: 'use' activity ONLY created from Note context (note_id required)

**Technical Notes:**
- activity_type ENUM validation
- entity_type is always 'material_batch' in MVP

---

### Story 7.2: Activity History Queries

**As a** developer  
**I want to** implement activity history queries  
**So that** users can view action timelines

**Acceptance Criteria:**
- Add to ActivityService:
- Method: `get_batch_history(batch_id)` → List[Activity] (ordered by created_at DESC)
- Method: `get_note_activities(note_id)` → List[Activity] (all actions linked to note)
- Method: `list_activities(activity_type=None, start_date=None, end_date=None)` → List[Activity]
- Include related entities: batch details, locations, user info
- Support pagination

---

### Story 7.3: Note-Linked Activity Integration

**As a** developer  
**I want to** implement Note-specific activity handling  
**So that** inventory actions link to Constellab Notes

**Acceptance Criteria:**
- Add to ActivityService:
- Method: `log_note_activity(note_id, batch_id, activity_type, quantity, unit_type, user_id)` → Activity
- Validate: activity_type is 'consume' or 'use'
- Validate: 'use' requires non-consumable material
- Validate: 'consume' requires consumable material
- Set note_id field
- For 'consume': decrement batch quantity via MaterialBatchService
- For 'use': log reference only (no quantity change)

**Technical Notes:**
- 'use' activity ONLY available in Note context
- 'consume' can be done standalone OR in Note context

---

### Story 7.4: Activity Service Tests

**As a** developer  
**I want to** write tests for ActivityService  
**So that** audit logging is validated

**Acceptance Criteria:**
- Create `tests/test_activity_service.py`
- Test: log activity for each of 7 types
- Test: get batch history (chronological)
- Test: get activities by note_id
- Test: log_note_activity with 'use' on non-consumable (succeeds)
- Test: log_note_activity with 'use' on consumable (fails)
- Test: log_note_activity with 'consume' on consumable (succeeds)
- Test: list activities with filters (type, date range)
- Test: activity includes related entity details

---

# PHASE 2: FRONTEND EPICS (8-12)

**⚠️ CRITICAL: Do NOT start Phase 2 until ALL Phase 1 tests pass**

---

## Epic 8: Reflex UI Foundation

**Goal:** Establish Reflex project structure following gws_project patterns.

**Dependencies:** ALL Phase 1 epics complete with passing tests

**Definition of Done:**
- Reflex app initializes correctly
- Auth integration via CurrentUserService working
- Base layouts and components ready
- Routing structure established

### Story 8.1: Study gws_project Reflex Structure

**As a** developer  
**I want to** study gws_project Reflex frontend patterns  
**So that** UI follows established conventions

**Acceptance Criteria:**
- Review gws_project Reflex structure (pages, states, components)
- Document routing patterns
- Identify reusable components
- Understand state management
- Create reference notes for team

---

### Story 8.2: Initialize Reflex Project

**As a** developer  
**I want to** initialize the Reflex project structure  
**So that** the frontend foundation is ready

**Acceptance Criteria:**
- Create `src/gws_eln/project_app/_project_app/rxconfig.py`
- Configure GWS_REFLEX_API_URL
- Create base directory structure: pages/, states/, components/
- Test: `gws reflex run` command starts successfully
- Auth via CurrentUserService working

**Technical Notes:**
- Follow gws_project directory layout
- Use gws_core.CurrentUserService for user context

---

### Story 8.3: Base Layout & Navigation

**As a** developer  
**I want to** create base layout components  
**So that** consistent UI structure is established

**Acceptance Criteria:**
- Create `components/layout.py` with header, sidebar, main content
- Create navigation menu with links to: Materials, Batches, Suppliers, Locations, Activities
- Responsive layout (desktop-first)
- Consistent styling (follow Constellab design)

---

### Story 8.4: Reusable Form Components

**As a** developer  
**I want to** create reusable form components  
**So that** forms are consistent across pages

**Acceptance Criteria:**
- Create `components/forms.py`
- Component: TextInput (with validation)
- Component: SelectInput (dropdown)
- Component: NumberInput (with unit picker)
- Component: DateInput
- Component: TextArea
- All components support error states

---

## Epic 9: Material & Batch Management UI

**Goal:** Build UI for creating/viewing/editing materials and batches.

**Dependencies:** Epic 8 (UI foundation)

**Definition of Done:**
- Material CRUD pages functional
- Batch CRUD pages functional
- Quantity input with unit conversion working
- Increment/decrement/move flows complete

### Story 9.1: Material List Page

**As a** lab user  
**I want to** view all materials in a list  
**So that** I can browse the catalog

**Acceptance Criteria:**
- Create `pages/materials/list.py`
- Display: material name, type (consumable/non-consumable), supplier
- Filter: by consumable flag
- Search: by name
- Actions: Create New, Edit, Delete (if unused)
- Click material → navigate to detail page

**Technical Notes:**
- Use MaterialService.list_materials()

---

### Story 9.2: Material Create/Edit Form

**As a** lab user  
**I want to** create or edit a material  
**So that** I can manage the catalog

**Acceptance Criteria:**
- Create `pages/materials/form.py`
- Form fields: name, description, supplier (dropdown), is_consumable (toggle), default_unit_type (dropdown)
- Validation: required fields, unique name
- On submit: call MaterialService.create_material() or update_material()
- Success: show confirmation, navigate to list
- Error: display inline errors

---

### Story 9.3: Material Detail Page

**As a** lab user  
**I want to** view material details with associated batches  
**So that** I can see complete inventory

**Acceptance Criteria:**
- Create `pages/materials/detail.py`
- Display: material metadata, supplier info
- Display: list of batches (batch_number, location, quantity, expiry)
- Actions: Edit Material, Create Batch, View Batch

---

### Story 9.4: Batch List Page

**As a** lab user  
**I want to** view all batches with filtering  
**So that** I can find inventory quickly

**Acceptance Criteria:**
- Create `pages/batches/list.py`
- Display: batch_number, material name, location, quantity + unit, expiry_date
- Filter: by material, by location
- Search: by batch_number or label
- Actions: Create New, View Details, Move, Delete
- Click batch → navigate to detail page

---

### Story 9.5: Batch Create/Receive Form

**As a** lab user  
**I want to** create a new batch (receive inventory)  
**So that** incoming materials are tracked

**Acceptance Criteria:**
- Create `pages/batches/receive.py`
- Form fields: material (dropdown), batch_number, quantity (with unit picker), location (dropdown with "labo" default), expiry_date, notes
- Unit picker: shows appropriate units based on material.default_unit_type
- On submit: call MaterialBatchService.create_batch()
- Quantity converted to base units automatically
- Success: show confirmation with batch ID

---

### Story 9.6: Batch Detail Page with Actions

**As a** lab user  
**I want to** view batch details and perform actions  
**So that** I can manage inventory

**Acceptance Criteria:**
- Create `pages/batches/detail.py`
- Display: batch info, material info, current location, quantity + unit, parent batch (if aliquot)
- Actions for consumable batches: Increment Quantity, Decrement Quantity, Create Aliquot
- Actions for all batches: Move Location, Relabel, Delete (if no children)
- Show activity history timeline
- Show lineage (ancestors and descendants)

---

### Story 9.7: Quantity Adjustment Forms

**As a** lab user  
**I want to** increment or decrement batch quantities  
**So that** stock levels stay accurate

**Acceptance Criteria:**
- Create `components/quantity_adjustment.py`
- Increment form: quantity + unit, reason (optional)
- Decrement form: quantity + unit, reason (required)
- Validation: positive numbers, no negative stock
- On submit: call MaterialBatchService.increment_quantity() or decrement_quantity()
- Display: current quantity before and after
- Success: refresh batch details

**Technical Notes:**
- Decrement only enabled for consumable materials

---

### Story 9.8: Move Batch Dialog

**As a** lab user  
**I want to** move a batch to a different location  
**So that** inventory organization is maintained

**Acceptance Criteria:**
- Create `components/move_batch_dialog.py`
- Display: current location
- Form: select new location (dropdown)
- On submit: call MaterialBatchService.move_batch()
- Success: refresh batch details, show new location
- Activity logged automatically

---

## Epic 10: Suppliers & Locations UI

**Goal:** Build CRUD pages for Suppliers and Locations.

**Dependencies:** Epic 8 (UI foundation)

**Definition of Done:**
- Supplier CRUD pages functional
- Location CRUD pages functional
- Selection pickers integrated into forms

### Story 10.1: Supplier List & CRUD Pages

**As a** lab user  
**I want to** manage suppliers  
**So that** supplier catalog stays current

**Acceptance Criteria:**
- Create `pages/suppliers/list.py`: display all suppliers, Create/Edit/Delete actions
- Create `pages/suppliers/form.py`: name, description fields
- Validation: unique name
- Delete: prevent if referenced by materials
- On submit: call SupplierService methods

---

### Story 10.2: Location List & CRUD Pages

**As a** lab user  
**I want to** manage locations  
**So that** storage organization is maintained

**Acceptance Criteria:**
- Create `pages/locations/list.py`: display all locations, Create/Edit/Delete actions
- Create `pages/locations/form.py`: name, description fields
- Validation: unique name
- Delete: prevent if referenced by batches or if name = "labo"
- On submit: call LocationService methods

---

### Story 10.3: Supplier & Location Pickers

**As a** developer  
**I want to** create reusable supplier and location picker components  
**So that** forms have consistent selection UI

**Acceptance Criteria:**
- Create `components/supplier_picker.py`: dropdown with search
- Create `components/location_picker.py`: dropdown with "labo" default highlighted
- Both integrate with form validation
- Load data via services on component mount

---

## Epic 11: Aliquots & Lineage UI

**Goal:** Build UI for aliquot creation and lineage visualization.

**Dependencies:** Epic 9 (batch UI)

**Definition of Done:**
- Aliquot creation form functional
- Lineage viewer component working
- Multi-level navigation supported

### Story 11.1: Aliquot Creation Form

**As a** lab user  
**I want to** create an aliquot from a parent batch  
**So that** derived samples are tracked

**Acceptance Criteria:**
- Create `pages/batches/create_aliquot.py`
- Display: parent batch info (material, quantity, location)
- Form fields: quantity (with unit picker), label, location (defaults to parent location)
- Validation: positive quantity, doesn't exceed parent if consumable
- On submit: call MaterialBatchService.create_aliquot()
- Success: navigate to new aliquot detail page
- Activity logged automatically

**Technical Notes:**
- Multi-level supported: aliquot can itself be parent

---

### Story 11.2: Lineage Viewer Component

**As a** lab user  
**I want to** view lineage (ancestors and descendants) for a batch  
**So that** provenance is clear

**Acceptance Criteria:**
- Create `components/lineage_viewer.py`
- Display ancestors: parent → grandparent → ... (recursive)
- Display descendants: children → grandchildren → ... (recursive)
- Each node shows: label, batch_number, quantity, location
- Click node → navigate to batch detail
- Use MaterialBatchService.get_lineage()

**Technical Notes:**
- Tree or list view (MVP can be simple list)
- Highlight current batch

---

### Story 11.3: Relabel Batch Form

**As a** lab user  
**I want to** relabel a batch  
**So that** identification is updated without losing lineage

**Acceptance Criteria:**
- Create `components/relabel_batch_dialog.py`
- Display: current label
- Form: new label (text input)
- On submit: call MaterialBatchService.relabel_batch()
- Success: refresh batch details
- Lineage preserved (parent_batch_id unchanged)

---

## Epic 12: Activity Log & Note Integration

**Goal:** Build activity history viewer and Note context integration.

**Dependencies:** Epic 9 (batch UI), Epic 7 (Activity service)

**Definition of Done:**
- Activity log page functional
- Note-linked action interface working
- 'use' activity only available in Note context

### Story 12.1: Activity Log Page

**As a** lab user  
**I want to** view a chronological log of all inventory activities  
**So that** I can audit changes

**Acceptance Criteria:**
- Create `pages/activities/log.py`
- Display: timestamp, activity_type, user, entity (batch), quantity, locations, reason
- Filter: by activity_type, date range, user
- Search: by batch_number or material name
- Pagination support
- Use ActivityService.list_activities()

---

### Story 12.2: Batch Activity Timeline

**As a** lab user  
**I want to** view activity history for a specific batch  
**So that** I can see its complete timeline

**Acceptance Criteria:**
- Add to batch detail page (Story 9.6)
- Component: `components/batch_timeline.py`
- Display: all activities for batch (ordered by created_at DESC)
- Show: activity type icon, timestamp, user, quantity change, location change, notes
- Highlight: Note-linked activities with note_id
- Use ActivityService.get_batch_history()

---

### Story 12.3: Note Context Action Interface

**As a** lab user  
**I want to** perform inventory actions from a Constellab Note  
**So that** actions link to my experimental notes

**Acceptance Criteria:**
- Create `pages/note_actions/inventory_tool.py` (embedded in Note)
- Display: batch selector (dropdown with search)
- For consumable batches: show "Consume" action with quantity input
- For non-consumable batches: show "Use" action (reference only)
- On submit:
  - Consumable → call ActivityService.log_note_activity('consume', ...)
  - Non-consumable → call ActivityService.log_note_activity('use', ...)
- Pass note_id from Note context
- Success: show confirmation, update Note with linked action

**Technical Notes:**
- 'use' activity ONLY available in this interface
- Embedded via Constellab Notes integration

---

### Story 12.4: Note-Linked Activities Viewer

**As a** lab user  
**I want to** view all inventory actions linked to a Note  
**So that** I can see experimental inventory usage

**Acceptance Criteria:**
- Create `pages/note_actions/linked_activities.py` (embedded in Note)
- Display: all activities with note_id = current note
- Show: batch info (material name, batch_number), activity type, quantity, timestamp
- Click batch → navigate to batch detail (opens in new tab/context)
- Use ActivityService.get_note_activities()

---

## ✅ Completion Criteria

### Phase 1 (Backend) Complete When:
- All 5 entities defined and tested
- All service methods implemented
- 100% of backend tests passing
- Seed data script working
- Documentation for service APIs complete

### Phase 2 (Frontend) Complete When:
- All CRUD pages functional
- Aliquot creation and lineage working
- Note integration functional
- Manual testing checklist passed
- User acceptance testing complete

---

## 📋 Testing Strategy

### Backend Testing (Phase 1):
- Unit tests for each service method
- Integration tests for workflows (create material → create batch → create aliquot)
- Test consumable vs non-consumable behavior
- Test supplier inheritance in aliquots
- Test activity logging for all types
- Test concurrency scenarios

### Frontend Testing (Phase 2):
- Manual testing checklist for each page
- User acceptance testing for workflows
- Integration testing: UI → service → database
- Cross-browser testing (Chrome, Firefox, Safari, Edge)

---

**End of Epic Breakdown**
