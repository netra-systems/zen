import os
from functools import lru_cache
from pydantic_settings import BaseSettings  # <-- CORRECTED IMPORT
from dotenv import load_dotenv

load_dotenv()

# Check if the script is being run for OpenAPI schema generation.
# The `generate_openAPI_schema.py` script will set this environment variable.
IS_SCHEMA_GENERATION = os.environ.get("GENERATE_SCHEMA_MODE") == "1"

class Settings(BaseSettings):
    """
    Manages application settings and environment variables.
    It automatically reads variables from a .env file or the environment.
    """
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    CLICKHOUSE_HOST: str
    CLICKHOUSE_PORT: int
    CLICKHOUSE_USER: str
    CLICKHOUSE_PASSWORD: str
    CLICKHOUSE_DB: str
    DATABASE_URL: str

    class Config:
        # Specifies the file to load environment variables from.
        env_file = ".env"

# When generating the OpenAPI schema, we don't need real credentials.
# We can instantiate Settings with dummy values to prevent errors about
# missing environment variables or a missing .env file.
if IS_SCHEMA_GENERATION:
    settings = Settings(
        database_url="postgresql+asyncpg://user:pass@dummy-postgres:5432/netra",
        clickhouse_host="dummy-clickhouse",
        clickhouse_port=9000,
        clickhouse_user="user",
        clickhouse_password="password",
        clickhouse_db="netra",
        secret_key="a-super-secret-key-for-dev-and-schema-generation"
    )
else:
    # In normal operation (e.g., when running the web server),
    # load the settings from the environment. Pydantic will raise
    # an error if required settings are not found.
    settings = Settings()
