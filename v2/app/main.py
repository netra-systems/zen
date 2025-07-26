# /v2/main.py
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from . import database as db
from .config import settings
from .services.supply_catalog_service import SupplyCatalogService
from .routes import auth, supply, analysis

# --- App Initialization ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

app = FastAPI(
    title="Netra API V2",
    version="2.0.0",
    description="API for Netra workload analysis and optimization."
)

# --- Middleware ---
# SessionMiddleware must be present for OAuth user session to work.
app.add_middleware(
    SessionMiddleware, 
    secret_key=settings.SESSION_SECRET_KEY
)
# CORS for allowing frontend access
app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], # In production, restrict this to your frontend's domain
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"]
)

# --- API Routers ---
# Include routers from the routes module.
# Authentication routes are at the root, others are prefixed with /api/v2.
app.include_router(auth.router, tags=["Authentication"])
app.include_router(analysis.router, prefix=settings.API_V2_STR, tags=["Analysis & Credentials"])
app.include_router(supply.router, prefix=settings.API_V2_STR, tags=["Supply Catalog"])


# --- Health Check Endpoint ---
@app.get("/", tags=["Root"])
def read_root():
    """A simple health check endpoint."""
    return {"status": "ok", "message": "Welcome to Netra API V2"}

# --- On Startup Event ---
@app.on_event("startup")
def on_startup():
    """
    Actions to perform on application startup.
    - Create database tables if they don't exist.
    - Autofill the supply catalog with default models.
    """
    logging.info("Executing startup events...")
    db.create_db_and_tables()
    
    # Use a database session to autofill the catalog
    db_session = next(db.SessionLocal())
    try:
        catalog_service = SupplyCatalogService()
        catalog_service.autofill_catalog(db_session)
    finally:
        db_session.close()
    logging.info("Startup events completed.")
