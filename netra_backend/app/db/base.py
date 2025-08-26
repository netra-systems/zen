from sqlalchemy.orm import DeclarativeBase

# This is the central Base for all SQLAlchemy models using SQLAlchemy 2.0 patterns.
# All models will inherit from this Base. This avoids circular imports by creating
# a single, dependency-free source for the declarative base.
class Base(DeclarativeBase):
    """Declarative base class for all SQLAlchemy models using SQLAlchemy 2.0 patterns."""
    pass