"""State for the batch detail page."""

import reflex as rx
from gws_eln.materials.material_batch import MaterialBatch
from gws_eln.materials.material_batch_dto import MaterialBatchDTO
from gws_eln.materials.material_batch_service import MaterialBatchService
from gws_reflex_main import ReflexMainState

from ..activities.activities_list_state import ActivitiesListState
from ..batch_event_form_dialog.batch_event_form_dialog_state import (
    BatchEventFormDialogState,
    BatchEventType,
)
from ..move_batch_form_dialog.move_batch_form_dialog_state import (
    MoveBatchFormDialogState,
)


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

    async def _on_batch_event_success(self, updated_batch: MaterialBatchDTO):
        """Callback invoked when a batch event completes successfully.

        Updates the batch data and refreshes the activities list.

        :param updated_batch: The updated batch DTO
        :type updated_batch: MaterialBatchDTO
        """
        # Update the batch with the new data
        self.batch = updated_batch

        # Refresh the activities list
        activities_state = await self.get_state(ActivitiesListState)
        await activities_state.refresh_activities()

    @rx.event
    async def open_receive_dialog(self):
        """Open the receive stock dialog for the current batch."""
        if not self.batch:
            return
        dialog_state = await self.get_state(BatchEventFormDialogState)
        dialog_state.set_callback_after_close(self._on_batch_event_success)
        dialog_state.open_dialog_for_event(self.batch, BatchEventType.RECEIVE)

    @rx.event
    async def open_consume_dialog(self):
        """Open the consume stock dialog for the current batch."""
        if not self.batch:
            return
        dialog_state = await self.get_state(BatchEventFormDialogState)
        dialog_state.set_callback_after_close(self._on_batch_event_success)
        dialog_state.open_dialog_for_event(self.batch, BatchEventType.CONSUME)

    @rx.event
    async def open_move_dialog(self):
        """Open the move batch dialog for the current batch."""
        if not self.batch:
            return
        dialog_state = await self.get_state(MoveBatchFormDialogState)
        dialog_state.set_callback_after_close(self._on_batch_event_success)
        await dialog_state.open_move_dialog(self.batch)
