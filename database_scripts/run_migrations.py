import os

import alembic.config

# Use centralized environment management
try:
    from shared.isolated_environment import get_env
except ImportError:
    # Fallback for standalone execution
    class FallbackEnv:
        def get(self, key, default=None):
            return get_env().get(key, default)
        def set(self, key, value, source="migration_script"):
            os.environ[key] = value
    
    def get_env():
        return FallbackEnv()

print(os.getcwd())
env = get_env()

# Use DatabaseURLBuilder for proper URL construction
from shared.database_url_builder import DatabaseURLBuilder

# Create environment variables for builder
builder_env = env.get_all().copy() if hasattr(env, 'get_all') else {}
builder_env['POSTGRES_HOST'] = builder_env.get('POSTGRES_HOST', 'localhost')
builder_env['POSTGRES_PORT'] = builder_env.get('POSTGRES_PORT', '5432')
builder_env['POSTGRES_DB'] = builder_env.get('POSTGRES_DB', 'netra')
builder_env['POSTGRES_USER'] = builder_env.get('POSTGRES_USER', env.get('USER'))
# Password may not be needed for local connections
if 'POSTGRES_PASSWORD' not in builder_env:
    builder_env['POSTGRES_PASSWORD'] = ''
builder_env['ENVIRONMENT'] = 'development'

builder = DatabaseURLBuilder(builder_env)
# Use async URL for Alembic with asyncpg
database_url = builder.tcp.async_url or builder.development.default_url
env.set('DATABASE_URL', database_url, 'run_migrations')
alembic_args = [
    '-c',
    'config/alembic.ini',
    'upgrade',
    'head',
]
alembic.config.main(argv=alembic_args)
