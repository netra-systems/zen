# /api.py
import os
import logging
import uuid
from typing import Dict, List
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session

# Import all services and database components
from services.credential_manager import get_credentials, MOCK_SECRET_STORE
from services.database import SessionLocal, create_db_and_tables
from services.supply_catalog_service import SupplyCatalog, SupplyOption, SupplyOptionCreate

# --- Configuration & App Initialization ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

# On startup, create the database and tables if they don't exist
create_db_and_tables()

app = FastAPI(
    title="Netra Log Analysis API",
    description="API to manage customer credentials, supply catalog, and trigger analysis.",
    version="1.1.0"
)

app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET_KEY", "a_very_secret_key_for_dev"))
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# --- OAuth and Pydantic Models ---
# (Content is identical to previous version, omitted for brevity)
oauth = OAuth()
oauth.register(
    name='google',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    client_kwargs={'scope': 'openid email profile'}
)

class ClickHouseCredentials(BaseModel):
    host: str; port: int = 9440; user: str; password: str = Field(..., min_length=1); database: str

class AnalysisRun(BaseModel):
    run_id: str; status: str = "pending"; message: str

analysis_statuses: Dict[str, Dict] = {}

# --- Database Dependency ---
def get_db():
    """Dependency to get a DB session for each request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Helper Functions and Auth Endpoints ---
# (get_user_from_session, login, auth, logout, get_me are identical, omitted for brevity)
def get_user_from_session(request: Request) -> Dict:
    user = request.session.get('user')
    if not user: raise HTTPException(status_code=401, detail="Not authenticated")
    return user

def run_full_analysis_pipeline(customer_id: str, creds: Dict):
    # This function now needs to create its own DB session for the background task
    db = SessionLocal()
    try:
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        analysis_statuses[run_id] = {"status": "starting", "customer_id": customer_id}
        # ... (rest of the pipeline logic is identical)
    finally:
        db.close()

@app.get("/login/google")
async def login_via_google(request: Request):
    redirect_uri = request.url_for('auth_via_google')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.get("/auth/google")
async def auth_via_google(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
        user = token.get('userinfo')
        if user: request.session['user'] = dict(user)
    except Exception as e:
        return RedirectResponse(url="/?error=auth_failed")
    return RedirectResponse(url="/")

@app.get("/logout")
async def logout(request: Request):
    request.session.pop('user', None)
    return RedirectResponse(url="/")

@app.get("/api/me")
async def get_me(user: Dict = Depends(get_user_from_session)):
    return JSONResponse(user)

# --- Core API Endpoints ---
@app.post("/api/credentials")
async def save_credentials(creds: ClickHouseCredentials, user: Dict = Depends(get_user_from_session)):
    customer_id = user.get('email')
    secret_name = f"{customer_id}_ch_creds"
    MOCK_SECRET_STORE[secret_name] = creds.dict()
    return JSONResponse({"message": "Credentials stored successfully."})

@app.post("/api/analyze", response_model=AnalysisRun)
async def start_analysis(background_tasks: BackgroundTasks, user: Dict = Depends(get_user_from_session)):
    customer_id = user.get('email')
    secret_name = f"{customer_id}_ch_creds"
    try:
        creds = get_credentials(secret_name)
    except ValueError:
        raise HTTPException(status_code=404, detail="Credentials not found.")
    
    background_tasks.add_task(run_full_analysis_pipeline, customer_id, creds)
    run_id = f"run_init_{uuid.uuid4().hex[:4]}"
    return AnalysisRun(run_id=run_id, message="Analysis initiated.")

@app.get("/api/status/{run_id}")
async def get_analysis_status(run_id: str, user: Dict = Depends(get_user_from_session)):
    status = analysis_statuses.get(run_id)
    if not status or status.get("customer_id") != user.get("email"):
        raise HTTPException(status_code=404, detail="Analysis run not found or not authorized.")
    return JSONResponse(status)

# --- NEW: Supply Catalog API Endpoints ---
@app.get("/api/supply", response_model=List[SupplyOption])
async def get_supply_options(db: Session = Depends(get_db)):
    """Get all available supply options."""
    catalog = SupplyCatalog(db)
    return catalog.get_all_options()

@app.post("/api/supply", response_model=SupplyOption, status_code=201)
async def create_supply_option(option: SupplyOptionCreate, db: Session = Depends(get_db)):
    """Create a new supply option."""
    catalog = SupplyCatalog(db)
    return catalog.add_option(option)

@app.put("/api/supply/{option_id}", response_model=SupplyOption)
async def update_supply_option(option_id: str, option: SupplyOptionCreate, db: Session = Depends(get_db)):
    """Update an existing supply option by its ID."""
    catalog = SupplyCatalog(db)
    updated_option = catalog.update_option(option_id, option)
    if not updated_option:
        raise HTTPException(status_code=404, detail="Supply option not found.")
    return updated_option

@app.delete("/api/supply/{option_id}", status_code=204)
async def delete_supply_option(option_id: str, db: Session = Depends(get_db)):
    """Delete a supply option by its ID."""
    catalog = SupplyCatalog(db)
    if not catalog.delete_option(option_id):
        raise HTTPException(status_code=404, detail="Supply option not found.")
    return

# --- Main Entry Point for development ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
