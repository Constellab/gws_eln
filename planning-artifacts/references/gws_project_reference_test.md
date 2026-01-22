
## Test Patterns

### Test Organization

**Mirror source structure:**
```
bricks/gws_eln/
├── src/
│   └── gws_eln/
│       ├── materials/
│       │   ├── material.py
│       │   └── material_service.py
│       └── suppliers/
│           ├── supplier.py
│           └── supplier_service.py
└── tests/
    └── test_gws_eln/
        ├── test_material_service.py    # Tests MaterialService
        └── test_supplier_service.py    # Tests SupplierService
```

### Test Class Structure

**Pattern from gws_project:**
```python
from gws_core import BaseTestCase, CurrentUserService
from gws_eln.materials.material_service import MaterialService
from gws_eln.materials.material_dto import CreateMaterialDTO

class TestMaterialService(BaseTestCase):
    """Test suite for MaterialService"""
    
    @classmethod
    def init_before_test(cls):
        """Initialize before all tests in class."""
        super().init_before_test()
        # Setup code that runs once per test class
        # e.g., sync users, create test data
    
    def test_create_material(self):
        """Test create_material method"""
        service = MaterialService()
        
        # Arrange
        dto = CreateMaterialDTO(
            name="Test Material",
            cas_number="50-00-0",
        )
        
        # Act
        material = service.create_material(dto)
        
        # Assert
        self.assertIsNotNone(material)
        self.assertEqual(material.name, "Test Material")
        self.assertEqual(material.cas_number, "50-00-0")
        self.assertIsNotNone(material.id)
    
    def test_create_material_invalid_cas(self):
        """Test create_material with invalid CAS number"""
        service = MaterialService()
        
        dto = CreateMaterialDTO(
            name="Test Material",
            cas_number="invalid",
        )
        
        # Assert exception is raised
        with self.assertRaises(BadRequestException) as context:
            service.create_material(dto)
        
        self.assertIn("CAS", str(context.exception))
    
    def test_delete_material_with_batches(self):
        """Test delete_material with existing batches"""
        service = MaterialService()
        
        # Create material with batch
        material = service.create_material(CreateMaterialDTO(name="Test"))
        batch = MaterialBatch(material=material, batch_number="B001")
        batch.save()
        
        # Try to delete material (should fail)
        with self.assertRaises(BadRequestException) as context:
            service.delete_material(material.id)
        
        self.assertIn("batches", str(context.exception).lower())
```

### Test Method Naming

**Convention:** `test_{method_name}_{scenario}`

**Examples:**
```python
def test_create_material():                          # ✅ Basic case
    pass

def test_create_material_with_optional_fields():    # ✅ Variation
    pass

def test_create_material_invalid_cas():             # ✅ Error case
    pass

def test_update_material_name():                    # ✅ Specific update
    pass

def test_delete_material_with_batches():            # ✅ Constraint check
    pass
```

### Common Test Patterns

#### 1. Arrange-Act-Assert

```python
def test_create_material(self):
    # Arrange: Setup data and dependencies
    service = MaterialService()
    dto = CreateMaterialDTO(name="Test Material")
    
    # Act: Execute the operation
    material = service.create_material(dto)
    
    # Assert: Verify results
    self.assertIsNotNone(material)
    self.assertEqual(material.name, "Test Material")
```

#### 2. Exception Testing

```python
def test_delete_material_with_batches(self):
    service = MaterialService()
    
    # Setup: Create material with batch
    material = service.create_material(CreateMaterialDTO(name="Test"))
    batch = MaterialBatch(material=material, batch_number="B001")
    batch.save()
    
    # Assert exception
    with self.assertRaises(BadRequestException) as context:
        service.delete_material(material.id)
    
    # Assert exception message
    self.assertIn("batches", str(context.exception).lower())
```

#### 3. Database State Verification

```python
def test_update_material(self):
    service = MaterialService()
    
    # Create
    material = service.create_material(CreateMaterialDTO(name="Original"))
    original_id = material.id
    
    # Update
    updated = service.update_material(
        original_id,
        UpdateMaterialDTO(name="Updated")
    )
    
    # Verify in database
    reloaded = Material.get_by_id(original_id)
    self.assertEqual(reloaded.name, "Updated")
    self.assertEqual(reloaded.id, original_id)
```

#### 4. Helper Methods

```python
class TestMaterialService(BaseTestCase):
    
    def _create_test_material(self, name: str = "Test Material") -> Material:
        """Helper to create material for tests."""
        service = MaterialService()
        dto = CreateMaterialDTO(name=name)
        return service.create_material(dto)
    
    def test_update_material(self):
        # Use helper
        material = self._create_test_material("Original")
        # ... test update ...
```

### BaseTestCase Features

**From gws_core:**
- Automatic database setup/teardown
- Test user creation (via `CurrentUserService`)
- Transaction rollback after each test
- Common assertion methods

**Usage:**
```python
from gws_core import BaseTestCase

class TestMyService(BaseTestCase):
    @classmethod
    def init_before_test(cls):
        """Runs once before all tests."""
        super().init_before_test()
        # Custom setup
    
    def setUp(self):
        """Runs before each test."""
        super().setUp()
        # Per-test setup
    
    def test_something(self):
        current_user = CurrentUserService.get_and_check_current_user()
        # Test code...
```

### Running Tests

**From architecture documentation:**
```bash
# Run all tests
gws server test all

# Run specific test file (without .py extension)
cd bricks/gws_eln
gws server test test_material_service
```
