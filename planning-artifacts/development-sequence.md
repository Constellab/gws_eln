# Development Sequence - ELN Inventory System

**Version:** 2.0  
**Date:** 2026-01-21

## Overview

**CRITICAL:** Backend-First Approach - Complete Phase 1 with passing tests before Phase 2.

---

## 🎯 Phase 1: Backend Development (MUST COMPLETE FIRST)

All backend services and tests must pass before starting frontend.

### Step 1: Study Reference Implementation

**Before writing any code:**
1. Clone and study `gws_project` repository
2. Understand backend structure:
   - Domain-driven organization (entities + services co-located)
   - Service patterns (CRUD, business logic)
   - Testing patterns
3. Understand core infrastructure:
   - Database manager setup
   - Base model classes with audit fields
   - Peewee ORM patterns

**Duration:** 2-4 hours  
**Output:** Understanding of gws_project patterns

---

### Step 2: Initialize Project

**Actions:**
1. Create brick structure following gws_project
2. Set up `core/` infrastructure:
   - `eln_db_manager.py` (DatabaseProxy)
   - `model_with_user.py` (base model with audit fields)
3. Configure `settings.json` (dependencies)
4. Set up test infrastructure

**Commands:**
```bash
# Navigate to brick
cd bricks/gws_eln

# Install dependencies (defined in settings.json)
gws brick install

# Initialize test database
pytest tests/ --setup-only
```

**Duration:** 2-3 hours  
**Output:** Working project scaffold, database manager

---

### Step 3: Implement Unit Conversion Utilities

**Location:** `src/gws_eln/utils/units.py`

**Required Functions:**
```python
def to_base_unit(quantity: float, unit: str, unit_type: str) -> Decimal:
    """Convert user unit to base unit (L, kg, m, units)."""
    pass

def from_base_unit(quantity_base: Decimal, unit_type: str) -> Tuple[float, str]:
    """Convert base unit to user-friendly display unit."""
    pass

CONVERSION_FACTORS = {
    'volume': {'L': 1, 'mL': 0.001, 'µL': 0.000001},
    'mass': {'kg': 1, 'g': 0.001, 'mg': 0.000001, 'µg': 0.000000001},
    'length': {'m': 1, 'cm': 0.01, 'mm': 0.001},
    'count': {'units': 1}
}
```

**Tests:** `tests/utils/test_unit_converter.py`
- Test all conversions (volume, mass, length, count)
- Test precision (DECIMAL vs FLOAT)
- Test invalid units
- Test edge cases (0, negative, very large)

**Duration:** 3-4 hours  
**Output:** Complete unit conversion with 100% test coverage

---

### Step 4: Implement Core Entities

**Order:** materials → suppliers → locations → activities

#### 4.1 Supplier Entity
**Location:** `src/gws_eln/suppliers/supplier.py`

```python
class Supplier(ModelWithUser):
    name = CharField(unique=True, max_length=255)
    contact_info = TextField(null=True)
    # audit fields inherited from ModelWithUser
```

**Tests:** `tests/suppliers/test_supplier_service.py`
- Create, read, update, delete
- Unique name constraint
- Audit fields populated

**Duration:** 2 hours

---

#### 4.2 Material Entity
**Location:** `src/gws_eln/materials/material.py`

```python
class Material(ModelWithUser):
    name = CharField(max_length=255)
    description = TextField(null=True)
    supplier = ForeignKeyField(Supplier, null=True, backref='materials')
    catalog_number = CharField(max_length=100, null=True)
    is_consumable = BooleanField()  # TRUE: chemicals/samples, FALSE: instruments
    default_unit_type = CharField(choices=['volume', 'mass', 'length', 'count'])
    # audit fields inherited
```

**Tests:** `tests/materials/test_material_service.py`
- Create consumables and non-consumables
- Supplier relationship
- Audit fields

**Duration:** 2-3 hours

---

#### 4.3 Location Entity
**Location:** `src/gws_eln/locations/location.py`

```python
class Location(ModelWithUser):
    name = CharField(unique=True, max_length=255)
    description = TextField(null=True)
    # audit fields inherited
```

**Tests:** `tests/locations/test_location_service.py`
- CRUD operations
- Unique name constraint
- Default "labo" location creation

**Duration:** 2 hours

---

#### 4.4 MaterialBatch Entity
**Location:** `src/gws_eln/materials/material_batch.py`

