from fastapi import APIRouter, Depends, HTTPException
from app.db.session import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.models_postgres import Reference
from app.models.references import ReferenceGetResponse, ReferenceItem, ReferenceCreateRequest, ReferenceUpdateRequest

router = APIRouter()

@router.get("/references", response_model=ReferenceGetResponse)
async def get_references(db: AsyncSession = Depends(get_db_session)):
    """
    Returns a list of available @reference items.
    """
    async with db as session:
        result = await session.execute(select(Reference))
        references = result.scalars().all()
        return ReferenceGetResponse(references=references)


@router.get("/references/{reference_id}", response_model=ReferenceItem)
async def get_reference(reference_id: int, db: AsyncSession = Depends(get_db_session)):
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
async def create_reference(reference: ReferenceCreateRequest, db: AsyncSession = Depends(get_db_session)):
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
async def update_reference(reference_id: int, reference: ReferenceUpdateRequest, db: AsyncSession = Depends(get_db_session)):
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