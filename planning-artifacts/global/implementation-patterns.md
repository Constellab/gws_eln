# Implementation Patterns - ELN Inventory System

**Version:** 2.0  
**Date:** 2026-01-21

## Overview

Critical patterns and conventions to ensure consistency across AI agents and developers.

---

## 🏷️ Naming Patterns

### Database Naming

**Tables:**
- Format: `snake_case` plural
- Examples: `materials`, `material_batches`, `suppliers`, `locations`, `activities`
- ❌ DON'T: singular (`material`), camelCase (`materialBatches`)

**Columns:**
- Format: `snake_case`
- Examples: `created_by_id`, `last_modified_by_id`, `parent_batch_id`, `unit_type`, `is_consumable`
- ❌ DON'T: camelCase (`createdById`), abbreviated (`created_by`)

**Foreign Keys:**
- Format: `<entity>_id`
- Examples: `material_id`, `supplier_id`, `location_id`, `parent_batch_id`
- ✅ Consistency: always singular entity name + `_id`

**Indices:**
- Format: `idx_<table>_<column(s)>`
- Examples: `idx_materials_supplier`, `idx_material_batches_parent`
- ❌ DON'T: `index_materials_supplier`, `materials_supplier_idx`

**Audit Fields (all tables):**
- `created_by_id`, `last_modified_by_id`, `created_at`, `last_modified_at`
- ✅ Standardized across ALL tables

### API Naming

**Endpoints:**
- Format: plural nouns
- Examples: `/materials`, `/material_batches`, `/suppliers`, `/locations`
- ❌ DON'T: `/material`, `/getMaterials`, `/material-list`

**Route Parameters:**
- Format: `/:id`
- Examples: `/material_batches/:id`, `/materials/:id/batches`
- ❌ DON'T: `/:material_batch_id`, `/:batchId`

**Query Parameters:**
- Format: `snake_case`
- Examples: `?location_id=1`, `?is_consumable=true`, `?parent_batch_id=5`
- ❌ DON'T: `?locationId=1`, `?isConsumable=true`

### Code Naming

**Components (Reflex):**
- Format: `PascalCase`
- Examples: `InventoryList`, `LineageViewer`, `QuantityInput`, `SupplierPicker`
- ❌ DON'T: `inventory_list`, `lineageViewer`

**Files (Python):**
- Format: `snake_case`
- Examples: `material_service.py`, `unit_converter.py`, `material_batch.py`
- ❌ DON'T: `MaterialService.py`, `unitConverter.py`

**Functions/Variables (Python):**
- Format: `snake_case`
- Examples: `get_material_batches()`, `to_base_unit()`, `current_user_id`
- ❌ DON'T: `getMaterialBatches()`, `toBaseUnit()`, `currentUserId`

**Constants:**
- Format: `UPPER_SNAKE_CASE`
- Examples: `BASE_UNITS`, `CONVERSION_FACTORS`, `DEFAULT_LOCATION_NAME`
- ❌ DON'T: `baseUnits`, `Base_Units`

---

## 📁 Structure Patterns

### Domain-Driven Organization

**Pattern:** Co-locate models and services by domain.

```
src/gws_eln/
├── materials/              # Material domain
│   ├── material.py         # Entity/Model
│   ├── material_batch.py   # Entity/Model
│   ├── material_service.py # Service
│   └── material_batch_service.py
├── suppliers/              # Supplier domain
│   ├── supplier.py
│   └── supplier_service.py
├── locations/              # Location domain
│   ├── location.py
│   └── location_service.py
└── activities/             # Activity domain
    ├── activity.py
    └── activity_service.py
```

**Benefits:**
- ✅ High cohesion: related code together
- ✅ Easy to find: domain-based navigation
- ✅ Clear boundaries: reduces coupling
- ❌ DON'T: layer-based structure (`models/`, `services/`)

### File Organization

**Configuration:**
- `rxconfig.py` in `project_app/_project_app/`
- `settings.json` in brick root
- `.env` managed by Constellab

**Tests:**
- Mirror domain structure
- Location: `tests/<domain>/`
- Examples: `tests/materials/test_material_service.py`

**Assets:**
- Location: `project_app/_project_app/assets/`
- No external CDN/hosting

---

## 📋 Format Patterns

### API Response Formats

**Success Response:**
```json
{
  "data": {
    "id": 123,
    "name": "Ethanol 99%",
    "quantity": 0.5,
    "unit_type": "volume"
  }
}
```

**Error Response:**
```json
{
  "error": {
    "code": "INVALID_QUANTITY",
    "message": "Quantity must be positive",
    "details": {
      "field": "quantity",
      "value": -10
    }
  }
}
```

**✅ Consistency:**
- Always wrap in `data` or `error`
- Use `snake_case` for JSON fields
- Include optional `details` for debugging

### Date/Time Formats

- **Storage:** UTC timestamps
- **JSON:** ISO-8601 strings (`2026-01-21T10:30:00Z`)
- ❌ DON'T: Unix timestamps, custom formats

### Quantity Formats

**Storage (database):**
```json
{
  "quantity": 0.5,
  "unit_type": "volume"
}
```

**Display (API response):**
```json
{
  "quantity": 500,
  "unit": "mL",
  "quantity_base": 0.5,
  "unit_type": "volume"
}
```

**✅ Include both:**
- User-friendly display (`quantity`, `unit`)
- Base unit storage (`quantity_base`, `unit_type`)

---

## 🔄 Process Patterns

### Error Handling

