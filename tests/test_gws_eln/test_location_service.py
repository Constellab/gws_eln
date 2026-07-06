"""
Test suite for LocationService.

Tests Story 3.4 from Epic 3: Service Layer - Suppliers & Locations.

Tests cover:
- Create location with valid data
- Create location with duplicate name (fails)
- Get default "labo" location
- Update location
- Delete unused location (succeeds)
- Delete referenced location (fails)
- Delete "labo" location (fails)
- List all locations
"""

from decimal import Decimal

from gws_core import BadRequestException, BaseTestCase, NotFoundException
from gws_eln.items.item import Item
from gws_eln.items.item_dto import CreateItemDTO
from gws_eln.items.item_service import ItemService
from gws_eln.items.item_sheet_dto import CreateItemSheetDTO
from gws_eln.items.item_sheet_service import ItemSheetService
from gws_eln.locations.location import Location
from gws_eln.locations.location_dto import CreateLocationDTO, UpdateLocationDTO
from gws_eln.locations.location_service import DEFAULT_LOCATION_NAME, LocationService
from gws_eln.user.eln_user_sync_service import ElnUserSyncService


class TestLocationService(BaseTestCase):
    """Test suite for LocationService"""

    @classmethod
    def init_before_test(cls):
        """Setup: sync users from gws_core to gws_eln before tests"""
        super().init_before_test()
        # Sync users so that the current user exists in gws_eln_user table
        sync_service = ElnUserSyncService()
        sync_service.sync_all_users()

    def test_create_location_valid_data(self):
        """Test creating a location with valid data"""
        service = LocationService()

        # Act
        location = service.create_location(
            CreateLocationDTO(name="Test Location", description="A test location description")
        )

        # Assert
        self.assertIsNotNone(location)
        self.assertIsNotNone(location.id)
        self.assertEqual(location.name, "Test Location")
        self.assertEqual(location.description, "A test location description")
        self.assertIsNotNone(location.created_at)
        self.assertIsNotNone(location.created_by)

        # Verify in database
        db_location = Location.get_by_id(location.id)
        self.assertEqual(db_location.name, "Test Location")

        # Cleanup
        location.delete_instance()

    def test_create_location_name_only(self):
        """Test creating a location with only name (no description)"""
        service = LocationService()

        # Act
        location = service.create_location(CreateLocationDTO(name="Minimal Location"))

        # Assert
        self.assertIsNotNone(location)
        self.assertEqual(location.name, "Minimal Location")
        self.assertIsNone(location.description)

        # Cleanup
        location.delete_instance()

    def test_create_location_trims_whitespace(self):
        """Test that location name and description are trimmed"""
        service = LocationService()

        # Act
        location = service.create_location(
            CreateLocationDTO(name="  Trimmed Location  ", description="  trimmed description  ")
        )

        # Assert
        self.assertEqual(location.name, "Trimmed Location")
        self.assertEqual(location.description, "trimmed description")

        # Cleanup
        location.delete_instance()

    def test_create_location_duplicate_name_fails(self):
        """Test creating a location with duplicate name fails"""
        service = LocationService()

        # Create first location
        location1 = service.create_location(CreateLocationDTO(name="Unique Location"))

        # Act & Assert: duplicate name should fail
        with self.assertRaises(BadRequestException) as context:
            service.create_location(CreateLocationDTO(name="Unique Location"))

        self.assertIn("already exists", str(context.exception))
        self.assertIn("Unique Location", str(context.exception))

        # Cleanup
        location1.delete_instance()

    def test_create_location_empty_name_fails(self):
        """Test creating a location with empty name fails"""
        service = LocationService()

        # Act & Assert
        with self.assertRaises(BadRequestException) as context:
            service.create_location(CreateLocationDTO(name=""))

        self.assertIn("name is required", str(context.exception))

    def test_create_location_whitespace_name_fails(self):
        """Test creating a location with whitespace-only name fails"""
        service = LocationService()

        # Act & Assert
        with self.assertRaises(BadRequestException) as context:
            service.create_location(CreateLocationDTO(name="   "))

        self.assertIn("name is required", str(context.exception))

    def test_get_location(self):
        """Test getting a location by ID"""
        service = LocationService()

        # Create location
        location = service.create_location(
            CreateLocationDTO(name="Get Test Location", description="A location to get")
        )

        # Act
        retrieved = service.get_location(location.id)

        # Assert
        self.assertEqual(retrieved.id, location.id)
        self.assertEqual(retrieved.name, "Get Test Location")
        self.assertEqual(retrieved.description, "A location to get")

        # Cleanup
        location.delete_instance()

    def test_get_location_not_found(self):
        """Test getting a non-existent location raises NotFoundException"""
        service = LocationService()

        # Act & Assert
        with self.assertRaises(NotFoundException):
            service.get_location("non-existent-id")

    def test_get_default_location(self):
        """Test getting the default 'labo' location"""
        service = LocationService()

        # Act
        default_location = service.get_default_location()

        # Assert
        self.assertIsNotNone(default_location)
        self.assertEqual(default_location.name, DEFAULT_LOCATION_NAME)

    def test_get_default_location_creates_if_missing(self):
        """Test that get_default_location creates the location if it doesn't exist"""
        service = LocationService()

        # Remove default location if it exists
        existing = Location.select().where(Location.name == DEFAULT_LOCATION_NAME).first()
        # Remove it only if it isn't referenced by any item
        if existing and not Item.select().where(Item.location == existing).exists():
            existing.delete_instance()

        # Act
        default_location = service.get_default_location()

        # Assert
        self.assertIsNotNone(default_location)
        self.assertEqual(default_location.name, DEFAULT_LOCATION_NAME)
        self.assertEqual(default_location.description, "Default laboratory location")

    def test_list_locations(self):
        """Test listing all locations"""
        service = LocationService()

        # Create multiple locations
        location1 = service.create_location(CreateLocationDTO(name="Alpha Location"))
        location2 = service.create_location(CreateLocationDTO(name="Beta Location"))
        location3 = service.create_location(CreateLocationDTO(name="Gamma Location"))

        # Act
        locations = service.list_locations()

        # Assert (at least our 3 locations)
        location_names = [loc.name for loc in locations]
        self.assertIn("Alpha Location", location_names)
        self.assertIn("Beta Location", location_names)
        self.assertIn("Gamma Location", location_names)

        # Verify order (should be by name)
        alpha_idx = location_names.index("Alpha Location")
        beta_idx = location_names.index("Beta Location")
        gamma_idx = location_names.index("Gamma Location")
        self.assertLess(alpha_idx, beta_idx)
        self.assertLess(beta_idx, gamma_idx)

        # Cleanup
        location1.delete_instance()
        location2.delete_instance()
        location3.delete_instance()

    def test_update_location(self):
        """Test updating a location"""
        service = LocationService()

        # Create location
        location = service.create_location(
            CreateLocationDTO(name="Original Name", description="Original description")
        )
        original_id = location.id

        # Act
        updated = service.update_location(
            location_id=location.id,
            dto=UpdateLocationDTO(name="Updated Name", description="Updated description"),
        )

        # Assert
        self.assertEqual(updated.id, original_id)
        self.assertEqual(updated.name, "Updated Name")
        self.assertEqual(updated.description, "Updated description")

        # Verify in database
        db_location = Location.get_by_id(original_id)
        self.assertEqual(db_location.name, "Updated Name")
        self.assertEqual(db_location.description, "Updated description")

        # Cleanup
        location.delete_instance()

    def test_update_location_clear_description(self):
        """Test updating location to clear description"""
        service = LocationService()

        # Create location with description
        location = service.create_location(
            CreateLocationDTO(name="Clear Description Location", description="to-be-cleared")
        )

        # Act: update with None description
        updated = service.update_location(
            location_id=location.id,
            dto=UpdateLocationDTO(name="Clear Description Location", description=None),
        )

        # Assert
        self.assertIsNone(updated.description)

        # Cleanup
        location.delete_instance()

    def test_update_location_same_name(self):
        """Test updating location keeping the same name"""
        service = LocationService()

        # Create location
        location = service.create_location(
            CreateLocationDTO(name="Same Name Location", description="original")
        )

        # Act: update description only, keep same name
        updated = service.update_location(
            location_id=location.id,
            dto=UpdateLocationDTO(name="Same Name Location", description="new description"),
        )

        # Assert
        self.assertEqual(updated.name, "Same Name Location")
        self.assertEqual(updated.description, "new description")

        # Cleanup
        location.delete_instance()

    def test_update_location_duplicate_name_fails(self):
        """Test updating location to a name that already exists fails"""
        service = LocationService()

        # Create two locations
        location1 = service.create_location(CreateLocationDTO(name="Location One"))
        location2 = service.create_location(CreateLocationDTO(name="Location Two"))

        # Act & Assert: try to rename location2 to location1's name
        with self.assertRaises(BadRequestException) as context:
            service.update_location(
                location_id=location2.id, dto=UpdateLocationDTO(name="Location One")
            )

        self.assertIn("already exists", str(context.exception))

        # Cleanup
        location1.delete_instance()
        location2.delete_instance()

    def test_update_location_empty_name_fails(self):
        """Test updating location with empty name fails"""
        service = LocationService()

        # Create location
        location = service.create_location(CreateLocationDTO(name="To Update Location"))

        # Act & Assert
        with self.assertRaises(BadRequestException) as context:
            service.update_location(location_id=location.id, dto=UpdateLocationDTO(name=""))

        self.assertIn("name is required", str(context.exception))

        # Cleanup
        location.delete_instance()

    def test_delete_location_unused(self):
        """Test deleting a location that is not referenced"""
        service = LocationService()

        # Create location
        location = service.create_location(CreateLocationDTO(name="To Delete Location"))
        location_id = location.id

        # Act
        result = service.delete_location(location_id)

        # Assert
        self.assertTrue(result)
        self.assertFalse(Location.select().where(Location.id == location_id).exists())

    def test_delete_location_referenced_fails(self):
        """Test deleting a location referenced by batches fails"""
        service = LocationService()

        # Create location
        location = service.create_location(CreateLocationDTO(name="Referenced Location"))

        # Create an item that references the location
        sheet = ItemSheetService().create_item_sheet(
            CreateItemSheetDTO(name="Sheet LOCR", code="LOCR")
        )
        ItemService().create_item(
            CreateItemDTO(
                item_sheet_id=sheet.id,
                quantity=Decimal(1),
                unit="units",
                location_id=location.id,
                label="Test item",
            )
        )

        # Act & Assert
        with self.assertRaises(BadRequestException) as context:
            service.delete_location(location.id)

        self.assertIn("Cannot delete", str(context.exception))
        self.assertIn("item", str(context.exception).lower())

        # Verify location still exists
        self.assertTrue(Location.select().where(Location.id == location.id).exists())

    def test_delete_default_location_fails(self):
        """Test deleting the default 'labo' location fails"""
        service = LocationService()

        # Ensure default location exists
        default_location = service.get_default_location()

        # Act & Assert
        with self.assertRaises(BadRequestException) as context:
            service.delete_location(default_location.id)

        self.assertIn("Cannot delete", str(context.exception))
        self.assertIn(DEFAULT_LOCATION_NAME, str(context.exception))

        # Verify location still exists
        self.assertTrue(Location.select().where(Location.id == default_location.id).exists())

    def test_delete_location_not_found(self):
        """Test deleting a non-existent location raises NotFoundException"""
        service = LocationService()

        # Act & Assert
        with self.assertRaises(NotFoundException):
            service.delete_location("non-existent-id")

    def test_audit_fields_on_create(self):
        """Test that audit fields are set on create"""
        service = LocationService()

        # Act
        location = service.create_location(CreateLocationDTO(name="Audit Test Location"))

        # Assert
        self.assertIsNotNone(location.created_at)
        self.assertIsNotNone(location.last_modified_at)
        self.assertIsNotNone(location.created_by)
        self.assertIsNotNone(location.last_modified_by)

        # Cleanup
        location.delete_instance()

    def test_audit_fields_on_update(self):
        """Test that audit fields are updated on update"""
        service = LocationService()

        # Create location
        location = service.create_location(CreateLocationDTO(name="Audit Update Location"))
        original_created_by_id = location.created_by.id

        # Act: update location
        updated = service.update_location(
            location_id=location.id, dto=UpdateLocationDTO(name="Audit Update Location Modified")
        )

        # Assert: created_by unchanged, last_modified_by is set
        self.assertEqual(updated.created_by.id, original_created_by_id)
        self.assertIsNotNone(updated.last_modified_at)
        self.assertIsNotNone(updated.last_modified_by)

        # Cleanup
        location.delete_instance()
