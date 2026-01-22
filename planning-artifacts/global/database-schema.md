# Database Schema v2 - ELN Inventory System

**Version:** 2.0  
**Date:** 2026-01-21

## Overview

5 core entities with unified model - no separate tables for samples, instruments, units, or aliquots.

## Entity Definitions

### materials (Unified Product Catalog)

Handles ALL material types: chemicals, instruments, equipment, samples.

```
materials
├── id (PK, INT AUTO_INCREMENT)
├── name (VARCHAR(255), NOT NULL)
│   Examples: "Éthanol 99%", "Spectrophotomètre UV-Vis", "Échantillon Sang"
├── description (TEXT)
├── supplier_id (FK → suppliers.id, NULL)
│   Supplier's catalog number (e.g., "E7023")
├── is_consumable (BOOLEAN, NOT NULL)
│   TRUE: chemicals, reagents, samples → quantity decrements on use
│   FALSE: instruments, equipment → usage reference only
├── default_unit_type (ENUM: 'volume', 'mass', 'length', 'count', NOT NULL)
│   Default unit type for this material
├── created_by_id (FK → users.id)
├── last_modified_by_id (FK → users.id)
├── created_at (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)
└── last_modified_at (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP)
```

**Indices:**
```sql
CREATE INDEX idx_materials_supplier ON materials(supplier_id);
CREATE INDEX idx_materials_consumable ON materials(is_consumable);
CREATE INDEX idx_materials_name ON materials(name);
```

---

### material_batches (Unified Physical Inventory)

Handles: received batches, aliquots, instrument instances, sample instances.

```
material_batches
├── id (PK, INT AUTO_INCREMENT)
├── material_id (FK → materials.id, NOT NULL)
├── parent_batch_id (FK → material_batches.id, NULL)
│   NULL: original batch/instance
│   NOT NULL: aliquot/sub-batch (inherits supplier_id from parent)
├── batch_number (VARCHAR(100))
│   For received batches; NULL for aliquots
├── label (VARCHAR(255), NULL)
│   For aliquots or custom identification
├── expiry_date (DATE, NULL)
├── quantity (DECIMAL(20,12), NULL)
│   Stored in BASE UNITS (L, kg, m, units)
│   NULL for non-quantifiable items
├── unit_type (ENUM: 'volume', 'mass', 'length', 'count', NULL)
│   NULL if not applicable
├── location_id (FK → locations.id, NOT NULL)
├── notes (TEXT)
├── created_by_id (FK → users.id)
├── last_modified_by_id (FK → users.id)
├── created_at (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)
└── last_modified_at (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP)
```

**Indices:**
```sql
CREATE INDEX idx_material_batches_material ON material_batches(material_id);
CREATE INDEX idx_material_batches_parent ON material_batches(parent_batch_id);
CREATE INDEX idx_material_batches_location ON material_batches(location_id);
CREATE INDEX idx_material_batches_batch_number ON material_batches(batch_number);
CREATE INDEX idx_material_batches_expiry ON material_batches(expiry_date);
```

---

### suppliers (Material Suppliers)

```
suppliers
├── id (PK, INT AUTO_INCREMENT)
├── name (VARCHAR(255), NOT NULL, UNIQUE)
├── contact_info (TEXT)
│   Email, phone, address, etc.
├── created_by_id (FK → users.id)
├── last_modified_by_id (FK → users.id)
├── created_at (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)
└── last_modified_at (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP)
```

**Indices:**
```sql
CREATE UNIQUE INDEX idx_suppliers_name ON suppliers(name);
```

---

### locations (Storage Locations)

Simplified: just name and description.

```
locations
├── id (PK, INT AUTO_INCREMENT)
├── name (VARCHAR(255), NOT NULL, UNIQUE)
│   Examples: "labo", "Freezer -80C", "Shelf A1"
├── description (TEXT)
├── created_by_id (FK → users.id)
├── last_modified_by_id (FK → users.id)
├── created_at (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)
└── last_modified_at (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP)
```

**Indices:**
```sql
CREATE UNIQUE INDEX idx_locations_name ON locations(name);
```

**Default Location:**
- "labo" must be created at Constellab startup

---

### activities (Audit Log)

