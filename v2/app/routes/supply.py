from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from ..dependencies import DbDep
from ..services.supply_catalog_service import SupplyCatalogService
from .. import schemas

router = APIRouter()
catalog_service = SupplyCatalogService()

@router.post("/supply-catalog/", response_model=schemas.SupplyOption, status_code=status.HTTP_201_CREATED)
def create_supply_option(
    option_create: schemas.SupplyOptionCreate,
    db: DbDep,
):
    """
    Creates a new supply option in the catalog.
    """
    return catalog_service.create_option(db_session=db, option_data=option_create)


@router.get("/supply-catalog/", response_model=List[schemas.SupplyOption])
def read_supply_catalog(
    db: DbDep
):
    """
    Retrieves a list of all models in the supply catalog.
    """
    return catalog_service.get_all_options(db_session=db)



@router.get("/supply-catalog/{option_id}", response_model=schemas.SupplyOption)
def read_supply_option(option_id: int, db: DbDep):
    """
    Retrieves a single supply option by its ID.
    """
    db_option = catalog_service.get_option_by_id(db_session=db, option_id=option_id)
    if not db_option:
        raise HTTPException(status_code=404, detail="Supply option not found")
    return db_option