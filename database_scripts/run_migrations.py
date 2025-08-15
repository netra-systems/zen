import os
import alembic.config

print(os.getcwd())
user = os.environ.get('USER')
os.environ['DATABASE_URL'] = f'postgresql+asyncpg://{user}@localhost/netra'
alembic_args = [
    '-c',
    'config/alembic.ini',
    'upgrade',
    'head',
]
alembic.config.main(argv=alembic_args)
