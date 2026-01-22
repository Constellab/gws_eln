# Story 1.2: Define Material Entity

Status: ready-for-dev

## Story

As a developer,
I want to create the Material entity with all required fields,
so that we can catalog all lab materials (chemicals, instruments, samples).

## Acceptance Criteria

1. Create `src/gws_eln/materials/material.py`
2. Fields: id, name, description, supplier_id (FK), is_consumable, default_unit_type
3. Audit fields: created_by_id, last_modified_by_id, created_at, last_modified_at
4. Indices: supplier_id, is_consumable, name
5. Model extends `gws_core.ModelWithUser`
6. Unit test for entity creation

## Context

This is the **second story** in Epic 1 (Core Infrastructure & Database Entities) and represents the **first entity implementation** in the gws_eln project. This story creates the foundational Material entity that catalogs ALL types of lab materials (chemicals, instruments, equipment, samples) using a **unified data model** approach.

**Critical Architecture Decision:** The Material entity uses a single `is_consumable` flag to differentiate behavior:
- `is_consumable=TRUE`: chemicals, reagents, samples (quantity decrements on consumption)
- `is_consumable=FALSE`: instruments, equipment (usage reference only, no quantity decrement)

This unified approach eliminates the need for separate tables for samples, instruments, or other material types.

## Technical Requirements

### 1. File Location and Structure

**File Path:** `src/gws_eln/materials/material.py`

**Directory Structure:**
```
src/gws_eln/
└── materials/
    ├── __init__.py
    └── material.py
```

**Import Pattern:**
```python
from peewee import CharField, TextField, BooleanField, ForeignKeyField
from gws_core.core.model.model_with_user import ModelWithUser
from gws_core.core.classes.enum_field import EnumField
```

### 2. Entity Definition

**Class Name:** `Material` (singular, note the spelling - "material" not "material")

**Extends:** `ModelWithUser` from `gws_core.core.model.model_with_user`

**Why ModelWithUser:**
- Automatically provides audit fields: `created_by`, `last_modified_by`
- Automatically populates `created_by` on insert via `_before_insert()` hook
- Automatically populates `last_modified_by` on update via `_before_update()` hook
- Inherits from `Model` which provides: `id`, `created_at`, `last_modified_at`

**Table Name:** `materials` (plural, snake_case)

### 3. Field Definitions

Based on [database-schema.md](database-schema.md) and gws_core patterns:

```python
class Material(ModelWithUser):
    """
    Material entity - Unified catalog for ALL lab material types.
    
    Handles chemicals, instruments, equipment, samples, and reagents.
    The is_consumable flag determines behavior:
    - TRUE: quantity decrements on consumption (chemicals, reagents, samples)
    - FALSE: usage reference only (instruments, equipment)
    """
    
    # Name of the material (e.g., "Éthanol 99%", "Spectrophotomètre UV-Vis")
    name = CharField(max_length=255, null=False, index=True)
    
    # Detailed description
    description = TextField(null=True)
    
    # Foreign key to Supplier (optional - can be set later)
    # Note: Supplier entity will be created in Story 1.4
    # Use backref="+" to prevent reverse relation
    supplier_id = ForeignKeyField(
        'Supplier',  # String reference (forward declaration)
        null=True,
        backref="+",
        column_name="supplier_id"
    )
        
    # Consumable flag determines behavior
    is_consumable = BooleanField(null=False, default=True, index=True)
    
    # Default unit type for this material
    default_unit_type = EnumField(
        choices=['volume', 'mass', 'length', 'count'],
        null=False,
        default='count'
    )
    
    class Meta:
        table_name = 'materials'
        is_table = True
        indexes = (
            # Composite index for supplier lookups
            (('supplier_id',), False),
            # Index for filtering by consumable type
            (('is_consumable',), False),
            # Index for name searches (already indexed via field, but explicit for clarity)
            (('name',), False),
        )
```

### 4. Audit Fields (Inherited from ModelWithUser)

**DO NOT manually define these fields** - they are inherited:
- `id` (CharField, primary key, UUID) - from Model
- `created_by` (ForeignKeyField to User) - from ModelWithUser
- `last_modified_by` (ForeignKeyField to User) - from ModelWithUser
- `created_at` (DateTimeUTC) - from Model
- `last_modified_at` (DateTimeUTC) - from Model

**Automatic Population:**
- `created_by` and `last_modified_by` are automatically populated via `CurrentUserService.get_and_check_current_user()` in the `_before_insert()` and `_before_update()` hooks
- Timestamps are automatically managed by Peewee

### 5. Foreign Key Pattern

**Supplier Reference:**
- Use string reference `'Supplier'` for forward declaration (Supplier entity created in Story 1.4)
- Set `backref="+"` to prevent reverse relation (cleaner, avoids circular imports)
- Set `column_name="supplier_id"` explicitly for database column naming

**Example from gws_core:**
```python
# From ResourceModel
scenario = ForeignKeyField(
    "Scenario",  # String reference
    null=True,
    backref="+",
    column_name="scenario"
)
```

### 6. Enum Field Pattern

**Unit Type Enum:**
- Use `EnumField` from `gws_core.core.classes.enum_field`
- Pass list of string choices: `['volume', 'mass', 'length', 'count']`
- Set default value: `default='count'`
- Store as VARCHAR in database

