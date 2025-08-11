import os
import alembic.config

print(os.getcwd())
os.environ['DATABASE_URL'] = 'postgresql+asyncpg://postgres:123@localhost/netra'
alembic_args = [
    '-c',
    'alembic.ini',
    'upgrade',
    'head',
]
alembic.config.main(argv=alembic_args)
