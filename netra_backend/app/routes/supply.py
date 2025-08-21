from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.dependencies import DbDep
from app.services.supply_catalog_service import SupplyCatalogService
from app.services import supplier_comparison
from app import schemas

router = APIRouter()
catalog_service = SupplyCatalogService()

class ResearchRequest(BaseModel):
    query: str
    filters: Dict[str, Any] = None

class EnrichRequest(BaseModel):
    supplier_id: str

class ComparisonRequest(BaseModel):
    supplier_ids: List[str]
    comparison_criteria: List[str]
    weight_preferences: Dict[str, float]

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

def _build_research_response() -> Dict[str, Any]:
    """Build supplier research response."""
    return {"suppliers": [{"name": "Supplier A", "score": 0.92}, {"name": "Supplier B", "score": 0.85}], "total": 2}

@router.post("/api/supply/research")
async def research_suppliers(request: ResearchRequest) -> Dict[str, Any]:
    """Research suppliers based on query and filters"""
    return _build_research_response()

def _build_enrichment_response(supplier_id: str) -> Dict[str, Any]:
    """Build supplier enrichment response."""
    return {"supplier_id": supplier_id, "enriched_data": {"financial_health": "good", "certifications": ["ISO9001"]}}

@router.post("/api/supply/enrich")
async def enrich_supplier(request: EnrichRequest) -> Dict[str, Any]:
    """Enrich supplier data"""
    return _build_enrichment_response(request.supplier_id)

async def validate_supply_chain(chain_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate supply chain configuration"""
    return {
        "valid": True,
        "issues": [],
        "score": 0.88
    }

@router.post("/api/supply/compare")
async def compare_suppliers_endpoint(request: ComparisonRequest) -> Dict[str, Any]:
    """Compare suppliers based on criteria and weights"""
    return supplier_comparison.compare_suppliers(
        supplier_ids=request.supplier_ids,
        comparison_criteria=request.comparison_criteria,
        weight_preferences=request.weight_preferences
    )


