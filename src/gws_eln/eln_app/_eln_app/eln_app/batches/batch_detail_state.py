"""State for the batch detail page."""

import reflex as rx
from gws_eln.materials.material_batch import MaterialBatch
from gws_eln.materials.material_batch_dto import MaterialBatchDTO
from gws_eln.materials.material_batch_service import MaterialBatchService
from gws_reflex_main import ReflexMainState


class BatchDetailState(rx.State):
    """State for managing the batch detail page.

    This state handles fetching and displaying a single batch's details.
    """

    batch: MaterialBatchDTO | None = None
    is_loading: bool = False
    error_message: str = ""

    async def load_batch(self, batch_id: str):
        """Load a batch by its ID.

        :param batch_id: The ID of the batch to load
        :type batch_id: str
        """
        main_state = await self.get_state(ReflexMainState)
        if not await main_state.check_authentication():
            self.error_message = "You must be authenticated to view this batch"
            return

        self.is_loading = True
        self.error_message = ""

        try:
            batch_service = MaterialBatchService()
            batch: MaterialBatch
            with await main_state.authenticate_user():
                batch = batch_service.get_batch(batch_id)

            if batch:
                self.batch = batch.to_dto()
            else:
                self.error_message = "Batch not found"
                self.batch = None

        except Exception as e:
            self.error_message = f"Error loading batch: {str(e)}"
            self.batch = None
        finally:
            self.is_loading = False

    @rx.event
    async def on_load(self):
        """Event handler called when the page loads."""
        batch_id = self.batch_id
        if batch_id:
            await self.load_batch(batch_id)
        else:
            self.error_message = "No batch ID provided"
