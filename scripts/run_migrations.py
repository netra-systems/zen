import os
import sys

# Set the DATABASE_URL environment variable
os.environ['DATABASE_URL'] = 'postgresql://postgres:DTprdt5KoQXlEG4Gh9lF@localhost:5433/netra_dev'

# Run the alembic command
os.system('alembic -c config/alembic.ini upgrade head')