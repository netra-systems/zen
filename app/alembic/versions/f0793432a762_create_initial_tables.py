"""create initial tables - Main Migration Module

Revision ID: f0793432a762
Revises: 29d08736f8b7
Create Date: 2025-08-09 08:45:22.040879

Re-exports migration functions from focused modules for Alembic compatibility.
"""

# Import metadata and functions from focused modules
from .migration_metadata import (
    revision, down_revision, branch_labels, depends_on
)
from .upgrade_workflow import upgrade
from .downgrade_workflow import downgrade

# Re-export for Alembic compatibility
__all__ = ['revision', 'down_revision', 'branch_labels', 'depends_on', 'upgrade', 'downgrade']