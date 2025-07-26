# /v2/routes/supply.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from .. import models, dependencies
from ..database import get_db

router = APIRouter()

@router.post("/supply-catalog/", response_model=models.SupplyModel, status_code=status.HTTP_201_CREATED)
def create_supply_model(
    supply_model: models.SupplyModelBase,
    db: Session = Depends(get_db),
    # Optional: Add admin-only dependency here later
):
    """
    Creates a new supply model in the catalog.
    """
    db_model = models.SupplyModel.model_validate(supply_model)
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    return db_model


@router.get("/supply-catalog/", response_model=List[models.SupplyModel])
def read_supply_catalog(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Retrieves a list of all models in the supply catalog.
    """
    statement = select(models.SupplyModel).offset(skip).limit(limit)
    supply_models = db.exec(statement).all()
    return supply_models


@router.get("/supply-catalog/{model_id}", response_model=models.SupplyModel)
def read_supply_model(model_id: int, db: Session = Depends(get_db)):
    """
    Retrieves a single supply model by its ID.
    """
    db_model = db.get(models.SupplyModel, model_id)
    if not db_model:
        raise HTTPException(status_code=404, detail="Supply model not found")
    return db_model
