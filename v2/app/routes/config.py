from fastapi import APIRouter, Depends
from app.config import settings
from app import schemas

router = APIRouter()

@router.get("/config", response_model=schemas.AppConfig)
async def get_config():
    return schemas.AppConfig(
        ws_url=settings.WS_URL
    )
