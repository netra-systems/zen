from sqlalchemy.orm import declarative_base

# This is the central Base for all SQLAlchemy models.
# All models will inherit from this Base. This avoids circular imports by creating
# a single, dependency-free source for the declarative base.
Base = declarative_base()