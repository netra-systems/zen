import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os

# Connect to the default database using current user
user = os.environ.get('USER')
conn = psycopg2.connect(dbname="postgres", user=user, host="localhost")
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

# Create a cursor to perform database operations
cur = conn.cursor()

# Check if the database exists
cur.execute("SELECT 1 FROM pg_database WHERE datname = 'netra'")
exists = cur.fetchone()

if not exists:
    # Create the database
    cur.execute("CREATE DATABASE netra")
    print("Database 'netra' created successfully.")
else:
    print("Database 'netra' already exists.")

# Close the cursor and connection
cur.close()
conn.close()
