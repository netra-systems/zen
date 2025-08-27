"""add deleted_at column to threads table

Revision ID: add_deleted_at_001
Revises: 66e0e5d9662d
Create Date: 2025-08-27 10:00:00.000000

Business Value Justification (BVJ):
- Segment: Platform stability (all tiers)
- Business Goal: Enable soft delete functionality for threads
- Value Impact: Maintains data integrity and audit trail
- Strategic Impact: Supports data recovery and compliance requirements
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'add_deleted_at_001'
down_revision: Union[str, Sequence[str], None] = '66e0e5d9662d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add deleted_at column to threads table."""
    # Check if column already exists before adding
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Get columns for threads table
    columns = []
    try:
        columns = [col['name'] for col in inspector.get_columns('threads')]
    except Exception:
        # Table might not exist
        pass
    
    # Add deleted_at column if it doesn't exist
    if 'deleted_at' not in columns:
        op.add_column('threads', 
            sa.Column('deleted_at', sa.DateTime(), nullable=True)
        )


def downgrade() -> None:
    """Remove deleted_at column from threads table."""
    op.drop_column('threads', 'deleted_at')