from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from ..config import settings
import logging

engine = create_engine(settings.database_url, echo=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency to get a synchronous DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
