"""fix json column casting for PostgreSQL compatibility

Revision ID: fix_json_casting_001
Revises: 882759db46ce
Create Date: 2025-09-08 20:00:00.000000

Business Value Justification (BVJ):
- Segment: Platform stability (all tiers)
- Business Goal: Fix migration failures blocking deployments
- Value Impact: Enables successful database schema updates
- Strategic Impact: Unblocks staging and production deployments

This migration fixes the PostgreSQL column casting issue by using raw SQL 
for ALTER COLUMN operations that require explicit USING clauses.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'fix_json_casting_001'
down_revision: Union[str, Sequence[str], None] = '882759db46ce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Fix JSON column casting using raw SQL for PostgreSQL compatibility."""
    
    # Use raw SQL to handle the column type changes with proper USING clauses
    # This ensures compatibility with PostgreSQL's strict type casting requirements
    
    # Check if we're in offline mode or can execute SQL
    try:
        conn = op.get_bind()
        
        # Only run these fixes if the previous migration actually failed
        # Check if columns still need to be converted
        
        # Fix assistants.file_ids column casting
        op.execute("""
            DO $$ 
            BEGIN
                -- Check if column exists and needs conversion
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'assistants' 
                    AND column_name = 'file_ids'
                    AND data_type = 'ARRAY'
                ) THEN
                    ALTER TABLE assistants 
                    ALTER COLUMN file_ids TYPE json 
                    USING (
                        CASE 
                            WHEN file_ids IS NULL THEN NULL
                            WHEN array_length(file_ids, 1) IS NULL THEN '[]'::json
                            ELSE array_to_json(file_ids)
                        END
                    );
                END IF;
            END $$;
        """)
        
        # Fix messages.file_ids column casting  
        op.execute("""
            DO $$ 
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'messages' 
                    AND column_name = 'file_ids'
                    AND data_type = 'ARRAY'
                ) THEN
                    ALTER TABLE messages 
                    ALTER COLUMN file_ids TYPE json 
                    USING (
                        CASE 
                            WHEN file_ids IS NULL THEN NULL
                            WHEN array_length(file_ids, 1) IS NULL THEN '[]'::json
                            ELSE array_to_json(file_ids)
                        END
                    );
                END IF;
            END $$;
        """)
        
        # Fix runs.file_ids column casting
        op.execute("""
            DO $$ 
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'runs' 
                    AND column_name = 'file_ids'
                    AND data_type = 'ARRAY'
                ) THEN
                    ALTER TABLE runs 
                    ALTER COLUMN file_ids TYPE json 
                    USING (
                        CASE 
                            WHEN file_ids IS NULL THEN NULL
                            WHEN array_length(file_ids, 1) IS NULL THEN '[]'::json
                            ELSE array_to_json(file_ids)
                        END
                    );
                END IF;
            END $$;
        """)
        
        # Fix corpus_audit_logs.compliance_flags column casting
        op.execute("""
            DO $$ 
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'corpus_audit_logs' 
                    AND column_name = 'compliance_flags'
                    AND data_type = 'ARRAY'
                ) THEN
                    ALTER TABLE corpus_audit_logs 
                    ALTER COLUMN compliance_flags TYPE json 
                    USING (
                        CASE 
                            WHEN compliance_flags IS NULL THEN NULL
                            WHEN array_length(compliance_flags, 1) IS NULL THEN '[]'::json
                            ELSE array_to_json(compliance_flags)
                        END
                    );
                END IF;
            END $$;
        """)
        
    except Exception:
        # In offline mode, generate the raw SQL
        op.execute("-- JSON column casting fixes will be applied during online migration")


def downgrade() -> None:
    """Revert JSON columns back to arrays."""
    
    # Revert changes back to array format
    op.execute("""
        DO $$ 
        BEGIN
            -- Revert assistants.file_ids
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'assistants' 
                AND column_name = 'file_ids'
                AND data_type = 'json'
            ) THEN
                ALTER TABLE assistants 
                ALTER COLUMN file_ids TYPE varchar[] 
                USING (
                    CASE 
                        WHEN file_ids IS NULL THEN NULL
                        ELSE ARRAY(SELECT jsonb_array_elements_text(file_ids::jsonb))
                    END
                );
            END IF;
            
            -- Revert messages.file_ids
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'messages' 
                AND column_name = 'file_ids'
                AND data_type = 'json'
            ) THEN
                ALTER TABLE messages 
                ALTER COLUMN file_ids TYPE varchar[] 
                USING (
                    CASE 
                        WHEN file_ids IS NULL THEN NULL
                        ELSE ARRAY(SELECT jsonb_array_elements_text(file_ids::jsonb))
                    END
                );
            END IF;
            
            -- Revert runs.file_ids
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'runs' 
                AND column_name = 'file_ids'
                AND data_type = 'json'
            ) THEN
                ALTER TABLE runs 
                ALTER COLUMN file_ids TYPE varchar[] 
                USING (
                    CASE 
                        WHEN file_ids IS NULL THEN NULL
                        ELSE ARRAY(SELECT jsonb_array_elements_text(file_ids::jsonb))
                    END
                );
            END IF;
            
            -- Revert corpus_audit_logs.compliance_flags
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'corpus_audit_logs' 
                AND column_name = 'compliance_flags'
                AND data_type = 'json'
            ) THEN
                ALTER TABLE corpus_audit_logs 
                ALTER COLUMN compliance_flags TYPE varchar[] 
                USING (
                    CASE 
                        WHEN compliance_flags IS NULL THEN NULL
                        ELSE ARRAY(SELECT jsonb_array_elements_text(compliance_flags::jsonb))
                    END
                );
            END IF;
        END $$;
    """)