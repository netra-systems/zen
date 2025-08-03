from sqlalchemy import create_engine
from app.db.base import Base
from app.db.models_postgres import User, Supply, Analysis, AnalysisResult, SupplyOption

DATABASE_URL = "postgresql://postgres:123@localhost/netra"

engine = create_engine(DATABASE_URL)

Base.metadata.create_all(bind=engine)

print("Tables created successfully.")
