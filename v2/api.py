# /v2/api.py
import logging
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth

from . import database as db, pydantic_models as schemas
from .config import settings
from .services.supply_catalog_service import SupplyCatalogService
from .services.security_service import security_service
# Import other services and the main analysis function as needed

# --- App Initialization ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
app = FastAPI(title="Netra API V2", version="2.0.0")

# --- Middleware ---
app.add_middleware(SessionMiddleware, secret_key=settings.SESSION_SECRET_KEY)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# --- OAuth Setup ---
oauth = OAuth()
oauth.register(
    name='google',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    client_kwargs={'scope': 'openid email profile'}
)

# --- Dependencies ---
def get_db():
    database = db.SessionLocal()
    try:
        yield database
    finally:
        database.close()

def get_current_user(request: Request, db_session: Session = Depends(get_db)) -> db.User:
    user_info = request.session.get('user')
    if not user_info:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = db_session.query(db.User).filter(db.User.email == user_info['email']).first()
    if not user:
        # Auto-provision user on first login
        user = db.User(email=user_info['email'], full_name=user_info.get('name'))
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return user

# --- Auth Endpoints ---
@app.get("/login/google")
async def login_via_google(request: Request):
    redirect_uri = request.url_for('auth_via_google')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.get("/auth/google")
async def auth_via_google(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')
        if user_info:
            request.session['user'] = dict(user_info)
    except Exception as e:
        logging.error(f"Authentication failed: {e}")
        return RedirectResponse(url="/?error=auth_failed")
    return RedirectResponse(url="/") # Redirect to frontend

@app.get("/logout")
async def logout(request: Request):
    request.session.pop('user', None)
    return RedirectResponse(url="/")

@app.get(f"{settings.API_V2_STR}/me", response_model=schemas.User)
async def get_me(current_user: db.User = Depends(get_current_user)):
    return current_user

# --- Supply Catalog API ---
catalog_service = SupplyCatalogService()

@app.post(f"{settings.API_V2_STR}/supply", response_model=schemas.SupplyOption, status_code=201)
def create_supply_option(option: schemas.SupplyOptionCreate, db_session: Session = Depends(get_db)):
    return catalog_service.create_option(db_session, option)

@app.get(f"{settings.API_V2_STR}/supply", response_model=list[schemas.SupplyOption])
def read_supply_options(db_session: Session = Depends(get_db)):
    return catalog_service.get_all_options(db_session)
    
@app.put(f"{settings.API_V2_STR}/supply/autofill", status_code=200)
def autofill_supply_options(db_session: Session = Depends(get_db)):
    catalog_service.autofill_catalog(db_session)
    return {"message": "Supply catalog autofill process completed."}

# --- Analysis Endpoints (Placeholder) ---
@app.post(f"{settings.API_V2_STR}/analysis/start", response_model=schemas.AnalysisRun)
async def start_analysis(
    request: schemas.AnalysisRunCreate,
    background_tasks: BackgroundTasks,
    current_user: db.User = Depends(get_current_user),
    db_session: Session = Depends(get_db)
):
    # 1. Create a record for the analysis run
    new_run = db.AnalysisRun(user_id=current_user.id, status="pending", config=request.config)
    db_session.add(new_run)
    db_session.commit()
    db_session.refresh(new_run)
    
    # 2. Add the actual analysis task to the background
    # background_tasks.add_task(run_full_analysis_pipeline, run_id=new_run.id, user_id=current_user.id)
    
    # For now, we'll just simulate completion
    background_tasks.add_task(simulate_analysis, run_id=new_run.id)

    return new_run

@app.get(f"{settings.API_V2_STR}/analysis/status/{{run_id}}", response_model=schemas.AnalysisRun)
def get_analysis_status(run_id: str, current_user: db.User = Depends(get_current_user), db_session: Session = Depends(get_db)):
    run = db_session.query(db.AnalysisRun).filter(db.AnalysisRun.id == run_id).first()
    if not run or run.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    return run
    
# --- Placeholder for background task simulation ---
import time
import json
from datetime import datetime

def simulate_analysis(run_id: str):
    db_session = next(get_db())
    try:
        run = db_session.query(db.AnalysisRun).filter(db.AnalysisRun.id == run_id).first()
        if not run: return

        run.status = "running"
        run.execution_log = "Starting analysis...\n"
        db_session.commit()
        time.sleep(5)

        run.execution_log += "Data enrichment complete...\n"
        db_session.commit()
        time.sleep(5)
        
        run.execution_log += "Pattern discovery complete.\n"
        run.status = "completed"
        run.completed_at = datetime.utcnow()
        run.result_summary = {"projected_monthly_savings": 4356.21, "delta_percent": 28.7}
        run.result_details = {"message": "Detailed results would go here."}
        db_session.commit()

    finally:
        db_session.close()

# --- On Startup ---
@app.on_event("startup")
def on_startup():
    db.create_db_and_tables()
    # Autofill the catalog on first startup if empty
    db_session = next(get_db())
    catalog_service.autofill_catalog(db_session)
    db_session.close()
