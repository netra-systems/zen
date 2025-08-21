from fastapi import APIRouter, Depends, HTTPException, Query
from netra_backend.app.dependencies import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession
from netra_backend.app.services.database_operations_service import database_operations_service
from netra_backend.app.schemas.Reference import ReferenceGetResponse, ReferenceItem, ReferenceCreateRequest, ReferenceUpdateRequest
from typing import Optional

router = APIRouter()

async def _get_total_references_count(session: AsyncSession) -> int:
    """Get total count of references."""
    return await database_operations_service.get_references_count(session)

async def _get_paginated_references(session: AsyncSession, offset: int, limit: int):
    """Get paginated references."""
    return await database_operations_service.get_paginated_references(session, offset, limit)

def _build_references_response(references, total: int, offset: int, limit: int) -> ReferenceGetResponse:
    """Build paginated references response."""
    return ReferenceGetResponse(references=references, total=total, offset=offset, limit=limit)

@router.get("/references", response_model=ReferenceGetResponse)
async def get_references(
    offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000), db: AsyncSession = Depends(get_db_session)
) -> ReferenceGetResponse:
    """Returns a paginated list of available @reference items."""
    total = await _get_total_references_count(db)
    references = await _get_paginated_references(db, offset, limit)
    return _build_references_response(references, total, offset, limit)

@router.get("/references/search")
async def search_references(query: Optional[str] = Query(None), db: AsyncSession = Depends(get_db_session)):
    """Search references by name or description."""
    return await database_operations_service.search_references(db, query)

async def _get_reference_safe(reference_id: str, session: AsyncSession) -> ReferenceItem:
    """Get reference with validation."""
    reference = await database_operations_service.get_reference_by_id(session, reference_id)
    if not reference:
        raise HTTPException(status_code=404, detail="Reference not found")
    return reference

@router.get("/references/{reference_id}", response_model=ReferenceItem)
async def get_reference(reference_id: str, db: AsyncSession = Depends(get_db_session)) -> ReferenceItem:
    """Returns a specific @reference item."""
    return await _get_reference_safe(reference_id, db)

async def _create_reference_in_db(reference: ReferenceCreateRequest, session: AsyncSession) -> ReferenceItem:
    """Create reference in database."""
    return await database_operations_service.create_reference(session, reference.model_dump())

@router.post("/references", response_model=ReferenceItem, status_code=201)
async def create_reference(reference: ReferenceCreateRequest, db: AsyncSession = Depends(get_db_session)) -> ReferenceItem:
    """Creates a new @reference item."""
    return await _create_reference_in_db(reference, db)

async def _get_reference_by_id(session: AsyncSession, reference_id: str):
    """Get reference by ID or raise 404."""
    db_reference = await database_operations_service.get_reference_by_id(session, reference_id)
    if not db_reference:
        raise HTTPException(status_code=404, detail="Reference not found")
    return db_reference

def _update_reference_fields(db_reference, reference: ReferenceUpdateRequest) -> None:
    """Update reference fields from request."""
    for key, value in reference.model_dump(exclude_unset=True).items():
        setattr(db_reference, key, value)

async def _update_reference_in_db(reference_id: str, reference: ReferenceUpdateRequest, session: AsyncSession) -> ReferenceItem:
    """Update reference in database."""
    db_reference = await _get_reference_by_id(session, reference_id)
    update_data = reference.model_dump(exclude_unset=True)
    return await database_operations_service.update_reference(session, db_reference, update_data)

@router.put("/references/{reference_id}", response_model=ReferenceItem)
async def update_reference(reference_id: str, reference: ReferenceUpdateRequest, db: AsyncSession = Depends(get_db_session)) -> ReferenceItem:
    """Updates a specific @reference item."""
    return await _update_reference_in_db(reference_id, reference, db)

async def _get_reference_or_404(session: AsyncSession, reference_id: str):
    """Get reference or raise 404 error."""
    db_reference = await database_operations_service.get_reference_by_id(session, reference_id)
    if not db_reference:
        raise HTTPException(status_code=404, detail="Reference not found")
    return db_reference

async def _patch_reference_in_db(reference_id: str, reference: ReferenceUpdateRequest, session: AsyncSession) -> ReferenceItem:
    """Patch reference in database."""
    db_reference = await _get_reference_or_404(session, reference_id)
    update_data = reference.model_dump(exclude_unset=True)
    return await database_operations_service.update_reference(session, db_reference, update_data)

@router.patch("/references/{reference_id}", response_model=ReferenceItem)
async def patch_reference(reference_id: str, reference: ReferenceUpdateRequest, db: AsyncSession = Depends(get_db_session)) -> ReferenceItem:
    """Partially update a reference."""
    return await _patch_reference_in_db(reference_id, reference, db)

async def _delete_reference_from_db(session: AsyncSession, db_reference) -> dict:
    """Delete reference from database."""
    return await database_operations_service.delete_reference(session, db_reference)

@router.delete("/references/{reference_id}", status_code=204)
async def delete_reference(reference_id: str, db: AsyncSession = Depends(get_db_session)):
    """Delete a reference."""
    db_reference = await _get_reference_or_404(db, reference_id)
    return await _delete_reference_from_db(db, db_reference)