**Reference:** [database-schema.md#Base Unit Storage](database-schema.md)

### 7. Index Definitions

**Three indices required:**
1. `supplier_id` - for supplier-based queries
2. `is_consumable` - for filtering consumables vs non-consumables
3. `name` - for name searches (already indexed via field definition)

**Pattern:** Define in `Meta.indexes` tuple as shown above

### 8. Testing Requirements

**Test File:** `tests/test_materials/test_material.py`

**Test Structure:**
```python
from unittest import TestCase
from gws_core.impl.file.file_helper import FileHelper
from gws_core.core.utils.settings import Settings
from gws_eln.materials.material import Material

class TestMaterial(TestCase):
    
    def test_create_material(self):
        """Test basic material creation"""
        # Create consumable material
        material = Material.create(
            name="Éthanol 99%",
            description="High purity ethanol",
            is_consumable=True,
            default_unit_type='volume'
        )
        
        self.assertIsNotNone(material.id)
        self.assertEqual(material.name, "Éthanol 99%")
        self.assertTrue(material.is_consumable)
        self.assertEqual(material.default_unit_type, 'volume')
        
    def test_create_non_consumable_material(self):
        """Test non-consumable material (instrument)"""
        material = Material.create(
            name="Spectrophotomètre UV-Vis",
            description="UV-Visible spectrophotometer",
            is_consumable=False,
            default_unit_type='count'
        )
        
        self.assertFalse(material.is_consumable)
        
    def test_audit_fields_populated(self):
        """Test that audit fields are automatically populated"""
        material = Material.create(
            name="Test Material",
            is_consumable=True,
            default_unit_type='mass'
        )
        
        # These should be auto-populated by ModelWithUser
        self.assertIsNotNone(material.created_by)
        self.assertIsNotNone(material.last_modified_by)
        self.assertIsNotNone(material.created_at)
        self.assertIsNotNone(material.last_modified_at)
```

**Run Command:**
```bash
cd bricks/gws_eln
gws server test test_material
```

## Dev Notes

### Critical Naming Convention

**Spelling:** "Material" not "Material"
- This is the project's chosen naming convention
- Use consistently: class name, file names, table names, variable names
- Table name: `materials` (plural)
- Entity name: `Material` (singular)

### ModelWithUser vs Model

**Use ModelWithUser when:**
- Entity requires audit trail (who created, who modified)
- Entity is user-generated content
- Need automatic user context population

**Use Model when:**
- System-managed data
- No need for user audit trail
- Example: system configuration tables

**For gws_eln:** ALL 5 entities use `ModelWithUser` for complete audit trail.

### Forward Declaration Pattern

Since Supplier entity doesn't exist yet (Story 1.4), use **string reference**:
```python
supplier_id = ForeignKeyField('Supplier', ...)  # String, not class
```

This is resolved by Peewee during table creation.

### Database Precision

**DECIMAL(20,12) for quantities:**
- NOT stored in Material entity (quantities are in Material_Batch)
- Mentioned here for context: when implementing batch quantities in Story 1.3, use high precision

### Project Structure Alignment

**Follows gws_project patterns:**
- Domain-based organization: `materials/` folder
- Entity file naming: singular lowercase (`material.py`)
- Class naming: singular PascalCase (`Material`)
- Table naming: plural snake_case (`materials`)

**Example from gws_project:**
```
src/gws_project/
├── project/
│   └── project.py (class Project, table: projects)
├── task/
│   └── task_model.py (class TaskModel, table: task)
└── document/
    └── document.py (class Document, table: documents)
```

### References

**Source Documents:**
- [database-schema.md](database-schema.md) - Complete Material table definition
- [architecture-summary.md](architecture-summary.md) - Unified model approach
- [epics.md - Story 1.2](epics.md#story-12-define-material-entity)
- [1-1-study-gws-project-backend-structure.md](1-1-study-gws-project-backend-structure.md) - gws_project patterns

**gws_core References:**
- `/lab/user/bricks/gws_core/src/gws_core/core/model/model_with_user.py` - ModelWithUser implementation
- `/lab/user/bricks/gws_core/src/gws_core/core/model/model.py` - Model base class
- `/lab/user/bricks/gws_core/src/gws_core/core/classes/enum_field.py` - EnumField usage
- `/lab/user/bricks/gws_core/src/gws_core/user/user.py` - User entity example

## Tasks / Subtasks

- [ ] Create directory structure (AC: #1)
  - [ ] Create `src/gws_eln/materials/` directory
  - [ ] Create `__init__.py` in materials folder
  
- [ ] Implement Material entity (AC: #1, #2, #3, #4, #5)
  - [ ] Import required classes (ModelWithUser, CharField, TextField, etc.)
  - [ ] Define Material class extending ModelWithUser
  - [ ] Add all field definitions with correct types
  - [ ] Add Meta class with table_name and indexes
  - [ ] Add docstring explaining unified model approach
  
- [ ] Create test file (AC: #6)
  - [ ] Create `tests/test_materials/` directory
  - [ ] Create `test_material.py`
  - [ ] Implement test_create_material
  - [ ] Implement test_create_non_consumable_material
  - [ ] Implement test_audit_fields_populated
  
- [ ] Run tests and verify (AC: #6)
  - [ ] Run `gws server test test_material`
  - [ ] Verify all tests pass
  - [ ] Verify table created in database with correct schema

## Dev Agent Record

### Agent Model Used

_To be filled by Dev agent_

### Debug Log References

_To be filled by Dev agent_

### Completion Notes List

_To be filled by Dev agent_

### File List

**Expected Files Created:**
- `src/gws_eln/materials/__init__.py`
- `src/gws_eln/materials/material.py`
- `tests/test_materials/__init__.py`
- `tests/test_materials/test_material.py`
