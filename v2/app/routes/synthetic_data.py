from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from .. import schemas
from ..services import synthetic_data_service
from ..dependencies import get_db_session
from ..auth.auth_dependencies import get_current_user
from ..db.models_postgres import User

router = APIRouter()

@router.post("/synthetic-data/generate", response_model=schemas.Corpus)
def generate_synthetic_data(
    params: schemas.LogGenParams,
    request: Request,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    db_corpus = synthetic_data_service.generate_synthetic_data(db=db, params=params, user_id=current_user.id)
    return db_corpus