```python
class MaterialBatch(ModelWithUser):
    material = ForeignKeyField(Material, backref='batches')
    parent_batch = ForeignKeyField('self', null=True, backref='children')
    batch_number = CharField(max_length=100, null=True)
    label = CharField(max_length=255, null=True)
    expiry_date = DateField(null=True)
    quantity = DecimalField(max_digits=20, decimal_places=12, null=True)
    unit_type = CharField(choices=['volume', 'mass', 'length', 'count'], null=True)
    location = ForeignKeyField(Location, backref='batches')
    notes = TextField(null=True)
    # audit fields inherited
```

**Tests:** `tests/materials/test_material_batch_service.py`
- Create batches and aliquots
- Parent-child relationships
- Supplier inheritance
- Quantity precision

**Duration:** 3-4 hours

---

#### 4.5 Activity Entity
**Location:** `src/gws_eln/activities/activity.py`

```python
class Activity(ModelWithUser):
    activity_type = CharField(choices=['receive', 'move', 'consume', 'use', 'discard', 'aliquot', 'relabel'])
    entity_type = CharField(default='material_batch')
    entity_id = IntegerField()  # FK to material_batch
    related_entity_id = IntegerField(null=True)
    quantity = DecimalField(max_digits=20, decimal_places=12, null=True)
    unit_type = CharField(null=True)
    from_location = ForeignKeyField(Location, null=True, backref='activities_from')
    to_location = ForeignKeyField(Location, null=True, backref='activities_to')
    reason = TextField(null=True)
    notes = TextField(null=True)
    note_id = CharField(max_length=255, null=True)
    # audit fields inherited
```

**Tests:** `tests/activities/test_activity_service.py`
- Log all activity types
- Lineage tracking
- Note linkage

**Duration:** 3 hours

---

### Step 5: Implement Services

**Order:** Same as entities (suppliers → materials → locations → material_batches → activities)

#### 5.1 SupplierService
**Location:** `src/gws_eln/suppliers/supplier_service.py`

**Methods:**
- `create_supplier(name, contact_info) → Supplier`
- `get_supplier(supplier_id) → Supplier`
- `list_suppliers() → List[Supplier]`
- `update_supplier(supplier_id, **kwargs) → Supplier`
- `delete_supplier(supplier_id) → bool`

**Validation:**
- Unique name
- Required fields

**Duration:** 2-3 hours

---

#### 5.2 MaterialService
**Location:** `src/gws_eln/materials/material_service.py`

**Methods:**
- `create_material(name, is_consumable, default_unit_type, **kwargs) → Material`
- `get_material(material_id) → Material`
- `list_materials(is_consumable=None) → List[Material]`
- `update_material(material_id, **kwargs) → Material`
- `delete_material(material_id) → bool`

**Validation:**
- is_consumable flag required
- default_unit_type valid
- Supplier exists (if provided)

**Duration:** 3-4 hours

---

#### 5.3 LocationService
**Location:** `src/gws_eln/locations/location_service.py`

**Methods:**
- `create_location(name, description) → Location`
- `get_location(location_id) → Location`
- `list_locations() → List[Location]`
- `update_location(location_id, **kwargs) → Location`
- `delete_location(location_id) → bool`
- `ensure_default_location() → Location` (creates "labo" if not exists)

**Validation:**
- Unique name
- Default "labo" created at startup

**Duration:** 2-3 hours

---

#### 5.4 MaterialBatchService
**Location:** `src/gws_eln/materials/material_batch_service.py`

**MOST COMPLEX SERVICE**

**Methods:**

**Receive:**
```python
def receive_batch(material_id, batch_number, quantity, unit, location_id, **kwargs) → MaterialBatch:
    """
    Receive new batch from supplier.
    - Convert quantity to base unit
    - Create MaterialBatch
    - Log 'receive' activity
    """
```

**Consume (consumables only):**
```python
def consume_batch(batch_id, quantity, unit) → MaterialBatch:
    """
    Consume quantity from batch.
    - Verify is_consumable=TRUE
    - Convert quantity to base unit
    - Decrement batch.quantity
    - Log 'consume' activity
    """
```

**Use (non-consumables only):**
```python
def use_batch(batch_id) → Activity:
    """
    Log usage of non-consumable.
    - Verify is_consumable=FALSE
    - Log 'use' activity (no quantity change)
    """
```

**Move:**
```python
def move_batch(batch_id, to_location_id) → MaterialBatch:
    """
    Move batch to new location.
    - Update batch.location_id
    - Log 'move' activity
    """
```

