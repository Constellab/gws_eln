# gws_project Reference Patterns

**Purpose:** This document serves as the canonical reference for backend development patterns in gws_eln, extracted from studying the gws_project repository.

**Status:** Reference Document  
**Created:** 2026-01-22  
**Study Story:** 1.1 - Study gws_project Backend Structure  

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Entity Patterns](#entity-patterns)
3. [Naming Conventions](#naming-conventions)
4. [Service Layer Patterns](#service-layer-patterns)
5. [Test Patterns](#test-patterns)
6. [gws_eln Alignment Strategy](#gws_eln-alignment-strategy)

---

## Executive Summary

The gws_project repository demonstrates a well-structured backend architecture using:

- **ORM:** Peewee via gws_core base models
- **Base Models:** `gws_core.Model` and `gws_core.ModelWithUser` with automatic audit fields
- **Database Management:** Singleton DbManager pattern with DatabaseProxy
- **Service Layer:** Service classes with transaction management and security checks
- **Testing:** pytest-based with BaseTestCase, comprehensive service-layer testing

**Key Principles:**
1. ✅ All entities extend `ModelWithUser` for automatic audit tracking
2. ✅ All database identifiers use `snake_case`
3. ✅ Services handle business logic, validation, and transactions
4. ✅ Tests mirror source structure and test service methods
5. ✅ Security checks enforce user authorization at service layer

---

## Entity Patterns

### Base Model Classes

#### 1. `gws_core.Model` (Base)

**Location:** `/lab/user/bricks/gws_core/src/gws_core/core/model/model.py`

**Features:**
- Auto-generated UUID primary key (`id`)
- Timestamps: `created_at`, `last_modified_at` (automatically managed)
- Common CRUD methods: `get_by_id()`, `get_by_ids()`, `get_by_id_and_check()`
- Equality and hashing based on `id`

**Code Example:**
```python
from gws_core import Model
from peewee import CharField, IntegerField

class SimpleEntity(Model):
    name = CharField(max_length=255, null=False)
    count = IntegerField(default=0, null=False)
    
    class Meta:
        table_name = "simple_entities"
        database = MyDbManager.get_instance().db
        is_table = True
        db_manager = MyDbManager.get_instance()
```

**Key Fields:**
- `id: CharField(primary_key=True, max_length=36)` - UUID string
- `created_at: DateTimeUTC` - Auto-set on creation
- `last_modified_at: DateTimeUTC` - Auto-updated on save

#### 2. `gws_core.ModelWithUser` (Recommended for gws_eln)

**Location:** `/lab/user/bricks/gws_core/src/gws_core/core/model/model_with_user.py`

**Features:**
- Extends `Model` with audit user tracking
- Foreign keys to `User` entity for `created_by` and `last_modified_by`
- Automatic population via `_before_insert()` and `_before_update()` hooks
- Uses `CurrentUserService.get_and_check_current_user()` to get current user

**Code Example:**
```python
from gws_core import ModelWithUser
from peewee import CharField, ForeignKeyField

class Project(ModelWithUser):
    """
    Project model - Manages projects
    """
    title = CharField(max_length=255, null=False)
    project_manager = ForeignKeyField(User, null=False)
    
    class Meta:
        table_name = "gws_project_projects"
        database = ProjectDbManager.get_instance().db
        is_table = True
        db_manager = ProjectDbManager.get_instance()
```

**Automatic Audit Fields:**
- `created_by: ForeignKeyField(User)` - Set on insert
- `last_modified_by: ForeignKeyField(User)` - Updated on save
- Combined with `created_at` and `last_modified_at` from `Model`

**CRITICAL:** gws_project uses a custom `ModelWithUser` that references local `User` entity, not gws_core's. For gws_eln, we MUST use `gws_core.ModelWithUser` which references users in gws_core database.

### Field Patterns

#### Standard Field Types

```python
from peewee import (
    CharField,           # Text fields
    IntegerField,        # Integers
    DecimalField,        # Precise decimals (for quantities)
    DateField,           # Date only
    DateTimeField,       # Date and time
    BooleanField,        # True/False
    ForeignKeyField,     # Foreign keys
)
from gws_core import (
    EnumField,          # Enums
    RichTextDbField,    # Rich text content
    DateTimeUTC,        # UTC timestamps
)
```

#### Field Configuration Examples

```python
# Required text field with max length
title = CharField(max_length=255, null=False)

# Optional text field
description = CharField(max_length=500, null=True)

# Decimal for precise measurements (20 digits, 12 decimal places)
quantity = DecimalField(max_digits=20, decimal_places=12, null=False)

# Boolean with default
is_active = BooleanField(default=True, null=False)

# Enum field
status = EnumField(choices=TaskStatus, max_length=20, default=TaskStatus.TODO, null=False)

# Rich text
description = RichTextDbField(null=False)

# Foreign key with cascade delete
project = ForeignKeyField(Project, on_delete="CASCADE", null=False, backref="+")

# Self-referencing foreign key (hierarchical)
parent_task = ForeignKeyField("self", on_delete="CASCADE", null=True, backref="subtasks")

# Foreign key with index
start_date = DateField(null=False, index=True)
```

### Relationship Patterns

#### One-to-Many (N:1)

```python
# In Task model
class Task(ModelWithUser):
    # Many tasks belong to one project
    project = ForeignKeyField(Project, on_delete="CASCADE", null=False, backref="+")
```

**Notes:**
- `on_delete="CASCADE"`: Delete tasks when project is deleted
- `backref="+"`: Disable automatic reverse relationship
- `null=False`: Relationship is required

#### Self-Referencing (Hierarchical)

```python
# In Task model
class Task(ModelWithUser):
    # Task can have parent task (unlimited nesting)
    parent_task = ForeignKeyField("self", on_delete="CASCADE", null=True, backref="subtasks")
```

**Usage:**
```python
# Access subtasks
parent_task.subtasks  # Returns list of child tasks

# Check if root
task.is_root_task()  # Returns True if parent_task is None
```

#### Junction Table (Many-to-Many)

```python
class ProjectUser(ModelWithUser):
    """Junction table for project membership"""
    project = ForeignKeyField(Project, on_delete="CASCADE", null=False, backref="+")
    user = ForeignKeyField(User, null=False, backref="+")
    role = EnumField(choices=ProjectUserRole, max_length=20, null=False)
    
    class Meta:
        table_name = "gws_project_project_users"
        database = ProjectDbManager.get_instance().db
        is_table = True
        db_manager = ProjectDbManager.get_instance()
        indexes = (
            (("project_id", "user_id"), True),  # Unique constraint
        )
```

### Meta Class Configuration

Every entity MUST include a `Meta` class with these properties:

```python
class Meta:
    table_name = "gws_eln_materials"        # snake_case table name
    database = ElnDbManager.get_instance().db  # Database proxy
    is_table = True                         # Mark as table (not view)
    db_manager = ElnDbManager.get_instance()   # DB manager instance
```

**Optional Meta Properties:**
```python
class Meta:
    # ... standard properties ...
    
    # Composite unique constraints
    indexes = (
        (("field1", "field2"), True),  # Unique on field1+field2
        (("field3",), False),          # Non-unique index on field3
    )
```

### DTO Pattern

Entities should have a `to_dto()` method for data transfer:

```python
from gws_project.project.project_dto import ProjectDTO

class Project(ModelWithUser):
    # ... fields ...
    
    def to_dto(self) -> ProjectDTO:
        return ProjectDTO(
            id=self.id,
            created_at=self.created_at,
            last_modified_at=self.last_modified_at,
            created_by=self.created_by.to_dto(),
            last_modified_by=self.last_modified_by.to_dto(),
            title=self.title,
            description=self.description,
            start_date=self.start_date,
            end_date=self.end_date,
            project_manager=self.project_manager.to_dto(),
            progress=self.progress,
        )
```

## Service Layer Patterns

### Service Class Structure

Services contain business logic, validation, transaction management, and security checks.

**Standard Pattern:**
```python
from gws_core import CurrentUserService, BadRequestException
from gws_project.core.project_db_manager import ProjectDbManager

class MaterialService:
    """Service class for managing materials.
    
    Handles business logic, validation, and transactions for Material operations.
    """
    
    def __init__(self):
        """Initialize the service."""
        pass
    
    def get_material(self, material_id: str) -> Material:
        """Get a material by ID with security check.
        
        :param material_id: The ID of the material
        :type material_id: str
        :return: The material if found
        :rtype: Material
        :raises NotFoundException: If material not found
        """
        material = Material.get_by_id_and_check(material_id)
        return material
    
    @ProjectDbManager.transaction()
    def create_material(self, dto: CreateMaterialDTO) -> Material:
        """Create a new material with validation.
        
        :param dto: Material creation data
        :type dto: CreateMaterialDTO
        :return: The created material
        :rtype: Material
        :raises BadRequestException: If validation fails
        """
        # Validation
        self._validate_material_data(dto)
        
        # Create entity
        material = Material()
        material.name = dto.name
        material.cas_number = dto.cas_number
        # ... set other fields ...
        
        # Save
        material.save()
        
        return material
    
    @ProjectDbManager.transaction()
    def update_material(self, material_id: str, dto: UpdateMaterialDTO) -> Material:
        """Update a material with validation.
        
        :param material_id: The ID of the material to update
        :type material_id: str
        :param dto: Updated material data
        :type dto: UpdateMaterialDTO
        :return: The updated material
        :rtype: Material
        :raises NotFoundException: If material not found
        :raises BadRequestException: If validation fails
        """
        material = self.get_material(material_id)
        
        # Validation
        self._validate_material_data(dto)
        
        # Update fields
        material.name = dto.name
        # ... update other fields ...
        
        # Save
        material.save()
        
        return material
    
    @ProjectDbManager.transaction()
    def delete_material(self, material_id: str) -> None:
        """Delete a material.
        
        :param material_id: The ID of the material to delete
        :type material_id: str
        :raises NotFoundException: If material not found
        :raises BadRequestException: If material has dependencies
        """
        material = self.get_material(material_id)
        
        # Check dependencies
        if MaterialBatch.select().where(MaterialBatch.material == material).exists():
            raise BadRequestException("Cannot delete material with existing batches")
        
        material.delete_instance()
    
    def _validate_material_data(self, dto) -> None:
        """Private validation method.
        
        :param dto: Material data to validate
        :raises BadRequestException: If validation fails
        """
        if not dto.name or len(dto.name.strip()) == 0:
            raise BadRequestException("Material name is required")
        
        # Additional validation logic...
```

### Key Service Patterns

#### 1. Transaction Decorator

**Only use for write operations when it involves multiple database changes that must be atomic:**
```python
@ProjectDbManager.transaction()
def create_material(self, dto: CreateMaterialDTO) -> Material:
    # All database operations in this method are atomic
    material = Material()
    material.save()
    batch = MaterialBatch()
    batch.save()
    return material
```

**Benefits:**
- Automatic rollback on exceptions
- ACID compliance
- Consistent error handling

#### 2. Validation Pattern

**Private validation methods:**
```python
def _validate_material_data(self, dto) -> None:
    """Validate material data."""
    if not dto.name or len(dto.name.strip()) == 0:
        raise BadRequestException("Material name is required")
    
    if dto.cas_number and not self._is_valid_cas(dto.cas_number):
        raise BadRequestException("Invalid CAS number format")

def _is_valid_cas(self, cas: str) -> bool:
    """Check CAS number format."""
    # Implementation...
    return True
```

**Call validation before creating/updating:**
```python
@ProjectDbManager.transaction()
def create_material(self, dto: CreateMaterialDTO) -> Material:
    self._validate_material_data(dto)  # Validate first
    # ... create material ...
```

#### 3. Dependency Checks

**Before deletion:**
```python
@ProjectDbManager.transaction()
def delete_material(self, material_id: str) -> None:
    material = self.get_material(material_id)
    
    # Check for dependent batches
    if MaterialBatch.select().where(MaterialBatch.material == material).exists():
        raise BadRequestException(
            "Cannot delete material with existing batches. "
            "Delete all batches first."
        )
    
    material.delete_instance()
```

#### 5. CurrentUserService Usage

**Get current authenticated user:**
```python
from gws_core import CurrentUserService

current_user = CurrentUserService.get_and_check_current_user()
# Use current_user.id, current_user.email, etc.
```

**Note:** `ModelWithUser` automatically uses `CurrentUserService` in `_before_insert()` and `_before_update()` hooks.

### Service Method Naming

**CRUD Operations:**
- `get_{entity}(id)` - Get single by ID
- `get_{entities}()` - Get all
- `search_{entities}(filters)` - Search with filters
- `create_{entity}(dto)` - Create new
- `update_{entity}(id, dto)` - Update existing
- `delete_{entity}(id)` - Delete

**Business Operations:**
- `activate_{entity}(id)` - State change
- `assign_{entity}_to_{target}(id, target_id)` - Assignment
- `calculate_{something}(id)` - Calculation

**Private Methods:**
- `_validate_{something}(data)` - Validation
- `_check_{condition}(data)` - Boolean check
- `_build_{entity}_from_dto(dto)` - Construction helper


---

## gws_eln Alignment Strategy

### Domain Organization

Map gws_eln domains to gws_project patterns:

| gws_eln Domain | gws_project Reference | Pattern |
|----------------|----------------------|---------|
| Materials | Project | Core entity with hierarchy |
| Material Batches | Task | Self-referencing (parent_batch) |
| Suppliers | User | Simple entity |
| Locations | User | Simple entity |
| Activities | Task history | Audit trail entity |

### Folder Structure for gws_eln

**Following gws_project pattern:**
```
bricks/gws_eln/
├── planning-artifacts/
│   ├── prd.md
│   ├── architecture-summary.md
│   ├── database-schema.md
│   ├── implementation-patterns.md
│   ├── epics.md
│   ├── gws_project_reference_patterns.md  # This document
│   └── [stories]
├── src/
│   └── gws_eln/
│       ├── __init__.py
│       ├── core/
│       │   ├── __init__.py
│       │   └── eln_db_manager.py           # Database manager
│       ├── materials/
│       │   ├── __init__.py
│       │   ├── material.py                 # Material entity
│       │   ├── material_batch.py           # MaterialBatch entity
│       │   ├── material_service.py         # Material service
│       │   ├── material_batch_service.py   # Batch service
│       │   └── material_dto.py             # DTOs
│       ├── suppliers/
│       │   ├── __init__.py
│       │   ├── supplier.py                 # Supplier entity
│       │   ├── supplier_service.py         # Supplier service
│       │   └── supplier_dto.py             # DTOs
│       ├── locations/
│       │   ├── __init__.py
│       │   ├── location.py                 # Location entity
│       │   ├── location_service.py         # Location service
│       │   └── location_dto.py             # DTOs
│       └── activities/
│           ├── __init__.py
│           ├── activity.py                 # Activity entity
│           ├── activity_service.py         # Activity service
│           └── activity_dto.py             # DTOs
└── tests/
    └── test_gws_eln/
        ├── __init__.py
        ├── test_material_service.py
        ├── test_material_batch_service.py
        ├── test_supplier_service.py
        ├── test_location_service.py
        └── test_activity_service.py
```

### Entity Naming for gws_eln

All entities use `gws_eln_` prefix:

| Entity | Table Name | Python Class |
|--------|-----------|--------------|
| Material | `gws_eln_materials` | `Material` |
| Material Batch | `gws_eln_material_batches` | `MaterialBatch` |
| Supplier | `gws_eln_suppliers` | `Supplier` |
| Location | `gws_eln_locations` | `Location` |
| Activity | `gws_eln_activities` | `Activity` |

### Key Deviations & Justifications

#### 1. User Model

**gws_project:** Custom `User` model in local database  
**gws_eln:** Use `gws_core.ModelWithUser` which references users in gws_core database

**Justification:** gws_eln should leverage existing user system, not duplicate it.

**Implementation:**
```python
from gws_core import ModelWithUser  # Use gws_core version

class Material(ModelWithUser):  # created_by/last_modified_by auto-managed
    # ... fields ...
    
    class Meta:
        table_name = "gws_eln_materials"
        database = ElnDbManager.get_instance().db
        is_table = True
        db_manager = ElnDbManager.get_instance()
```

#### 2. Space Integration

**gws_project:** Heavy integration with Space (folders, sync)  
**gws_eln:** No Space integration needed

**Justification:** ELN is standalone inventory management.

**Implementation:** Services don't need `SpaceService` dependency.

#### 3. Security Model

**gws_project:** Project-based access control (owner, admin, user roles)  
**gws_eln:** Simple authentication check (all authenticated users have access)

**Justification:** Inventory is shared across organization.

**Implementation:**
```python
# Simple authentication check
def get_material(self, material_id: str) -> Material:
    current_user = CurrentUserService.get_and_check_current_user()
    material = Material.get_by_id_and_check(material_id)
    return material
```

### Implementation Sequence

Based on epics and stories:

1. **Story 1.2-1.3:** Create `ElnDbManager` (core)
2. **Story 1.4:** Create `Material` and `MaterialBatch` entities
3. **Story 1.5:** Create `Supplier` entity
4. **Story 1.6:** Create `Location` entity
5. **Story 1.7:** Create `Activity` entity
6. **Epic 4-5:** Implement services with tests
7. **Epic 8+:** Build Reflex UI

### Standards Checklist

Use this checklist for all entity and service development:

**Entity Checklist:**
- [ ] Extends `gws_core.ModelWithUser`
- [ ] Has `class Meta` with all required properties
- [ ] Table name follows `gws_eln_{entity_plural}` pattern
- [ ] All fields use `snake_case`
- [ ] Foreign keys use appropriate `on_delete` behavior
- [ ] Has `to_dto()` method
- [ ] Includes docstring describing purpose

**Service Checklist:**
- [ ] Has docstring describing purpose
- [ ] Uses `@DbManager.transaction()` for write operations
- [ ] Validates input before creating/updating
- [ ] Checks dependencies before deletion
- [ ] Raises `BadRequestException` for validation errors
- [ ] Raises `NotFoundException` for missing entities
- [ ] Uses `CurrentUserService` for authentication
- [ ] Has private `_validate_*` methods
- [ ] Follows naming conventions (get_, create_, update_, delete_)

**Test Checklist:**
- [ ] Test class extends `BaseTestCase`
- [ ] Test file mirrors source structure
- [ ] Tests service public methods
- [ ] Tests error conditions with `assertRaises`
- [ ] Uses Arrange-Act-Assert pattern
- [ ] Has descriptive test method names
- [ ] Includes integration tests (database state)
- [ ] Uses helper methods for common setup

---

## Appendix: Code Examples

### Complete Entity Example

```python
from decimal import Decimal
from gws_core import ModelWithUser
from peewee import CharField, DecimalField, BooleanField, ForeignKeyField
from gws_eln.core.eln_db_manager import ElnDbManager
from gws_eln.suppliers.supplier import Supplier
from gws_eln.materials.material_dto import MaterialDTO

class Material(ModelWithUser):
    """
    Material entity - represents a chemical or biological material.
    
    Supports both consumables and lab equipment via is_consumable flag.
    Tracks quantities in base units (L, kg, m, units).
    """
    
    # Required fields
    name = CharField(max_length=255, null=False, index=True)
    is_consumable = BooleanField(default=True, null=False)
    
    # Optional fields
    cas_number = CharField(max_length=50, null=True, index=True)
    description = CharField(max_length=1000, null=True)
    
    # Quantity tracking
    unit = CharField(max_length=20, null=False)  # L, kg, m, units
    min_stock = DecimalField(max_digits=20, decimal_places=12, null=True)
    current_stock = DecimalField(max_digits=20, decimal_places=12, default=Decimal('0'), null=False)
    
    # Relationships
    default_supplier = ForeignKeyField(Supplier, null=True, backref="+")
    
    def to_dto(self) -> MaterialDTO:
        """Convert to DTO for API responses."""
        return MaterialDTO(
            id=self.id,
            created_at=self.created_at,
            last_modified_at=self.last_modified_at,
            created_by=self.created_by.to_dto(),
            last_modified_by=self.last_modified_by.to_dto(),
            name=self.name,
            cas_number=self.cas_number,
            description=self.description,
            unit=self.unit,
            min_stock=self.min_stock,
            current_stock=self.current_stock,
            is_consumable=self.is_consumable,
            default_supplier=self.default_supplier.to_dto() if self.default_supplier else None,
        )
    
    class Meta:
        table_name = "gws_eln_materials"
        database = ElnDbManager.get_instance().db
        is_table = True
        db_manager = ElnDbManager.get_instance()
```

### Complete Service Example

```python
from decimal import Decimal
from gws_core import CurrentUserService, BadRequestException, NotFoundException
from gws_eln.core.eln_db_manager import ElnDbManager
from gws_eln.materials.material import Material
from gws_eln.materials.material_batch import MaterialBatch
from gws_eln.materials.material_dto import CreateMaterialDTO, UpdateMaterialDTO

class MaterialService:
    """
    Service for managing Material entities.
    
    Handles CRUD operations, validation, and business logic for materials.
    """
    
    def get_material(self, material_id: str) -> Material:
        """Get a material by ID.
        
        :param material_id: Material ID
        :type material_id: str
        :return: The material
        :rtype: Material
        :raises NotFoundException: If material not found
        """
        # Verify authentication
        CurrentUserService.get_and_check_current_user()
        
        # Get material
        material = Material.get_by_id_and_check(material_id)
        return material
    
    def get_all_materials(self) -> list[Material]:
        """Get all materials.
        
        :return: List of materials
        :rtype: list[Material]
        """
        CurrentUserService.get_and_check_current_user()
        return list(Material.select().order_by(Material.name))
    
    @ElnDbManager.transaction()
    def create_material(self, dto: CreateMaterialDTO) -> Material:
        """Create a new material.
        
        :param dto: Material creation data
        :type dto: CreateMaterialDTO
        :return: Created material
        :rtype: Material
        :raises BadRequestException: If validation fails
        """
        # Validate
        self._validate_material_data(dto)
        
        # Create
        material = Material()
        material.name = dto.name
        material.cas_number = dto.cas_number
        material.description = dto.description
        material.unit = dto.unit
        material.min_stock = dto.min_stock
        material.current_stock = Decimal('0')
        material.is_consumable = dto.is_consumable
        material.default_supplier_id = dto.default_supplier_id
        
        # Save
        material.save()
        return material
    
    @ElnDbManager.transaction()
    def update_material(self, material_id: str, dto: UpdateMaterialDTO) -> Material:
        """Update a material.
        
        :param material_id: Material ID
        :type material_id: str
        :param dto: Updated material data
        :type dto: UpdateMaterialDTO
        :return: Updated material
        :rtype: Material
        :raises NotFoundException: If material not found
        :raises BadRequestException: If validation fails
        """
        material = self.get_material(material_id)
        
        # Validate
        self._validate_material_data(dto)
        
        # Update
        material.name = dto.name
        material.cas_number = dto.cas_number
        material.description = dto.description
        material.min_stock = dto.min_stock
        material.default_supplier_id = dto.default_supplier_id
        
        # Save
        material.save()
        return material
    
    @ElnDbManager.transaction()
    def delete_material(self, material_id: str) -> None:
        """Delete a material.
        
        :param material_id: Material ID
        :type material_id: str
        :raises NotFoundException: If material not found
        :raises BadRequestException: If material has batches
        """
        material = self.get_material(material_id)
        
        # Check for batches
        if MaterialBatch.select().where(MaterialBatch.material == material).exists():
            raise BadRequestException(
                "Cannot delete material with existing batches. "
                "Delete all batches first."
            )
        
        # Delete
        material.delete_instance()
    
    def _validate_material_data(self, dto) -> None:
        """Validate material data.
        
        :param dto: Material data
        :raises BadRequestException: If validation fails
        """
        if not dto.name or len(dto.name.strip()) == 0:
            raise BadRequestException("Material name is required")
        
        if dto.unit not in ['L', 'kg', 'm', 'units']:
            raise BadRequestException("Invalid unit. Must be L, kg, m, or units")
        
        if dto.min_stock and dto.min_stock < 0:
            raise BadRequestException("Minimum stock cannot be negative")
```

### Complete Test Example

```python
from decimal import Decimal
from gws_core import BaseTestCase, BadRequestException
from gws_eln.materials.material_service import MaterialService
from gws_eln.materials.material_dto import CreateMaterialDTO, UpdateMaterialDTO
from gws_eln.materials.material_batch import MaterialBatch

class TestMaterialService(BaseTestCase):
    """Test suite for MaterialService"""
    
    def _create_test_material(self, name: str = "Test Material") -> Material:
        """Helper to create test material."""
        service = MaterialService()
        dto = CreateMaterialDTO(
            name=name,
            unit="L",
            is_consumable=True
        )
        return service.create_material(dto)
    
    def test_create_material(self):
        """Test creating a material"""
        service = MaterialService()
        
        # Arrange
        dto = CreateMaterialDTO(
            name="Ethanol",
            cas_number="64-17-5",
            unit="L",
            min_stock=Decimal('10.0'),
            is_consumable=True
        )
        
        # Act
        material = service.create_material(dto)
        
        # Assert
        self.assertIsNotNone(material)
        self.assertEqual(material.name, "Ethanol")
        self.assertEqual(material.cas_number, "64-17-5")
        self.assertEqual(material.unit, "L")
        self.assertEqual(material.min_stock, Decimal('10.0'))
        self.assertTrue(material.is_consumable)
    
    def test_create_material_invalid_name(self):
        """Test creating material with empty name"""
        service = MaterialService()
        
        dto = CreateMaterialDTO(name="", unit="L")
        
        with self.assertRaises(BadRequestException) as context:
            service.create_material(dto)
        
        self.assertIn("name", str(context.exception).lower())
    
    def test_delete_material_with_batches(self):
        """Test deleting material with existing batches"""
        service = MaterialService()
        
        # Create material
        material = self._create_test_material("Test Material")
        
        # Create batch
        batch = MaterialBatch()
        batch.material = material
        batch.batch_number = "B001"
        batch.save()
        
        # Try to delete
        with self.assertRaises(BadRequestException) as context:
            service.delete_material(material.id)
        
        self.assertIn("batches", str(context.exception).lower())
    
    def test_update_material(self):
        """Test updating material"""
        service = MaterialService()
        
        # Create
        material = self._create_test_material("Original Name")
        original_id = material.id
        
        # Update
        dto = UpdateMaterialDTO(
            name="Updated Name",
            unit="L"
        )
        updated = service.update_material(original_id, dto)
        
        # Assert
        self.assertEqual(updated.id, original_id)
        self.assertEqual(updated.name, "Updated Name")
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-22 | Dev Agent | Initial creation from gws_project study |

---

## References

- **gws_project Source:** `/lab/user/bricks/others/gws_project/`
- **gws_core Source:** `/lab/user/bricks/gws_core/`
- **gws_eln PRD:** [prd.md](prd.md)
- **gws_eln Architecture:** [architecture-summary.md](architecture-summary.md)
- **gws_eln Database Schema:** [database-schema.md](database-schema.md)
- **gws_eln Implementation Patterns:** [implementation-patterns.md](implementation-patterns.md)
