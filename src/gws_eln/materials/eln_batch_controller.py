"""Controller for ELN batch action endpoints.

Provides batch-centric API endpoints for inventory actions.
Registered as a custom brick FastAPI app, mounted at /brick/gws_eln/.
"""

from fastapi.param_functions import Depends
from gws_core import AuthorizationService

from gws_eln.activities.activity_dto import ActivityDTO
from gws_eln.core.eln_settings import eln_api
from gws_eln.notes.eln_note_service import ElnNoteService


@eln_api.get(
    "/activity/{activity_id}",
    tags=["ELN Batch"],
    summary="Get batch activity by ID",
)
def get_activity(
    activity_id: str,
    _=Depends(AuthorizationService.check_user_access_token_or_app),
) -> ActivityDTO:
    return ElnNoteService().get_activity(activity_id).to_dto()
