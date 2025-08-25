import os

import alembic.config

# Use centralized environment management
try:
    from dev_launcher.isolated_environment import get_env
except ImportError:
    # Fallback for standalone execution
    class FallbackEnv:
        def get(self, key, default=None):
            return os.getenv(key, default)
        def set(self, key, value, source="migration_script"):
            os.environ[key] = value
    
    def get_env():
        return FallbackEnv()

print(os.getcwd())
env = get_env()
user = env.get('USER')
env.set('DATABASE_URL', f'postgresql+asyncpg://{user}@localhost/netra', 'run_migrations')
alembic_args = [
    '-c',
    'config/alembic.ini',
    'upgrade',
    'head',
]
alembic.config.main(argv=alembic_args)
