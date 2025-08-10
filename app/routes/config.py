from fastapi import APIRouter, Depends
from app.config import settings
from app import schemas

router = APIRouter()

@router.get("/config", response_model=schemas.WebSocketConfig)
async def get_config():
    return settings.ws_config