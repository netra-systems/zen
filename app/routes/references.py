from fastapi import APIRouter, Depends, HTTPException, Query
from app.db.session import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from app.db.models_postgres import Reference
from app.schemas import ReferenceGetResponse, ReferenceItem, ReferenceCreateRequest, ReferenceUpdateRequest
from typing import Optional

router = APIRouter()

@router.get("/references", response_model=ReferenceGetResponse)
async def get_references(
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of items to return"),
    db: AsyncSession = Depends(get_db_session)
) -> ReferenceGetResponse:
    """
    Returns a paginated list of available @reference items.
    
    Args:
        offset: Number of items to skip (default: 0)
        limit: Maximum number of items to return (default: 100, max: 1000)
    """
    async with db as session:
        # Get total count for pagination metadata
        count_result = await session.execute(select(func.count(Reference.id)))
        total = count_result.scalar()
        
        # Get paginated results
        query = select(Reference).offset(offset).limit(limit)
        result = await session.execute(query)
        references = result.scalars().all()
        
        return ReferenceGetResponse(
            references=references,
            total=total,
            offset=offset,
            limit=limit
        )

@router.get("/references/{reference_id}", response_model=ReferenceItem)
async def get_reference(reference_id: int, db: AsyncSession = Depends(get_db_session)) -> ReferenceItem:
    """
    Returns a specific @reference item.
    """
    async with db as session:
        result = await session.execute(select(Reference).filter(Reference.id == reference_id))
        reference = result.scalars().first()
        if not reference:
            raise HTTPException(status_code=404, detail="Reference not found")
        return reference

@router.post("/references", response_model=ReferenceItem)
async def create_reference(reference: ReferenceCreateRequest, db: AsyncSession = Depends(get_db_session)) -> ReferenceItem:
    """
    Creates a new @reference item.
    """
    async with db as session:
        db_reference = Reference(**reference.dict())
        session.add(db_reference)
        await session.commit()
        await session.refresh(db_reference)
        return db_reference

@router.put("/references/{reference_id}", response_model=ReferenceItem)
async def update_reference(reference_id: int, reference: ReferenceUpdateRequest, db: AsyncSession = Depends(get_db_session)) -> ReferenceItem:
    """
    Updates a specific @reference item.
    """
    async with db as session:
        result = await session.execute(select(Reference).filter(Reference.id == reference_id))
        db_reference = result.scalars().first()
        if not db_reference:
            raise HTTPException(status_code=404, detail="Reference not found")

        for key, value in reference.dict(exclude_unset=True).items():
            setattr(db_reference, key, value)

        await session.commit()
        await session.refresh(db_reference)
        return db_reference
