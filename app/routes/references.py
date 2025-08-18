from fastapi import APIRouter, Depends, HTTPException, Query
from app.db.session import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, or_
from app.db.models_content import Reference
from app.schemas import ReferenceGetResponse, ReferenceItem, ReferenceCreateRequest, ReferenceUpdateRequest
from typing import Optional

router = APIRouter()

async def _get_total_references_count(session: AsyncSession) -> int:
    """Get total count of references."""
    count_result = await session.execute(select(func.count(Reference.id)))
    return count_result.scalar()

async def _get_paginated_references(session: AsyncSession, offset: int, limit: int):
    """Get paginated references."""
    query = select(Reference).offset(offset).limit(limit)
    result = await session.execute(query)
    return result.scalars().all()

def _build_references_response(references, total: int, offset: int, limit: int) -> ReferenceGetResponse:
    """Build paginated references response."""
    return ReferenceGetResponse(references=references, total=total, offset=offset, limit=limit)

@router.get("/references", response_model=ReferenceGetResponse)
async def get_references(
    offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000), db: AsyncSession = Depends(get_db_session)
) -> ReferenceGetResponse:
    """Returns a paginated list of available @reference items."""
    async with db as session:
        total = await _get_total_references_count(session)
        references = await _get_paginated_references(session, offset, limit)
        return _build_references_response(references, total, offset, limit)

def _build_search_filter(query: str):
    """Build search filter for references."""
    return or_(Reference.name.ilike(f"%{query}%"), Reference.description.ilike(f"%{query}%"))

def _build_search_query(query: Optional[str]):
    """Build search query with optional filter."""
    base_query = select(Reference)
    if query:
        base_query = base_query.filter(_build_search_filter(query))
    return base_query

@router.get("/references/search")
async def search_references(query: Optional[str] = Query(None), db: AsyncSession = Depends(get_db_session)):
    """Search references by name or description."""
    async with db as session:
        search_query = _build_search_query(query)
        result = await session.execute(search_query)
        return result.scalars().all()

async def _get_reference_safe(reference_id: str, session: AsyncSession) -> ReferenceItem:
    """Get reference with validation."""
    result = await session.execute(select(Reference).filter(Reference.id == reference_id))
    reference = result.scalars().first()
    if not reference:
        raise HTTPException(status_code=404, detail="Reference not found")
    return reference

@router.get("/references/{reference_id}", response_model=ReferenceItem)
async def get_reference(reference_id: str, db: AsyncSession = Depends(get_db_session)) -> ReferenceItem:
    """Returns a specific @reference item."""
    async with db as session:
        return await _get_reference_safe(reference_id, session)

async def _create_reference_in_db(reference: ReferenceCreateRequest, session: AsyncSession) -> ReferenceItem:
    """Create reference in database."""
    db_reference = Reference(**reference.model_dump())
    session.add(db_reference)
    await session.commit()
    await session.refresh(db_reference)
    return db_reference

@router.post("/references", response_model=ReferenceItem, status_code=201)
async def create_reference(reference: ReferenceCreateRequest, db: AsyncSession = Depends(get_db_session)) -> ReferenceItem:
    """Creates a new @reference item."""
    async with db as session:
        return await _create_reference_in_db(reference, session)

async def _get_reference_by_id(session: AsyncSession, reference_id: str) -> Reference:
    """Get reference by ID or raise 404."""
    result = await session.execute(select(Reference).filter(Reference.id == reference_id))
    db_reference = result.scalars().first()
    if not db_reference:
        raise HTTPException(status_code=404, detail="Reference not found")
    return db_reference

def _update_reference_fields(db_reference: Reference, reference: ReferenceUpdateRequest) -> None:
    """Update reference fields from request."""
    for key, value in reference.model_dump(exclude_unset=True).items():
        setattr(db_reference, key, value)

async def _update_reference_in_db(reference_id: str, reference: ReferenceUpdateRequest, session: AsyncSession) -> ReferenceItem:
    """Update reference in database."""
    db_reference = await _get_reference_by_id(session, reference_id)
    _update_reference_fields(db_reference, reference)
    await session.commit()
    await session.refresh(db_reference)
    return db_reference

@router.put("/references/{reference_id}", response_model=ReferenceItem)
async def update_reference(reference_id: str, reference: ReferenceUpdateRequest, db: AsyncSession = Depends(get_db_session)) -> ReferenceItem:
    """Updates a specific @reference item."""
    async with db as session:
        return await _update_reference_in_db(reference_id, reference, session)

async def _get_reference_or_404(session: AsyncSession, reference_id: str) -> Reference:
    """Get reference or raise 404 error."""
    result = await session.execute(select(Reference).filter(Reference.id == reference_id))
    db_reference = result.scalar_one_or_none()
    if not db_reference:
        raise HTTPException(status_code=404, detail="Reference not found")
    return db_reference

async def _patch_reference_in_db(reference_id: str, reference: ReferenceUpdateRequest, session: AsyncSession) -> ReferenceItem:
    """Patch reference in database."""
    db_reference = await _get_reference_or_404(session, reference_id)
    _update_reference_fields(db_reference, reference)
    await session.commit()
    await session.refresh(db_reference)
    return db_reference

@router.patch("/references/{reference_id}", response_model=ReferenceItem)
async def patch_reference(reference_id: str, reference: ReferenceUpdateRequest, db: AsyncSession = Depends(get_db_session)) -> ReferenceItem:
    """Partially update a reference."""
    async with db as session:
        return await _patch_reference_in_db(reference_id, reference, session)

async def _delete_reference_from_db(session: AsyncSession, db_reference: Reference) -> dict:
    """Delete reference from database."""
    await session.delete(db_reference)
    await session.commit()
    return {"status": "deleted"}

@router.delete("/references/{reference_id}", status_code=204)
async def delete_reference(reference_id: str, db: AsyncSession = Depends(get_db_session)):
    """Delete a reference."""
    async with db as session:
        db_reference = await _get_reference_or_404(session, reference_id)
        return await _delete_reference_from_db(session, db_reference)
