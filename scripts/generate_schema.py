from sqlalchemy import create_engine
from sqlalchemy.schema import CreateTable

from netra_backend.app.config import settings
from netra_backend.app.db.base import Base
from netra_backend.app.db.models_postgres import *

engine = create_engine(settings.database_url.replace("asyncpg", "psycopg2"))

with open("schema.sql", "w") as f:
    for table in Base.metadata.sorted_tables:
        f.write(str(CreateTable(table).compile(engine)))
        f.write(";\n")