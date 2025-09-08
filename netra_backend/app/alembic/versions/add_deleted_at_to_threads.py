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
    # Use try/except for both online and offline mode compatibility
    try:
        # This works for online mode - check if column exists
        conn = op.get_bind()
        if hasattr(conn, 'dialect') and not hasattr(conn, 'mock'):  # Not in offline mode
            inspector = sa.inspect(conn)
            columns = [col['name'] for col in inspector.get_columns('threads')]
            if 'deleted_at' in columns:
                return  # Column already exists
    except Exception:
        # In offline mode or if table doesn't exist, just add the column
        pass
    
    # Add deleted_at column (safe to run multiple times in production)
    op.add_column('threads', 
        sa.Column('deleted_at', sa.DateTime(), nullable=True)
    )


def downgrade() -> None:
    """Remove deleted_at column from threads table."""
    op.drop_column('threads', 'deleted_at')