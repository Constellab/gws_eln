"""Controller for ELN activity action endpoints.

Provides activity-centric API endpoints.
Registered as a custom brick FastAPI app, mounted at /brick/gws_eln/.
"""

from fastapi.param_functions import Depends
from gws_core import AuthorizationService

from gws_eln.activities.activity_dto import ActivityDTO
from gws_eln.core.eln_settings import eln_api
from gws_eln.notes.eln_note_service import ElnNoteService

_check_access = Depends(AuthorizationService.check_user_access_token_or_app)


@eln_api.get(
    "/activity/{activity_id}",
    tags=["ELN Activity"],
    summary="Get activity by ID",
)
def get_activity(
    activity_id: str,
    _=_check_access,
) -> ActivityDTO:
    return ElnNoteService().get_activity(activity_id).to_dto()
