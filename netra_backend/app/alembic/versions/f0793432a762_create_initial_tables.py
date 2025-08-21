"""create initial tables - Main Migration Module

Revision ID: f0793432a762
Revises: 29d08736f8b7
Create Date: 2025-08-09 08:45:22.040879

Re-exports migration functions from focused modules for Alembic compatibility.
"""

# Import metadata and functions from focused modules
from netra_backend.app.alembic.migrations_helpers.downgrade_workflow import downgrade
from netra_backend.app.alembic.migrations_helpers.migration_metadata import (
    branch_labels,
    depends_on,
    down_revision,
    revision,
)
from netra_backend.app.alembic.migrations_helpers.upgrade_workflow import upgrade

# Re-export for Alembic compatibility
__all__ = ['revision', 'down_revision', 'branch_labels', 'depends_on', 'upgrade', 'downgrade']