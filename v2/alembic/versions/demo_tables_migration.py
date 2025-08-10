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


def upgrade() -> None:
    """Create demo-related tables."""
    
    # Create demo_sessions table
    op.create_table(
        'demo_sessions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('industry', sa.String(50), nullable=False),
        sa.Column('company_name', sa.String(255), nullable=True),
        sa.Column('company_size', sa.String(50), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('progress_percentage', sa.Float(), nullable=False, server_default='0'),
        sa.Column('started_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['userbase.id'], ondelete='SET NULL'),
        sa.Index('idx_demo_sessions_user_id', 'user_id'),
        sa.Index('idx_demo_sessions_industry', 'industry'),
        sa.Index('idx_demo_sessions_status', 'status'),
        sa.Index('idx_demo_sessions_started_at', 'started_at'),
    )
    
    # Create demo_interactions table
    op.create_table(
        'demo_interactions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('session_id', sa.String(36), nullable=False),
        sa.Column('interaction_type', sa.String(50), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('response', sa.Text(), nullable=True),
        sa.Column('agents_involved', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('metrics', postgresql.JSONB(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['demo_sessions.id'], ondelete='CASCADE'),
        sa.Index('idx_demo_interactions_session_id', 'session_id'),
        sa.Index('idx_demo_interactions_type', 'interaction_type'),
        sa.Index('idx_demo_interactions_timestamp', 'timestamp'),
    )
    
    # Create demo_scenarios table
    op.create_table(
        'demo_scenarios',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('industry', sa.String(50), nullable=False),
        sa.Column('scenario_name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('prompt_template', sa.Text(), nullable=False),
        sa.Column('optimization_scenarios', postgresql.JSONB(), nullable=True),
        sa.Column('typical_metrics', postgresql.JSONB(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('industry', 'scenario_name', name='uq_demo_scenarios_industry_name'),
        sa.Index('idx_demo_scenarios_industry', 'industry'),
        sa.Index('idx_demo_scenarios_active', 'is_active'),
    )
    
    # Create demo_metrics table
    op.create_table(
        'demo_metrics',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('session_id', sa.String(36), nullable=False),
        sa.Column('metric_type', sa.String(50), nullable=False),
        sa.Column('baseline_value', sa.Float(), nullable=False),
        sa.Column('optimized_value', sa.Float(), nullable=False),
        sa.Column('improvement_percentage', sa.Float(), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['session_id'], ['demo_sessions.id'], ondelete='CASCADE'),
        sa.Index('idx_demo_metrics_session_id', 'session_id'),
        sa.Index('idx_demo_metrics_type', 'metric_type'),
        sa.Index('idx_demo_metrics_timestamp', 'timestamp'),
    )
    
    # Create demo_exports table
    op.create_table(
        'demo_exports',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('session_id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('export_format', sa.String(20), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=True),
        sa.Column('file_url', sa.String(500), nullable=True),
        sa.Column('sections_included', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['demo_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['userbase.id'], ondelete='SET NULL'),
        sa.Index('idx_demo_exports_session_id', 'session_id'),
        sa.Index('idx_demo_exports_user_id', 'user_id'),
        sa.Index('idx_demo_exports_status', 'status'),
        sa.Index('idx_demo_exports_created_at', 'created_at'),
    )
    
    # Create demo_feedback table
    op.create_table(
        'demo_feedback',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('session_id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('feedback_text', sa.Text(), nullable=True),
        sa.Column('would_recommend', sa.Boolean(), nullable=True),
        sa.Column('conversion_intent', sa.String(50), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['session_id'], ['demo_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['userbase.id'], ondelete='SET NULL'),
        sa.Index('idx_demo_feedback_session_id', 'session_id'),
        sa.Index('idx_demo_feedback_user_id', 'user_id'),
        sa.Index('idx_demo_feedback_rating', 'rating'),
        sa.Index('idx_demo_feedback_submitted_at', 'submitted_at'),
    )
    
    # Insert default demo scenarios
    op.execute("""
        INSERT INTO demo_scenarios (industry, scenario_name, description, prompt_template, optimization_scenarios, typical_metrics)
        VALUES 
        ('financial', 'fraud_detection', 'AI-powered fraud detection optimization', 
         'Analyze fraud detection workloads for financial services...', 
         '{"strategies": ["Model Selection", "Caching", "Batch Processing"]}',
         '{"baseline": {"latency_ms": 300, "accuracy": 0.85}, "optimized": {"latency_ms": 100, "accuracy": 0.92}}'),
        
        ('healthcare', 'diagnostic_ai', 'Medical diagnostic AI optimization',
         'Optimize diagnostic AI workloads for healthcare...',
         '{"strategies": ["Accuracy Enhancement", "Compliance", "Speed Optimization"]}',
         '{"baseline": {"latency_ms": 500, "accuracy": 0.88}, "optimized": {"latency_ms": 200, "accuracy": 0.95}}'),
        
        ('ecommerce', 'recommendation_engine', 'Product recommendation optimization',
         'Enhance recommendation engine performance for e-commerce...',
         '{"strategies": ["Personalization", "Real-time Processing", "Cost Reduction"]}',
         '{"baseline": {"latency_ms": 200, "conversion": 0.02}, "optimized": {"latency_ms": 50, "conversion": 0.035}}'),
        
        ('manufacturing', 'predictive_maintenance', 'Predictive maintenance AI optimization',
         'Optimize predictive maintenance models for manufacturing...',
         '{"strategies": ["Anomaly Detection", "Resource Optimization", "Downtime Prevention"]}',
         '{"baseline": {"prediction_accuracy": 0.75, "false_positives": 0.15}, "optimized": {"prediction_accuracy": 0.90, "false_positives": 0.05}}'),
        
        ('technology', 'code_generation', 'AI code generation optimization',
         'Optimize code generation and development assistance...',
         '{"strategies": ["Model Routing", "Context Management", "Output Quality"]}',
         '{"baseline": {"generation_time": 5000, "quality_score": 0.80}, "optimized": {"generation_time": 1500, "quality_score": 0.92}}')
    """)


def downgrade() -> None:
    """Drop demo-related tables."""
    op.drop_table('demo_feedback')
    op.drop_table('demo_exports')
    op.drop_table('demo_metrics')
    op.drop_table('demo_scenarios')
    op.drop_table('demo_interactions')
    op.drop_table('demo_sessions')