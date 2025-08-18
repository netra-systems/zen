"""Add demo tables for enterprise demonstrations

Revision ID: demo_tables_001
Revises: 
Create Date: 2025-01-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'demo_tables_001'
down_revision = None
branch_labels = None
depends_on = None


def _create_demo_sessions_table() -> None:
    """Create demo_sessions table with all columns and constraints."""
    op.create_table(
        'demo_sessions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('industry', sa.String(50), nullable=False),
        sa.Column('company_name', sa.String(255), nullable=True),
        sa.Column('company_size', sa.String(50), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'))

def _add_demo_sessions_progress_columns() -> None:
    """Add progress and timestamp columns to demo_sessions."""
    op.add_column('demo_sessions', 
                  sa.Column('progress_percentage', sa.Float(), nullable=False, server_default='0'))
    op.add_column('demo_sessions', 
                  sa.Column('started_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.add_column('demo_sessions', 
                  sa.Column('completed_at', sa.DateTime(), nullable=True))
    op.add_column('demo_sessions', 
                  sa.Column('metadata', postgresql.JSONB(), nullable=True))

def _add_demo_sessions_audit_columns() -> None:
    """Add audit columns to demo_sessions."""
    op.add_column('demo_sessions', 
                  sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.add_column('demo_sessions', 
                  sa.Column('updated_at', sa.DateTime(), nullable=False, 
                           server_default=sa.func.now(), onupdate=sa.func.now()))

def _create_demo_sessions_constraints() -> None:
    """Create foreign keys and indexes for demo_sessions."""
    op.create_foreign_key(None, 'demo_sessions', 'userbase', ['user_id'], ['id'], ondelete='SET NULL')
    op.create_index('idx_demo_sessions_user_id', 'demo_sessions', ['user_id'])
    op.create_index('idx_demo_sessions_industry', 'demo_sessions', ['industry'])
    op.create_index('idx_demo_sessions_status', 'demo_sessions', ['status'])
    op.create_index('idx_demo_sessions_started_at', 'demo_sessions', ['started_at'])

def _create_demo_interactions_table() -> None:
    """Create demo_interactions table with basic columns."""
    op.create_table(
        'demo_interactions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('session_id', sa.String(36), nullable=False),
        sa.Column('interaction_type', sa.String(50), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('response', sa.Text(), nullable=True))

def _add_demo_interactions_detail_columns() -> None:
    """Add detail columns to demo_interactions."""
    op.add_column('demo_interactions', 
                  sa.Column('agents_involved', postgresql.ARRAY(sa.String()), nullable=True))
    op.add_column('demo_interactions', 
                  sa.Column('metrics', postgresql.JSONB(), nullable=True))
    op.add_column('demo_interactions', 
                  sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.add_column('demo_interactions', 
                  sa.Column('duration_ms', sa.Integer(), nullable=True))

def _create_demo_interactions_constraints() -> None:
    """Create constraints and indexes for demo_interactions."""
    op.create_foreign_key(None, 'demo_interactions', 'demo_sessions', ['session_id'], ['id'], ondelete='CASCADE')
    op.create_index('idx_demo_interactions_session_id', 'demo_interactions', ['session_id'])
    op.create_index('idx_demo_interactions_type', 'demo_interactions', ['interaction_type'])
    op.create_index('idx_demo_interactions_timestamp', 'demo_interactions', ['timestamp'])

def _create_demo_scenarios_table() -> None:
    """Create demo_scenarios table with basic columns."""
    op.create_table(
        'demo_scenarios',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('industry', sa.String(50), nullable=False),
        sa.Column('scenario_name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('prompt_template', sa.Text(), nullable=False))

def _add_demo_scenarios_config_columns() -> None:
    """Add configuration columns to demo_scenarios."""
    op.add_column('demo_scenarios', 
                  sa.Column('optimization_scenarios', postgresql.JSONB(), nullable=True))
    op.add_column('demo_scenarios', 
                  sa.Column('typical_metrics', postgresql.JSONB(), nullable=True))
    op.add_column('demo_scenarios', 
                  sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))

def _add_demo_scenarios_audit_columns() -> None:
    """Add audit columns to demo_scenarios."""
    op.add_column('demo_scenarios', 
                  sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.add_column('demo_scenarios', 
                  sa.Column('updated_at', sa.DateTime(), nullable=False, 
                           server_default=sa.func.now(), onupdate=sa.func.now()))

def _create_demo_scenarios_constraints() -> None:
    """Create constraints and indexes for demo_scenarios."""
    op.create_unique_constraint('uq_demo_scenarios_industry_name', 'demo_scenarios', 
                               ['industry', 'scenario_name'])
    op.create_index('idx_demo_scenarios_industry', 'demo_scenarios', ['industry'])
    op.create_index('idx_demo_scenarios_active', 'demo_scenarios', ['is_active'])

def _create_demo_metrics_table() -> None:
    """Create demo_metrics table with metric columns."""
    op.create_table(
        'demo_metrics',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('session_id', sa.String(36), nullable=False),
        sa.Column('metric_type', sa.String(50), nullable=False),
        sa.Column('baseline_value', sa.Float(), nullable=False),
        sa.Column('optimized_value', sa.Float(), nullable=False))

def _add_demo_metrics_analysis_columns() -> None:
    """Add analysis columns to demo_metrics."""
    op.add_column('demo_metrics', 
                  sa.Column('improvement_percentage', sa.Float(), nullable=False))
    op.add_column('demo_metrics', 
                  sa.Column('confidence_score', sa.Float(), nullable=True))
    op.add_column('demo_metrics', 
                  sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.func.now()))

def _create_demo_metrics_constraints() -> None:
    """Create constraints and indexes for demo_metrics."""
    op.create_foreign_key(None, 'demo_metrics', 'demo_sessions', ['session_id'], ['id'], ondelete='CASCADE')
    op.create_index('idx_demo_metrics_session_id', 'demo_metrics', ['session_id'])
    op.create_index('idx_demo_metrics_type', 'demo_metrics', ['metric_type'])
    op.create_index('idx_demo_metrics_timestamp', 'demo_metrics', ['timestamp'])

def _create_demo_exports_table() -> None:
    """Create demo_exports table with basic columns."""
    op.create_table(
        'demo_exports',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('session_id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('export_format', sa.String(20), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=True))

def _add_demo_exports_detail_columns() -> None:
    """Add detail columns to demo_exports."""
    op.add_column('demo_exports', 
                  sa.Column('file_url', sa.String(500), nullable=True))
    op.add_column('demo_exports', 
                  sa.Column('sections_included', postgresql.ARRAY(sa.String()), nullable=True))
    op.add_column('demo_exports', 
                  sa.Column('status', sa.String(20), nullable=False, server_default='pending'))

def _add_demo_exports_timestamp_columns() -> None:
    """Add timestamp columns to demo_exports."""
    op.add_column('demo_exports', 
                  sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.add_column('demo_exports', 
                  sa.Column('expires_at', sa.DateTime(), nullable=True))

def _create_demo_exports_constraints() -> None:
    """Create constraints and indexes for demo_exports."""
    op.create_foreign_key(None, 'demo_exports', 'demo_sessions', ['session_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'demo_exports', 'userbase', ['user_id'], ['id'], ondelete='SET NULL')
    op.create_index('idx_demo_exports_session_id', 'demo_exports', ['session_id'])
    op.create_index('idx_demo_exports_user_id', 'demo_exports', ['user_id'])
    op.create_index('idx_demo_exports_status', 'demo_exports', ['status'])
    op.create_index('idx_demo_exports_created_at', 'demo_exports', ['created_at'])

def _create_demo_feedback_table() -> None:
    """Create demo_feedback table with basic columns."""
    op.create_table(
        'demo_feedback',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('session_id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('feedback_text', sa.Text(), nullable=True))

def _add_demo_feedback_detail_columns() -> None:
    """Add detail columns to demo_feedback."""
    op.add_column('demo_feedback', 
                  sa.Column('would_recommend', sa.Boolean(), nullable=True))
    op.add_column('demo_feedback', 
                  sa.Column('conversion_intent', sa.String(50), nullable=True))
    op.add_column('demo_feedback', 
                  sa.Column('metadata', postgresql.JSONB(), nullable=True))
    op.add_column('demo_feedback', 
                  sa.Column('submitted_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))

def _create_demo_feedback_constraints() -> None:
    """Create constraints and indexes for demo_feedback."""
    op.create_foreign_key(None, 'demo_feedback', 'demo_sessions', ['session_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'demo_feedback', 'userbase', ['user_id'], ['id'], ondelete='SET NULL')
    op.create_index('idx_demo_feedback_session_id', 'demo_feedback', ['session_id'])
    op.create_index('idx_demo_feedback_user_id', 'demo_feedback', ['user_id'])
    op.create_index('idx_demo_feedback_rating', 'demo_feedback', ['rating'])
    op.create_index('idx_demo_feedback_submitted_at', 'demo_feedback', ['submitted_at'])

def _insert_financial_scenarios() -> None:
    """Insert financial industry demo scenarios."""
    op.execute("""
        INSERT INTO demo_scenarios (industry, scenario_name, description, prompt_template, optimization_scenarios, typical_metrics)
        VALUES 
        ('financial', 'fraud_detection', 'AI-powered fraud detection optimization', 
         'Analyze fraud detection workloads for financial services...', 
         '{"strategies": ["Model Selection", "Caching", "Batch Processing"]}',
         '{"baseline": {"latency_ms": 300, "accuracy": 0.85}, "optimized": {"latency_ms": 100, "accuracy": 0.92}}')
    """)

def _insert_healthcare_scenarios() -> None:
    """Insert healthcare industry demo scenarios."""
    op.execute("""
        INSERT INTO demo_scenarios (industry, scenario_name, description, prompt_template, optimization_scenarios, typical_metrics)
        VALUES
        ('healthcare', 'diagnostic_ai', 'Medical diagnostic AI optimization',
         'Optimize diagnostic AI workloads for healthcare...',
         '{"strategies": ["Accuracy Enhancement", "Compliance", "Speed Optimization"]}',
         '{"baseline": {"latency_ms": 500, "accuracy": 0.88}, "optimized": {"latency_ms": 200, "accuracy": 0.95}}')
    """)

def _insert_ecommerce_scenarios() -> None:
    """Insert ecommerce industry demo scenarios."""
    op.execute("""
        INSERT INTO demo_scenarios (industry, scenario_name, description, prompt_template, optimization_scenarios, typical_metrics)
        VALUES
        ('ecommerce', 'recommendation_engine', 'Product recommendation optimization',
         'Enhance recommendation engine performance for e-commerce...',
         '{"strategies": ["Personalization", "Real-time Processing", "Cost Reduction"]}',
         '{"baseline": {"latency_ms": 200, "conversion": 0.02}, "optimized": {"latency_ms": 50, "conversion": 0.035}}')
    """)

def _insert_manufacturing_scenarios() -> None:
    """Insert manufacturing industry demo scenarios."""
    op.execute("""
        INSERT INTO demo_scenarios (industry, scenario_name, description, prompt_template, optimization_scenarios, typical_metrics)
        VALUES
        ('manufacturing', 'predictive_maintenance', 'Predictive maintenance AI optimization',
         'Optimize predictive maintenance models for manufacturing...',
         '{"strategies": ["Anomaly Detection", "Resource Optimization", "Downtime Prevention"]}',
         '{"baseline": {"prediction_accuracy": 0.75, "false_positives": 0.15}, "optimized": {"prediction_accuracy": 0.90, "false_positives": 0.05}}')
    """)

def _insert_technology_scenarios() -> None:
    """Insert technology industry demo scenarios."""
    op.execute("""
        INSERT INTO demo_scenarios (industry, scenario_name, description, prompt_template, optimization_scenarios, typical_metrics)
        VALUES
        ('technology', 'code_generation', 'AI code generation optimization',
         'Optimize code generation and development assistance...',
         '{"strategies": ["Model Routing", "Context Management", "Output Quality"]}',
         '{"baseline": {"generation_time": 5000, "quality_score": 0.80}, "optimized": {"generation_time": 1500, "quality_score": 0.92}}')
    """)

def upgrade() -> None:
    """Create demo-related tables."""
    _create_demo_sessions_table()
    _add_demo_sessions_progress_columns()
    _add_demo_sessions_audit_columns()
    _create_demo_sessions_constraints()
    _create_demo_interactions_table()
    _add_demo_interactions_detail_columns()
    _create_demo_interactions_constraints()
    _create_demo_scenarios_table()
    _add_demo_scenarios_config_columns()
    _add_demo_scenarios_audit_columns()
    _create_demo_scenarios_constraints()
    _create_demo_metrics_table()
    _add_demo_metrics_analysis_columns()
    _create_demo_metrics_constraints()
    _create_demo_exports_table()
    _add_demo_exports_detail_columns()
    _add_demo_exports_timestamp_columns()
    _create_demo_exports_constraints()
    _create_demo_feedback_table()
    _add_demo_feedback_detail_columns()
    _create_demo_feedback_constraints()
    _insert_financial_scenarios()
    _insert_healthcare_scenarios()
    _insert_ecommerce_scenarios()
    _insert_manufacturing_scenarios()
    _insert_technology_scenarios()


def downgrade() -> None:
    """Drop demo-related tables."""
    op.drop_table('demo_feedback')
    op.drop_table('demo_exports')
    op.drop_table('demo_metrics')
    op.drop_table('demo_scenarios')
    op.drop_table('demo_interactions')
    op.drop_table('demo_sessions')