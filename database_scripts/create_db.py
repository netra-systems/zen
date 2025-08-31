import os

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Use centralized environment management
try:
    from shared.isolated_environment import get_env
except ImportError:
    # Fallback for standalone execution
    class FallbackEnv:
        def get(self, key, default=None):
            return os.getenv(key, default)
    
    def get_env():
        return FallbackEnv()

# SECURITY: Get password from environment variable using IsolatedEnvironment
env = get_env()
password = env.get('POSTGRES_PASSWORD')
if not password:
    raise ValueError("POSTGRES_PASSWORD environment variable must be set")

# Connect to the default database
conn = psycopg2.connect(dbname="postgres", user="postgres", host="localhost", password=password)
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

# Create a cursor to perform database operations
cur = conn.cursor()

# Check if the database exists
cur.execute("SELECT 1 FROM pg_database WHERE datname = 'netra_dev'")
exists = cur.fetchone()

if not exists:
    # Create the database
    cur.execute("CREATE DATABASE netra_dev")
    print("Database 'netra_dev' created successfully.")
else:
    print("Database 'netra_dev' already exists.")

# Close the cursor and connection
cur.close()
conn.close()