**Service Layer:**
```python
# Raise specific exceptions
if quantity <= 0:
    raise ValidationError("Quantity must be positive")

if not location_exists(location_id):
    raise NotFoundError(f"Location {location_id} not found")
```

**Page/State Layer:**
```python
# Catch and display user-friendly messages
try:
    material_service.consume(batch_id, quantity, unit)
except ValidationError as e:
    self.error_message = str(e)
except NotFoundError as e:
    self.error_message = "Item not found"
```

**✅ Distinguish:**
- Validation errors (user input)
- Not found errors (missing resources)
- Operation failures (business logic)

### Loading States

**Naming:**
- `is_loading_<action>` (e.g., `is_loading_consume`, `is_loading_move`)
- ❌ DON'T: `loading`, `isLoading`, `consumeLoading`

**Scope:**
- Local to page/state
- No global spinner

**Lifecycle:**
1. Set `True` before service call
2. Execute service operation
3. Set `False` on completion/failure
4. Update UI state

### Unit Conversions

**On Input:**
```python
# User enters: 500 mL
quantity_base = to_base_unit(500, "mL", "volume")
# Store: 0.5 L
```

**On Display:**
```python
# Stored: 0.5 L
quantity_display, unit = from_base_unit(0.5, "volume")
# Display: 500 mL (auto-selects appropriate unit)
```

**✅ Centralized:**
- All conversions in `utils/units.py`
- Used by services AND UI components

---

## 🎯 Activity Type Patterns

### Activity Type Usage

| Type      | Purpose                          | Quantity? | Consumable? | Non-Consumable? |
|-----------|----------------------------------|-----------|-------------|-----------------|
| receive   | New batch from supplier          | ✅        | ✅          | ✅              |
| move      | Change location                  | ❌        | ✅          | ✅              |
| consume   | Use consumable                   | ✅        | ✅          | ❌              |
| use       | Use non-consumable               | ❌        | ❌          | ✅              |
| discard   | Remove/dispose                   | ✅        | ✅          | ✅              |
| aliquot   | Create child batch               | ✅        | ✅          | ❌              |
| relabel   | Change label only                | ❌        | ✅          | ✅              |

**✅ Always:**
- Log activity AFTER successful operation
- Include `created_by_id` (from CurrentUserService)
- Link to note via `note_id` if from Note tool

---

## ✅ Good Examples

### Database Query
```python
# Good: Use indices, explicit joins
batches = (MaterialBatch
    .select()
    .join(Material)
    .where(Material.is_consumable == True)
    .where(MaterialBatch.location_id == location_id))
```

### Service Method
```python
# Good: Clear validation, specific exceptions
def consume_batch(batch_id: int, quantity: float, unit: str) -> MaterialBatch:
    batch = MaterialBatch.get_or_none(MaterialBatch.id == batch_id)
    if not batch:
        raise NotFoundError(f"Batch {batch_id} not found")
    
    if not batch.material.is_consumable:
        raise ValidationError("Cannot consume non-consumable material")
    
    quantity_base = to_base_unit(quantity, unit, batch.unit_type)
    if quantity_base > batch.quantity:
        raise ValidationError("Insufficient quantity")
    
    batch.quantity -= quantity_base
    batch.save()
    
    Activity.create(
        activity_type='consume',
        entity_id=batch_id,
        quantity=quantity_base,
        unit_type=batch.unit_type
    )
    
    return batch
```

### Reflex State
```python
# Good: Clear action methods, error handling
class MaterialBatchState(rx.State):
    error_message: str = ""
    is_loading_consume: bool = False
    
    def consume_batch(self, batch_id: int, quantity: float, unit: str):
        self.error_message = ""
        self.is_loading_consume = True
        
        try:
            material_batch_service.consume_batch(batch_id, quantity, unit)
            return rx.redirect("/inventory")
        except ValidationError as e:
            self.error_message = str(e)
        except NotFoundError:
            self.error_message = "Batch not found"
        finally:
            self.is_loading_consume = False
```

---

## ❌ Anti-Patterns

### DON'T: Mixed Casing
```json
// Bad: Inconsistent field names
{
  "userId": 123,
  "created_at": "2026-01-21",
  "MaterialName": "Ethanol"
}

// Good: All snake_case
{
  "user_id": 123,
  "created_at": "2026-01-21",
  "material_name": "Ethanol"
}
```

### DON'T: Storing User Units
```python
# Bad: Store user-selected unit
batch.quantity = 500
batch.unit = "mL"

# Good: Convert to base unit
batch.quantity = to_base_unit(500, "mL", "volume")  # 0.5 L
batch.unit_type = "volume"
```

### DON'T: Using FLOAT for Quantities
```python
# Bad: Precision loss
quantity = models.FloatField()

# Good: High precision
quantity = models.DecimalField(max_digits=20, decimal_places=12)
```

### DON'T: Forgetting Supplier Inheritance
```python
# Bad: Manual supplier assignment
child_batch = MaterialBatch.create(
    material_id=parent_batch.material_id,
    parent_batch_id=parent_batch.id
    # Missing: supplier inheritance!
)

# Good: Automatic supplier inheritance
child_batch = MaterialBatch.create(
    material_id=parent_batch.material_id,
    parent_batch_id=parent_batch.id,
    # Supplier inherited from parent.material.supplier_id
)
```

---

## 🔒 Enforcement

**Code Reviews:**
- Check against this document
- Validate naming conventions
- Verify error handling patterns

**Linting:**
- Use project linting standards
- Enforce snake_case, PascalCase rules

**Testing:**
- Validate API response formats
- Test unit conversions
- Verify activity logging

---

