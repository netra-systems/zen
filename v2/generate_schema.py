from app.db.base import Base
from app.db.models_postgres import *
from sqlalchemy import create_engine
from app.config import settings

engine = create_engine(settings.database_url.replace("asyncpg", "psycopg2"))

with open("schema.sql", "w") as f:
    for table in Base.metadata.sorted_tables:
        f.write(str(table.compile(engine)))
        f.write(";\n")
