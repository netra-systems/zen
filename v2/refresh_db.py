import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy import create_engine
from app.db.base import Base
from app.db.models_postgres import User, Supply, Analysis, AnalysisResult, SupplyOption

DATABASE_NAME = "netra"
DATABASE_URL = f"postgresql://postgres:123@localhost/{DATABASE_NAME}"

# 1. Drop and recreate the database
conn = psycopg2.connect(dbname="postgres", user="postgres", host="localhost", password="123")
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cur = conn.cursor()

# Terminate other connections
cur.execute(f"""
    SELECT pg_terminate_backend(pg_stat_activity.pid)
    FROM pg_stat_activity
    WHERE pg_stat_activity.datname = '{DATABASE_NAME}' AND pid <> pg_backend_pid();
""")
print(f"Terminated other connections to '{DATABASE_NAME}' database.")

# Drop the database if it exists
cur.execute(f"DROP DATABASE IF EXISTS {DATABASE_NAME}")
print(f"Database '{DATABASE_NAME}' dropped successfully (if it existed).")

# Create the database
cur.execute(f"CREATE DATABASE {DATABASE_NAME}")
print(f"Database '{DATABASE_NAME}' created successfully.")

cur.close()
conn.close()

# 2. Create tables
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(bind=engine)
print("Tables created successfully.")

print(f"Database '{DATABASE_NAME}' refreshed successfully.")