Tracks all inventory actions.

```
activities
├── id (PK, INT AUTO_INCREMENT)
├── activity_type (ENUM: 'receive', 'move', 'consume', 'use', 'discard', 'aliquot', 'relabel', NOT NULL)
│   - receive: New batch from supplier
│   - move: Change location
│   - consume: Use consumable (decrements quantity)
│   - use: Use non-consumable (reference only)
│   - discard: Remove with reason
│   - aliquot: Create child batch
│   - relabel: Change label
├── entity_type (ENUM: 'material_batch', NOT NULL)
│   Always 'material_batch' (simplified for MVP)
├── entity_id (FK → material_batches.id, NOT NULL)
│   The batch being acted upon
├── related_entity_id (INT, NULL)
│   For lineage: child aliquot ID, related batch ID
├── quantity (DECIMAL(20,12), NULL)
│   For quantity-based actions (consume, aliquot)
│   Stored in BASE UNITS
├── unit_type (ENUM: 'volume', 'mass', 'length', 'count', NULL)
│   NULL for non-quantity actions
├── from_location_id (FK → locations.id, NULL)
│   For 'move' actions
├── to_location_id (FK → locations.id, NULL)
│   For 'move' actions
├── reason (TEXT)
│   For 'discard' actions (required)
├── notes (TEXT)
├── note_id (VARCHAR(255), NULL)
│   Link to Constellab Note
├── created_by_id (FK → users.id)
├── last_modified_by_id (FK → users.id)
├── created_at (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)
└── last_modified_at (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP)
```

**Indices:**
```sql
CREATE INDEX idx_activities_entity ON activities(entity_id);
CREATE INDEX idx_activities_created_at ON activities(created_at DESC);
CREATE INDEX idx_activities_type ON activities(activity_type);
CREATE INDEX idx_activities_note ON activities(note_id);
CREATE INDEX idx_activities_related ON activities(related_entity_id);
```

---

## Relationships

```
suppliers 1:N materials (optional)
materials 1:N material_batches
material_batches 1:N material_batches (self-reference via parent_batch_id)
locations 1:N material_batches
activities N:1 material_batches (entity_id)
activities N:1 locations (from_location_id, to_location_id)
```

---

## Base Unit Storage

All quantities stored in base units:

| Type   | Base Unit | Examples                          |
|--------|-----------|-----------------------------------|
| volume | L         | 1 mL = 0.001 L, 1 µL = 0.000001 L |
| mass   | kg        | 1 g = 0.001 kg, 1 mg = 0.000001 kg|
| length | m         | 1 cm = 0.01 m, 1 mm = 0.001 m     |
| count  | units     | 1 unit = 1                        |

**Precision:** DECIMAL(20,12) for high precision calculations.

**Conversion:** All conversions handled in `utils/units.py` at application layer.

---

## Audit Fields

**All tables include:**
- `created_by_id` (FK → users.id)
- `last_modified_by_id` (FK → users.id)
- `created_at` (TIMESTAMP)
- `last_modified_at` (TIMESTAMP)

**Purpose:** Complete change tracking and audit trail.

---

## Key Behaviors

### Consumable vs Non-Consumable

**Determined by:** `materials.is_consumable`

**Consumable (TRUE):**
- Examples: chemicals, reagents, samples
- Behavior: `consume` activity decrements quantity
- Quantity tracking: required

**Non-Consumable (FALSE):**
- Examples: instruments, equipment
- Behavior: `use` activity records reference only (no decrement)
- Quantity tracking: optional/not applicable

### Aliquot Creation

1. Create new `material_batch` with `parent_batch_id` set
2. **Automatically inherit** `supplier_id` from parent batch's material
3. Decrement parent quantity (if consumable)
4. Log `aliquot` activity

### Lineage Tracking

- Parent → Child via `parent_batch_id` in `material_batches`
- Multi-level supported (child can become parent)
- Supplier inherited through chain

---

## Migrations

Located in: `src/gws_eln/migrations/`

**Initial migrations:**
1. `migration_0001_initial.py`: Create all tables
2. `migration_0002_seed_data.py`: Seed default location "labo", example materials, suppliers

**Pattern:** Follow `gws_project` versioned migration approach.

---