**Aliquot:**
```python
def create_aliquot(parent_batch_id, quantity, unit, label, location_id) → MaterialBatch:
    """
    Create aliquot from parent batch.
    - Verify parent is consumable
    - Decrement parent quantity
    - Create child batch with parent_batch_id
    - Inherit supplier_id from parent.material.supplier_id
    - Log 'aliquot' activity
    """
```

**Discard:**
```python
def discard_batch(batch_id, reason, quantity=None, unit=None) → MaterialBatch:
    """
    Discard batch or partial quantity.
    - Decrement quantity (if partial)
    - Log 'discard' activity with reason
    """
```

**Relabel:**
```python
def relabel_batch(batch_id, new_label) → MaterialBatch:
    """
    Change batch label.
    - Update batch.label
    - Log 'relabel' activity
    """
```

**Lineage:**
```python
def get_lineage(batch_id) → Dict:
    """
    Get parent-child lineage tree.
    - Traverse parent_batch_id relationships
    - Return hierarchical structure
    """
```

**Validation:**
- Consumable flag consistency
- Quantity sufficiency
- Location existence
- Unit type consistency
- Supplier inheritance

**Tests:** Comprehensive coverage
- All material types (consumables, non-consumables)
- Aliquot creation with supplier inheritance
- Multi-level lineage
- Edge cases (zero quantity, no quantity items)

**Duration:** 8-10 hours (most complex)

---

#### 5.5 ActivityService
**Location:** `src/gws_eln/activities/activity_service.py`

**Methods:**
- `log_activity(activity_type, entity_id, **kwargs) → Activity`
- `get_activities_for_batch(batch_id) → List[Activity]`
- `get_activities_by_note(note_id) → List[Activity]`
- `get_lineage_activities(batch_id) → List[Activity]`

**Duration:** 3-4 hours

---

### Step 6: Write Comprehensive Tests

**Coverage Requirements:**
- All service methods
- All validation rules
- All material types (consumables, non-consumables)
- Supplier inheritance in aliquots
- Lineage tracking
- Unit conversions
- Activity logging
- Edge cases

**Test Data:**
- Consumable materials: chemicals, reagents, samples
- Non-consumable materials: instruments, equipment
- Multiple suppliers
- Multiple locations
- Multi-level aliquot chains

**Run Tests:**
```bash
cd bricks/gws_eln
gws server test all
```

**ALL TESTS MUST PASS before Phase 2.**

**Duration:** 6-8 hours

---

### Step 7: Migrations and Seed Data

**Location:** `src/gws_eln/migrations/`

**migration_0001_initial.py:**
- Create all tables (materials, material_batches, suppliers, locations, activities)
- Create all indices
- Apply audit fields

**migration_0002_seed_data.py:**
- Create default location "labo"
- Create example suppliers (2-3)
- Create example materials of all types:
  - Consumables: Ethanol, NaCl, Blood Sample
  - Non-consumables: Spectrophotometer, Microscope
- Create example batches

**Run Migrations:**
```bash
# Apply migrations
gws server migrate

# Verify seed data
gws server shell
>>> from gws_eln.materials.material import Material
>>> Material.select().count()
5  # Expected: seeded materials
```

**Duration:** 3-4 hours

---

### Step 8: Phase 1 Validation

**Checklist:**
- [ ] All entities defined with audit fields
- [ ] All services implemented with validations
- [ ] Unit conversion utilities complete
- [ ] All tests passing (100% coverage)
- [ ] Migrations applied successfully
- [ ] Seed data populated
- [ ] Consumable/non-consumable behavior tested
- [ ] Supplier inheritance in aliquots tested
- [ ] Lineage tracking tested
- [ ] Activity logging tested

**Validation Commands:**
```bash
# Run all tests
gws server test all

# Check coverage
pytest tests/ --cov=gws_eln --cov-report=html

# Manual testing
gws server shell
# Test CRUD operations manually
```

**Duration:** 2-3 hours

**⚠️ DO NOT proceed to Phase 2 until ALL Phase 1 tests pass.**

---

## 🎨 Phase 2: Frontend Development (AFTER PHASE 1 COMPLETE)

Frontend implementation ONLY after backend is stable and tested.

### Step 9: Study gws_project Reflex Structure

**Before writing UI code:**
1. Study `gws_project` Reflex application
2. Understand:
   - Page/state patterns
   - Component structure
   - Service integration
   - State management
   - Routing

**Duration:** 2-3 hours

---

### Step 10: Implement Shared Components

