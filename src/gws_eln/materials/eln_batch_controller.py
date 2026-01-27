"""Controller for ELN batch action endpoints.

Provides batch-centric API endpoints for inventory actions.
Registered as a custom brick FastAPI app, mounted at /brick/gws_eln/.
"""

from fastapi.param_functions import Depends
from gws_core import AuthorizationService

from gws_eln.core.eln_settings import eln_api
from gws_eln.materials.batch_activity_dto import BatchActivityResponseDTO
from gws_eln.materials.material_batch_dto import (
    CreateAliquotDTO,
    DecrementQuantityDTO,
    DiscardBatchDTO,
    MoveBatchDTO,
    ReceiveBatchDTO,
    RelabelBatchDTO,
    UseBatchDTO,
)
from gws_eln.materials.material_batch_service import MaterialBatchService


@eln_api.post(
    "/batch/{batch_id}/receive",
    tags=["ELN Batch"],
    summary="Receive additional stock to a batch",
)
def receive_batch(
    batch_id: str,
    dto: ReceiveBatchDTO,
    _=Depends(AuthorizationService.check_user_access_token),
) -> BatchActivityResponseDTO:
    service = MaterialBatchService()
    result = service.receive_batch(batch_id, dto)
    return result.to_dto()


@eln_api.post(
    "/batch/{batch_id}/consume",
    tags=["ELN Batch"],
    summary="Consume quantity from a batch",
)
def consume_batch(
    batch_id: str,
    dto: DecrementQuantityDTO,
    _=Depends(AuthorizationService.check_user_access_token),
) -> BatchActivityResponseDTO:
    service = MaterialBatchService()
    result = service.consume_quantity(batch_id, dto)
    return result.to_dto()


@eln_api.post(
    "/batch/{batch_id}/move",
    tags=["ELN Batch"],
    summary="Move a batch to a different location",
)
def move_batch(
    batch_id: str,
    dto: MoveBatchDTO,
    _=Depends(AuthorizationService.check_user_access_token),
) -> BatchActivityResponseDTO:
    service = MaterialBatchService()
    result = service.move_batch(batch_id, dto)
    return result.to_dto()


@eln_api.post(
    "/batch/{batch_id}/use",
    tags=["ELN Batch"],
    summary="Record a USE activity on a batch",
)
def use_batch(
    batch_id: str,
    dto: UseBatchDTO,
    _=Depends(AuthorizationService.check_user_access_token),
) -> BatchActivityResponseDTO:
    service = MaterialBatchService()
    result = service.use_batch(batch_id, dto)
    return result.to_dto()


@eln_api.post(
    "/batch/{batch_id}/discard",
    tags=["ELN Batch"],
    summary="Discard a batch",
)
def discard_batch(
    batch_id: str,
    dto: DiscardBatchDTO,
    _=Depends(AuthorizationService.check_user_access_token),
) -> BatchActivityResponseDTO:
    service = MaterialBatchService()
    result = service.discard_batch(batch_id, dto)
    return result.to_dto()


@eln_api.post(
    "/batch/{batch_id}/aliquot",
    tags=["ELN Batch"],
    summary="Create an aliquot from a batch",
)
def create_aliquot(
    batch_id: str,
    dto: CreateAliquotDTO,
    _=Depends(AuthorizationService.check_user_access_token),
) -> BatchActivityResponseDTO:
    service = MaterialBatchService()
    dto.parent_batch_id = batch_id
    result = service.create_aliquot(dto)
    return result.to_dto()


@eln_api.post(
    "/batch/{batch_id}/relabel",
    tags=["ELN Batch"],
    summary="Relabel a batch",
)
def relabel_batch(
    batch_id: str,
    dto: RelabelBatchDTO,
    _=Depends(AuthorizationService.check_user_access_token),
) -> BatchActivityResponseDTO:
    service = MaterialBatchService()
    result = service.relabel_batch(batch_id, dto)
    return result.to_dto()
