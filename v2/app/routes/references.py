
from fastapi import APIRouter
from app.models.references import ReferenceGetResponse, ReferenceItem

router = APIRouter()

@router.get("/references", response_model=ReferenceGetResponse)
async def get_references():
    """
    Returns a list of available @reference items.
    """
    references = [
        ReferenceItem(name="Synthetic Data", type="source", value="synthetic_data"),
        ReferenceItem(name="Real-time Data", type="source", value="real_time_data"),
        ReferenceItem(name="Last 24 Hours", type="time_period", value="last_24_hours"),
        ReferenceItem(name="Last 7 Days", type="time_period", value="last_7_days"),
        ReferenceItem(name="Last 30 Days", type="time_period", value="last_30_days"),
    ]
    return ReferenceGetResponse(references=references)
