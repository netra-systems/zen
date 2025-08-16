from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.dependencies import DbDep
from app.services.supply_catalog_service import SupplyCatalogService
from app import schemas

router = APIRouter()
catalog_service = SupplyCatalogService()

class ResearchRequest(BaseModel):
    query: str
    filters: Dict[str, Any] = None

class EnrichRequest(BaseModel):
    supplier_id: str

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

@router.post("/api/supply/research")
async def research_suppliers(request: ResearchRequest) -> Dict[str, Any]:
    """Research suppliers based on query and filters"""
    return {
        "suppliers": [
            {"name": "Supplier A", "score": 0.92},
            {"name": "Supplier B", "score": 0.85}
        ],
        "total": 2
    }

@router.post("/api/supply/enrich")
async def enrich_supplier(request: EnrichRequest) -> Dict[str, Any]:
    """Enrich supplier data"""
    return {
        "supplier_id": request.supplier_id,
        "enriched_data": {
            "financial_health": "good",
            "certifications": ["ISO9001"]
        }
    }


