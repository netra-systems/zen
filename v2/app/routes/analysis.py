# /v2/app/routes/analysis.py
import logging
from ..logging_config_custom.logger import logger

from typing import List
import uuid
from ..dependencies import DbDep, ActiveUserDep
from .. import schema
from ..db.models_postgres import Analysis
from fastapi import APIRouter, status, BackgroundTasks, Request

router = APIRouter()

@router.post("/runs", response_model=schema.AnalysisRunPublic, status_code=status.HTTP_202_ACCEPTED)
def start_new_analysis_run(
    run_create: schema.AnalysisRunCreate,
    background_tasks: BackgroundTasks,
    db: DbDep,
    current_user: ActiveUserDep,
    request: Request,
    use_deepagents: bool = False,
    use_deepagents_v2: bool = False
):
    """Creates an analysis run record and starts the pipeline in the background."""
    new_run = Analysis(
        created_by_id=current_user.id,
        name=run_create.source_table,
        description=run_create.source_table
    )
    db.add(new_run)
    db.commit()
    db.refresh(new_run)

    
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
