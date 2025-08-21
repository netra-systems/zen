from sqlalchemy import create_engine
from app.db.base import Base
# Import all model modules to ensure all tables are registered with Base
from app.db.models_user import User, Secret, ToolUsageLog
from app.db.models_postgres import Supply, Analysis, AnalysisResult, SupplyOption
from app.db.models_content import *  # Import all content models
from app.db.models_agent_state import *  # Import all agent state models

DATABASE_URL = "postgresql://postgres:123@localhost/netra"

engine = create_engine(DATABASE_URL)

Base.metadata.create_all(bind=engine, checkfirst=True)

print("Tables created successfully (if they didn't already exist).")