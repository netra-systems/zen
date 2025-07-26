import os
from pydantic_settings import BaseSettings

# Check if the script is being run for OpenAPI schema generation.
# The `generate_openAPI_schema.py` script will set this environment variable.
IS_SCHEMA_GENERATION = os.environ.get("GENERATE_SCHEMA_MODE") == "1"

class Settings(BaseSettings):
    """
    Defines the application settings.
    These can be loaded from a .env file or environment variables.
    """
    app_env: str = "development"
    database_url: str
    clickhouse_host: str
    clickhouse_port: int
    clickhouse_user: str
    clickhouse_password: str
    clickhouse_db: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    class Config:
        # In normal operation, load settings from a .env file.
        env_file = ".env"

# When generating the OpenAPI schema, we don't need real credentials.
# We can programmatically set dummy environment variables before Pydantic
# attempts to load them. This avoids validation errors and uses the
# intended mechanism of pydantic-settings.
if IS_SCHEMA_GENERATION:
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@dummy-postgres:5432/netra"
    os.environ["CLICKHOUSE_HOST"] = "dummy-clickhouse"
    os.environ["CLICKHOUSE_PORT"] = "9000"  # Env vars must be strings
    os.environ["CLICKHOUSE_USER"] = "user"
    os.environ["CLICKHOUSE_PASSWORD"] = "password"
    os.environ["CLICKHOUSE_DB"] = "netra"
    os.environ["SECRET_KEY"] = "a-super-secret-key-for-dev-and-schema-generation"

# Instantiate Settings.
# In normal operation, it loads from the environment or a .env file.
# If IS_SCHEMA_GENERATION is true, it loads from the dummy environment
# variables that were set in the block above. Pydantic will raise
# an error if required settings are not found from any source.
settings = Settings()
