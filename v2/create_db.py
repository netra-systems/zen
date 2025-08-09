import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Connect to the default database
conn = psycopg2.connect(dbname="postgres", user="postgres", host="localhost", password="123")
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

# Create a cursor to perform database operations
cur = conn.cursor()

# Check if the database exists
cur.execute("SELECT 1 FROM pg_database WHERE datname = 'netra'")
exists = cur.fetchone()

if exists:
    # Terminate other connections
    cur.execute("""
        SELECT pg_terminate_backend(pg_stat_activity.pid)
        FROM pg_stat_activity
        WHERE pg_stat_activity.datname = 'netra' AND pid <> pg_backend_pid();
    """)
    print("Terminated other connections to 'netra' database.")

    # Drop the database
    cur.execute("DROP DATABASE netra")
    print("Database 'netra' dropped successfully.")

# Create the database
cur.execute("CREATE DATABASE netra")
print("Database 'netra' created successfully.")

# Close the cursor and connection
cur.close()
conn.close()