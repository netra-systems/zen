# /v2/app/routes/analysis.py
import logging
import uuid
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlmodel import Session, select

from .. import schema
from ..db import models_clickhouse

from ..dependencies import ActiveUserDep, DbDep
from ..pipeline import run_full_analysis_pipeline
from ..services.security_service import security_service


router = APIRouter()

@router.post("/credentials", status_code=status.HTTP_204_NO_CONTENT)
def save_credentials(creds: models_clickhouse.ClickHouseCredentials, db: DbDep, current_user: ActiveUserDep):
    """Saves or updates the user's ClickHouse credentials securely."""
    try:
        security_service.save_user_credentials(user_id=current_user.id, credentials=creds, db_session=db)
        logger.info(f"Credentials saved successfully for user_id: {current_user.id}")
    except Exception as e:
        logger.error(f"Failed to save credentials for user_id {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Could not save credentials.")


@router.get("/credentials", response_model=models_clickhouse.ClickHouseCredentials)
def get_credentials(db: DbDep, current_user: ActiveUserDep):
    """Retrieves the user's saved ClickHouse credentials."""
    creds = security_service.get_user_credentials(user_id=current_user.id, db_session=db)
    if not creds:
        raise HTTPException(status_code=404, detail="Credentials not found for this user.")
    return creds


@router.post("/runs", response_model=schema.AnalysisRunPublic, status_code=status.HTTP_202_ACCEPTED)
def start_new_analysis_run(
    run_create: schema.AnalysisRunCreate,
    background_tasks: BackgroundTasks,
    db: DbDep,
    current_user: ActiveUserDep
):
    """Creates an analysis run record and starts the pipeline in the background."""
    new_run = schema.AnalysisRun(
        user_id=current_user.id,
        config={"source_table": run_create.source_table}
    )
    db.add(new_run)
    db.commit()
    db.refresh(new_run)

    background_tasks.add_task(run_full_analysis_pipeline, run_id=new_run.id, user_id=current_user.id)
    logger.info(f"Started analysis run {new_run.id} for user {current_user.email}")
    return new_run


@router.get("/runs/{run_id}", response_model=schema.AnalysisRunPublic)
def get_run_status(run_id: uuid.UUID, db: DbDep, current_user: ActiveUserDep):
    """Retrieves the status and details of a specific analysis run."""
    run = db.exec(
        select(schema.AnalysisRun).where(
            schema.AnalysisRun.id == run_id,
            schema.AnalysisRun.user_id == current_user.id
        )
    ).first()

    if not run:
        raise HTTPException(status_code=404, detail=f"Run with ID {run_id} not found.")
    return run


@router.get("/runs", response_model=List[schema.AnalysisRunPublic])
def get_all_user_runs(db: DbDep, current_user: ActiveUserDep):
    """Retrieves all analysis runs for the current user."""
    runs = db.exec(
        select(schema.AnalysisRun)
        .where(schema.AnalysisRun.user_id == current_user.id)
        .order_by(schema.AnalysisRun.created_at.desc())
    ).all()
    return runs
