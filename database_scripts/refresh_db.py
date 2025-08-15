import psycopg2
import os
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

DATABASE_NAME = "netra"

# SECURITY: Get password from environment variable - never hardcode passwords
password = os.getenv('POSTGRES_PASSWORD')
if not password:
    raise ValueError("POSTGRES_PASSWORD environment variable must be set")

# 1. Drop and recreate the database
conn = psycopg2.connect(dbname="postgres", user="postgres", host="localhost", password=password)
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

print(f"Database '{DATABASE_NAME}' created successfully. Now run migrations.")