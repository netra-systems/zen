from sqlalchemy import create_engine

from netra_backend.app.db.base import Base
from netra_backend.app.db.models_agent_state import *  # Import all agent state models
from netra_backend.app.db.models_content import *  # Import all content models
from netra_backend.app.db.models_postgres import (
    Analysis,
    AnalysisResult,
    Supply,
    SupplyOption,
)

# Import all model modules to ensure all tables are registered with Base
from netra_backend.app.db.models_user import Secret, ToolUsageLog, User

#removed-legacy= "postgresql://postgres:123@localhost/netra_dev"

engine = create_engine(DATABASE_URL)

Base.metadata.create_all(bind=engine, checkfirst=True)

print("Tables created successfully (if they didn't already exist).")