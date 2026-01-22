from gws_core import SearchBuilder

from gws_eln.materials.batch_status import BatchStatus
from gws_eln.materials.material_batch import MaterialBatch


class MaterialBatchSearchBuilder(SearchBuilder):
    def __init__(self) -> None:
        super().__init__(MaterialBatch, default_orders=[MaterialBatch.created_at.desc()])

    def add_material_filter(self, material_id: str) -> "MaterialBatchSearchBuilder":
        """Filter the search query by material ID"""
        self.add_expression(MaterialBatch.material == material_id)
        return self

    def add_location_filter(self, location_id: str) -> "MaterialBatchSearchBuilder":
        """Filter the search query by location ID"""
        self.add_expression(MaterialBatch.location == location_id)
        return self

    def add_parent_batch_filter(self, parent_batch_id: str) -> "MaterialBatchSearchBuilder":
        """Filter the search query by parent batch ID"""
        self.add_expression(MaterialBatch.parent_batch == parent_batch_id)
        return self

    def add_original_batches_only_filter(self) -> "MaterialBatchSearchBuilder":
        """Filter to only include original batches (no parent)"""
        self.add_expression(MaterialBatch.parent_batch.is_null(True))
        return self

    def add_aliquots_only_filter(self) -> "MaterialBatchSearchBuilder":
        """Filter to only include aliquots (has parent)"""
        self.add_expression(MaterialBatch.parent_batch.is_null(False))
        return self

    def add_supplier_filter(self, supplier_id: str) -> "MaterialBatchSearchBuilder":
        """Filter the search query by supplier ID"""
        self.add_expression(MaterialBatch.supplier == supplier_id)
        return self

    def add_batch_number_filter(self, batch_number: str) -> "MaterialBatchSearchBuilder":
        """Filter the search query by batch number (case-insensitive contains)"""
        like_pattern = f"%{batch_number}%"
        self.add_expression(MaterialBatch.batch_number.ilike(like_pattern))
        return self

    def add_label_filter(self, label: str) -> "MaterialBatchSearchBuilder":
        """Filter the search query by label (case-insensitive contains)"""
        like_pattern = f"%{label}%"
        self.add_expression(MaterialBatch.label.ilike(like_pattern))
        return self

    def add_notes_filter(self, notes: str) -> "MaterialBatchSearchBuilder":
        """Filter the search query by notes (case-insensitive contains)"""
        like_pattern = f"%{notes}%"
        self.add_expression(MaterialBatch.notes.ilike(like_pattern))
        return self

    def add_status_filter(self, status: BatchStatus) -> "MaterialBatchSearchBuilder":
        """Filter the search query by batch status"""
        self.add_expression(MaterialBatch.status == status)
        return self

    def add_active_only_filter(self) -> "MaterialBatchSearchBuilder":
        """Filter to only include active batches"""
        self.add_expression(MaterialBatch.status == BatchStatus.ACTIVE)
        return self
