"""Controller for ELN item lineage endpoints.

Exposes the derived lineage DAG (ancestors + descendants) for a focus item in
a single read-only call (decisions v2 §16). Registered as a custom brick
FastAPI app, mounted at /brick/gws_eln/.
"""

from fastapi.param_functions import Depends
from gws_core import AuthorizationService

from gws_eln.core.eln_settings import eln_api
from gws_eln.lineage.lineage_dto import LineageGraphDTO
from gws_eln.lineage.lineage_service import LineageService

_check_access = Depends(AuthorizationService.check_user_access_token_or_app)


@eln_api.get(
    "/item/{item_id}/lineage",
    tags=["ELN Lineage"],
    summary="Get the lineage DAG (ancestors + descendants) of an item",
)
def get_item_lineage(
    item_id: str,
    _=_check_access,
) -> LineageGraphDTO:
    return LineageService().get_lineage_graph(item_id)