**Location:** `src/gws_eln/project_app/_project_app/project_app/common/`

**Components:**

**QuantityInput:**
- Combined quantity + unit input
- Real-time conversion preview
- Validation (positive numbers)

**LocationPicker:**
- Dropdown of locations
- Current location highlighted

**SupplierPicker:**
- Dropdown of suppliers
- Optional (nullable)

**LineageViewer:**
- Parent-child tree visualization
- Clickable nodes
- Supplier inheritance display

**ConsumableIndicator:**
- Visual badge (consumable/non-consumable)
- Color-coded

**Duration:** 6-8 hours

---

### Step 11: Implement Inventory Page

**Location:** `src/gws_eln/project_app/_project_app/project_app/inventory/`

**Features:**
- List all materials
- Filter by consumable/non-consumable
- Filter by location
- Search by name
- Show batch counts and quantities
- Actions: receive, move, consume/use, discard, aliquot

**State Management:**
- Load materials on page load
- Refresh after actions
- Error handling
- Loading states

**Duration:** 8-10 hours

---

### Step 12: Implement Material Detail Page

**Location:** `src/gws_eln/project_app/_project_app/project_app/material_detail/`

**Features:**
- Material information
- List all batches for material
- Batch details (quantity, location, expiry)
- Lineage viewer for aliquots
- Activity history
- Batch actions

**Duration:** 6-8 hours

---

### Step 13: Implement Note Tool

**Location:** `src/gws_eln/project_app/_project_app/project_app/note_tool/`

**Features:**
- Embed in Constellab Notes
- Quick actions: consume, use, aliquot
- Link activities to note_id
- Display linked activities from note

**Integration:**
- Receive note_id from Constellab
- Call MaterialBatchService with note_id
- Return activity summary to note

**Duration:** 6-8 hours

---

### Step 14: Integration Testing

**Tests:**
- Page navigation
- Form submissions
- Service integration
- Error handling
- Loading states
- Data refresh

**Manual Testing:**
- Create materials (consumable and non-consumable)
- Receive batches
- Consume vs use behavior
- Create multi-level aliquots
- Verify supplier inheritance
- Check lineage display
- Test note-linked actions

**Duration:** 4-6 hours

---

### Step 15: Phase 2 Validation

**Checklist:**
- [ ] All pages functional
- [ ] All components working
- [ ] Services integrated correctly
- [ ] Consumable/non-consumable UI distinctions clear
- [ ] Unit conversions display correctly
- [ ] Lineage viewer shows full tree
- [ ] Activity log displays properly
- [ ] Note integration working
- [ ] Error messages user-friendly
- [ ] Loading states appropriate

**Duration:** 2-3 hours

---

## 📊 Time Estimates

### Phase 1: Backend (CRITICAL)
| Step | Duration | Cumulative |
|------|----------|------------|
| 1. Study gws_project | 2-4h | 2-4h |
| 2. Initialize project | 2-3h | 4-7h |
| 3. Unit conversion | 3-4h | 7-11h |
| 4. Entities | 12-15h | 19-26h |
| 5. Services | 18-24h | 37-50h |
| 6. Tests | 6-8h | 43-58h |
| 7. Migrations | 3-4h | 46-62h |
| 8. Validation | 2-3h | **48-65h** |

**Total Phase 1: 48-65 hours (~1-2 weeks)**

### Phase 2: Frontend (AFTER Phase 1)
| Step | Duration | Cumulative |
|------|----------|------------|
| 9. Study Reflex | 2-3h | 2-3h |
| 10. Components | 6-8h | 8-11h |
| 11. Inventory page | 8-10h | 16-21h |
| 12. Detail page | 6-8h | 22-29h |
| 13. Note tool | 6-8h | 28-37h |
| 14. Integration tests | 4-6h | 32-43h |
| 15. Validation | 2-3h | **34-46h** |

**Total Phase 2: 34-46 hours (~1 week)**

**Grand Total: 82-111 hours (~2-3 weeks)**

---

## ⚠️ Critical Success Factors

1. **Study gws_project first** - DO NOT skip reference study
2. **Backend-first** - NO UI work until Phase 1 complete
3. **Test everything** - 100% coverage for backend
4. **Follow patterns** - Naming, structure, formats
5. **Validate continuously** - Run tests after each step

---

## 🚀 Quick Start Command

```bash
# Initialize and run development server
cd bricks/gws_eln
gws reflex run src/gws_eln/project_app/_project_app/rxconfig.py
```

---
