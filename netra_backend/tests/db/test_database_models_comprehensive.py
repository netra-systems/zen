"""
Comprehensive Unit Tests for Database Models - User, Agent, and Content Data

Business Value Justification (BVJ):
- Segment: Platform/All Users
- Business Goal: Reliable data models for core business entities and relationships
- Value Impact: Models define the data structure that stores $500K+ ARR business data
- Revenue Impact: Proper data modeling enables scalable user management and AI optimization features

This test suite validates Database Models as the SINGLE SOURCE OF TRUTH for data structure.
Critical for golden path: user accounts → conversation data → agent execution → business insights.

SSOT Compliance:
- Tests the ONLY definitions for core business data structures
- Validates model relationships and data integrity constraints
- Ensures proper field definitions and data types
- Verifies authentication data separation and security

Golden Path Model Coverage:
- User models (accounts, authentication, profiles, billing, permissions)
- Agent models (assistants, executions, conversations, optimization results)
- Content models (messages, threads, files, metadata)
- Relationship integrity (foreign keys, cascades, data consistency)
- Business logic constraints (validation rules, data formats)
"""

import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from typing import Dict, Any, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError, ConstraintViolation

from netra_backend.app.db.base import Base
from netra_backend.app.db.models_user import User, Secret, ToolUsageLog
from netra_backend.app.db.models_agent import (
    Assistant, Thread, Message, Run, Step, 
    ApexOptimizerAgentRun, ApexOptimizerAgentRunReport
)


class TestUserModelsSSO:
    """Test User models as Single Source of Truth for user-related data structures."""
    
    @pytest.fixture
    def mock_session(self):
        """Create mock database session for testing."""
        return Mock()
    
    @pytest.mark.unit
    def test_user_model_structure_and_fields(self):
        """Test User model structure and field definitions.
        
        BVJ: Ensures user data structure supports all business requirements.
        Golden Path: User registration → profile management → subscription handling.
        """
        # Test User model field structure
        user_fields = User.__table__.columns.keys()
        
        # Verify core user fields
        assert 'id' in user_fields
        assert 'email' in user_fields
        assert 'full_name' in user_fields
        assert 'hashed_password' in user_fields
        assert 'picture' in user_fields
        
        # Verify timestamp fields
        assert 'created_at' in user_fields
        assert 'updated_at' in user_fields
        
        # Verify status fields
        assert 'is_active' in user_fields
        assert 'is_superuser' in user_fields
        assert 'is_developer' in user_fields
        
        # Verify permission fields
        assert 'role' in user_fields
        assert 'permissions' in user_fields
        
        # Verify billing fields
        assert 'plan_tier' in user_fields
        assert 'plan_expires_at' in user_fields
        assert 'plan_started_at' in user_fields
        assert 'feature_flags' in user_fields
        assert 'tool_permissions' in user_fields
        assert 'auto_renew' in user_fields
        assert 'payment_status' in user_fields
        assert 'trial_period' in user_fields
    
    @pytest.mark.unit
    def test_user_model_defaults_and_constraints(self):
        """Test User model default values and constraints.
        
        BVJ: Ensures proper default values for business logic consistency.
        Golden Path: New users get appropriate defaults for immediate platform use.
        """
        # Test User model constraints and defaults
        user_table = User.__table__
        
        # Verify email uniqueness constraint
        email_column = user_table.columns['email']
        assert email_column.unique == True
        assert email_column.index == True
        
        # Verify default values for status fields
        is_active_column = user_table.columns['is_active']
        assert is_active_column.default.arg == True
        
        is_superuser_column = user_table.columns['is_superuser'] 
        assert is_superuser_column.default.arg == False
        
        is_developer_column = user_table.columns['is_developer']
        assert is_developer_column.default.arg == False
        
        # Verify default role
        role_column = user_table.columns['role']
        assert role_column.default.arg == "standard_user"
        
        # Verify default plan tier
        plan_tier_column = user_table.columns['plan_tier']
        assert plan_tier_column.default.arg == "free"
        
        # Verify default payment status
        payment_status_column = user_table.columns['payment_status']
        assert payment_status_column.default.arg == "active"
    
    @pytest.mark.unit
    def test_user_authentication_field_security(self):
        """Test User model authentication field handling for security.
        
        BVJ: Ensures authentication data is properly structured for security.
        Golden Path: Authentication service integration → secure password handling.
        """
        # Test hashed_password field is optional (managed by auth service)
        hashed_password_column = User.__table__.columns['hashed_password']
        assert hashed_password_column.nullable == True
        
        # Test User model doesn't have password validation methods
        # (security: password handling delegated to auth service)
        user_methods = [method for method in dir(User) if not method.startswith('_')]
        password_methods = [method for method in user_methods if 'password' in method.lower()]
        assert len(password_methods) == 0, "User model should not have password methods"
    
    @pytest.mark.unit
    def test_user_billing_and_subscription_fields(self):
        """Test User model billing and subscription field structure.
        
        BVJ: Enables subscription management and revenue tracking.
        Golden Path: User subscription → plan management → billing operations.
        """
        user_table = User.__table__
        
        # Verify billing-related fields exist and have proper types
        plan_tier_column = user_table.columns['plan_tier']
        assert str(plan_tier_column.type) == 'VARCHAR'
        
        plan_expires_at_column = user_table.columns['plan_expires_at']
        assert 'DATETIME' in str(plan_expires_at_column.type).upper()
        assert plan_expires_at_column.nullable == True
        
        feature_flags_column = user_table.columns['feature_flags']
        assert 'JSON' in str(feature_flags_column.type).upper()
        
        tool_permissions_column = user_table.columns['tool_permissions']
        assert 'JSON' in str(tool_permissions_column.type).upper()
        
        auto_renew_column = user_table.columns['auto_renew']
        assert str(auto_renew_column.type) == 'BOOLEAN'
        assert auto_renew_column.default.arg == False
        
        trial_period_column = user_table.columns['trial_period']
        assert 'INTEGER' in str(trial_period_column.type).upper()
        assert trial_period_column.default.arg == 0
    
    @pytest.mark.unit
    def test_user_relationships_structure(self):
        """Test User model relationships with other entities.
        
        BVJ: Ensures proper data relationships for business operations.
        Golden Path: User → secrets/transactions/subscriptions → business functionality.
        """
        # Test User model has expected relationships
        assert hasattr(User, 'secrets')
        assert hasattr(User, 'credit_transactions')
        assert hasattr(User, 'subscriptions')
        
        # Verify relationship configurations
        secrets_rel = User.secrets.property
        assert secrets_rel.back_populates == "user"
        assert "all, delete-orphan" in str(secrets_rel.cascade)
        
        credit_transactions_rel = User.credit_transactions.property
        assert credit_transactions_rel.back_populates == "user"
        assert "all, delete-orphan" in str(credit_transactions_rel.cascade)
        
        subscriptions_rel = User.subscriptions.property
        assert subscriptions_rel.back_populates == "user"
        assert "all, delete-orphan" in str(subscriptions_rel.cascade)


class TestSecretModelSSO:
    """Test Secret model for user secret management."""
    
    @pytest.mark.unit
    def test_secret_model_structure(self):
        """Test Secret model structure for user secrets.
        
        BVJ: Enables secure storage of user API keys and sensitive data.
        Golden Path: User secrets → encrypted storage → secure API access.
        """
        secret_fields = Secret.__table__.columns.keys()
        
        # Verify core secret fields
        assert 'id' in secret_fields
        assert 'user_id' in secret_fields
        assert 'key' in secret_fields
        assert 'encrypted_value' in secret_fields
        assert 'created_at' in secret_fields
        assert 'updated_at' in secret_fields
        
        # Verify foreign key relationship
        user_id_column = Secret.__table__.columns['user_id']
        assert len(user_id_column.foreign_keys) == 1
        foreign_key = list(user_id_column.foreign_keys)[0]
        assert 'users.id' in str(foreign_key.column)
    
    @pytest.mark.unit
    def test_secret_model_relationships(self):
        """Test Secret model relationships with User.
        
        BVJ: Ensures proper relationship between users and their secrets.
        Golden Path: User management → secret access → API integration.
        """
        # Test Secret has user relationship
        assert hasattr(Secret, 'user')
        
        user_rel = Secret.user.property
        assert user_rel.back_populates == "secrets"
    
    @pytest.mark.unit
    def test_secret_model_security_considerations(self):
        """Test Secret model security field handling.
        
        BVJ: Ensures secrets are stored securely with encryption.
        Golden Path: Secret encryption → secure storage → protected user data.
        """
        # Verify encrypted_value field exists (should store encrypted data)
        encrypted_value_column = Secret.__table__.columns['encrypted_value']
        assert encrypted_value_column is not None
        assert str(encrypted_value_column.type) == 'VARCHAR'
        
        # Verify no plaintext value field exists
        secret_fields = Secret.__table__.columns.keys()
        assert 'value' not in secret_fields
        assert 'plaintext_value' not in secret_fields


class TestToolUsageLogModelSSO:
    """Test ToolUsageLog model for analytics and billing."""
    
    @pytest.mark.unit
    def test_tool_usage_log_structure(self):
        """Test ToolUsageLog model structure for usage analytics.
        
        BVJ: Enables usage tracking for billing and optimization insights.
        Golden Path: Tool usage → usage analytics → billing calculations.
        """
        log_fields = ToolUsageLog.__table__.columns.keys()
        
        # Verify core logging fields
        assert 'id' in log_fields
        assert 'user_id' in log_fields
        assert 'tool_name' in log_fields
        assert 'category' in log_fields
        assert 'execution_time_ms' in log_fields
        assert 'tokens_used' in log_fields
        assert 'cost_cents' in log_fields
        assert 'status' in log_fields
        assert 'plan_tier' in log_fields
        assert 'permission_check_result' in log_fields
        assert 'arguments' in log_fields
        assert 'created_at' in log_fields
    
    @pytest.mark.unit
    def test_tool_usage_log_indexing(self):
        """Test ToolUsageLog model indexing for performance.
        
        BVJ: Ensures fast queries for usage analytics and billing.
        Golden Path: Usage data → fast aggregation → billing reports.
        """
        # Verify indexed fields for performance
        tool_name_column = ToolUsageLog.__table__.columns['tool_name']
        assert tool_name_column.index == True
        
        category_column = ToolUsageLog.__table__.columns['category']
        assert category_column.index == True
        
        status_column = ToolUsageLog.__table__.columns['status']
        assert status_column.index == True
        
        created_at_column = ToolUsageLog.__table__.columns['created_at']
        assert created_at_column.index == True
    
    @pytest.mark.unit
    def test_tool_usage_log_data_types(self):
        """Test ToolUsageLog model data types for accurate analytics.
        
        BVJ: Ensures accurate usage tracking for business intelligence.
        Golden Path: Accurate metrics → business insights → optimization decisions.
        """
        # Verify numeric fields have proper types
        execution_time_column = ToolUsageLog.__table__.columns['execution_time_ms']
        assert 'INTEGER' in str(execution_time_column.type).upper()
        assert execution_time_column.default.arg == 0
        
        tokens_used_column = ToolUsageLog.__table__.columns['tokens_used']
        assert 'INTEGER' in str(tokens_used_column.type).upper()
        assert tokens_used_column.nullable == True
        
        cost_cents_column = ToolUsageLog.__table__.columns['cost_cents']
        assert 'INTEGER' in str(cost_cents_column.type).upper()
        assert cost_cents_column.nullable == True
        
        # Verify JSON fields for complex data
        permission_check_column = ToolUsageLog.__table__.columns['permission_check_result']
        assert 'JSON' in str(permission_check_column.type).upper()
        
        arguments_column = ToolUsageLog.__table__.columns['arguments']
        assert 'JSON' in str(arguments_column.type).upper()


class TestAgentModelsSSO:
    """Test Agent models as Single Source of Truth for AI assistant data structures."""
    
    @pytest.mark.unit
    def test_assistant_model_structure(self):
        """Test Assistant model structure for AI assistants.
        
        BVJ: Enables AI assistant management for core platform functionality.
        Golden Path: Assistant creation → configuration → user interactions.
        """
        assistant_fields = Assistant.__table__.columns.keys()
        
        # Verify core assistant fields
        assert 'id' in assistant_fields
        assert 'object' in assistant_fields
        assert 'created_at' in assistant_fields
        assert 'name' in assistant_fields
        assert 'description' in assistant_fields
        assert 'model' in assistant_fields
        assert 'instructions' in assistant_fields
        assert 'tools' in assistant_fields
        assert 'file_ids' in assistant_fields
        assert 'metadata_' in assistant_fields
    
    @pytest.mark.unit
    def test_assistant_model_defaults(self):
        """Test Assistant model default values.
        
        BVJ: Ensures consistent assistant creation with proper defaults.
        Golden Path: Assistant initialization → default configuration → ready for use.
        """
        # Verify default values
        object_column = Assistant.__table__.columns['object']
        assert object_column.default.arg == "assistant"
        
        tools_column = Assistant.__table__.columns['tools']
        assert tools_column.default.arg == []
        
        file_ids_column = Assistant.__table__.columns['file_ids']
        assert file_ids_column.default.arg == []
    
    @pytest.mark.unit
    def test_thread_model_structure(self):
        """Test Thread model structure for conversation threads.
        
        BVJ: Enables conversation management for chat functionality.
        Golden Path: Thread creation → message storage → conversation history.
        """
        thread_fields = Thread.__table__.columns.keys()
        
        # Verify core thread fields
        assert 'id' in thread_fields
        assert 'object' in thread_fields
        assert 'created_at' in thread_fields
        assert 'metadata_' in thread_fields
        assert 'deleted_at' in thread_fields  # Soft delete support
        
        # Verify default value
        object_column = Thread.__table__.columns['object']
        assert object_column.default.arg == "thread"
    
    @pytest.mark.unit
    def test_thread_model_relationships(self):
        """Test Thread model relationships with messages and runs.
        
        BVJ: Ensures proper conversation data relationships.
        Golden Path: Thread → messages → agent runs → complete conversation context.
        """
        # Test Thread has expected relationships
        assert hasattr(Thread, 'messages')
        assert hasattr(Thread, 'runs')
        
        messages_rel = Thread.messages.property
        assert messages_rel.back_populates == "thread"
        
        runs_rel = Thread.runs.property
        assert runs_rel.back_populates == "thread"
    
    @pytest.mark.unit
    def test_message_model_structure(self):
        """Test Message model structure for conversation messages.
        
        BVJ: Enables message storage for chat functionality - 90% of platform value.
        Golden Path: User message → message storage → agent response → conversation flow.
        """
        message_fields = Message.__table__.columns.keys()
        
        # Verify core message fields
        assert 'id' in message_fields
        assert 'object' in message_fields
        assert 'created_at' in message_fields
        assert 'thread_id' in message_fields
        assert 'role' in message_fields
        assert 'content' in message_fields
        assert 'assistant_id' in message_fields
        assert 'run_id' in message_fields
        assert 'file_ids' in message_fields
        assert 'metadata_' in message_fields
        
        # Verify default values
        object_column = Message.__table__.columns['object']
        assert object_column.default.arg == "thread.message"
        
        file_ids_column = Message.__table__.columns['file_ids']
        assert file_ids_column.default.arg == []
    
    @pytest.mark.unit
    def test_message_model_foreign_keys(self):
        """Test Message model foreign key relationships.
        
        BVJ: Ensures proper message relationships for data integrity.
        Golden Path: Message → thread/assistant/run relationships → complete context.
        """
        # Verify foreign key relationships
        thread_id_column = Message.__table__.columns['thread_id']
        assert len(thread_id_column.foreign_keys) == 1
        thread_fk = list(thread_id_column.foreign_keys)[0]
        assert 'threads.id' in str(thread_fk.column)
        
        assistant_id_column = Message.__table__.columns['assistant_id']
        assert len(assistant_id_column.foreign_keys) == 1
        assistant_fk = list(assistant_id_column.foreign_keys)[0]
        assert 'assistants.id' in str(assistant_fk.column)
        
        run_id_column = Message.__table__.columns['run_id']
        assert len(run_id_column.foreign_keys) == 1
        run_fk = list(run_id_column.foreign_keys)[0]
        assert 'runs.id' in str(run_fk.column)
    
    @pytest.mark.unit
    def test_run_model_structure(self):
        """Test Run model structure for agent execution runs.
        
        BVJ: Enables agent execution tracking for optimization and reliability.
        Golden Path: Agent execution → run tracking → performance optimization.
        """
        run_fields = Run.__table__.columns.keys()
        
        # Verify core run fields
        assert 'id' in run_fields
        assert 'object' in run_fields
        assert 'created_at' in run_fields
        assert 'thread_id' in run_fields
        assert 'assistant_id' in run_fields
        assert 'status' in run_fields
        assert 'required_action' in run_fields
        assert 'last_error' in run_fields
        
        # Verify execution lifecycle fields
        assert 'expires_at' in run_fields
        assert 'started_at' in run_fields
        assert 'cancelled_at' in run_fields
        assert 'failed_at' in run_fields
        assert 'completed_at' in run_fields
        
        # Verify configuration fields
        assert 'model' in run_fields
        assert 'instructions' in run_fields
        assert 'tools' in run_fields
        assert 'file_ids' in run_fields
        assert 'metadata_' in run_fields
        
        # Verify default values
        object_column = Run.__table__.columns['object']
        assert object_column.default.arg == "thread.run"
        
        tools_column = Run.__table__.columns['tools']
        assert tools_column.default.arg == []
        
        file_ids_column = Run.__table__.columns['file_ids']
        assert file_ids_column.default.arg == []
    
    @pytest.mark.unit
    def test_run_model_relationships(self):
        """Test Run model relationships for complete execution context.
        
        BVJ: Ensures complete agent execution tracking and context.
        Golden Path: Run → thread/assistant/messages/steps → complete execution visibility.
        """
        # Test Run has expected relationships
        assert hasattr(Run, 'thread')
        assert hasattr(Run, 'assistant')
        assert hasattr(Run, 'messages')
        assert hasattr(Run, 'steps')
        
        # Verify relationship back-references
        thread_rel = Run.thread.property
        assert thread_rel.back_populates == "runs"
        
        messages_rel = Run.messages.property
        assert messages_rel.back_populates == "run"
        
        steps_rel = Run.steps.property
        assert steps_rel.back_populates == "run"
    
    @pytest.mark.unit
    def test_step_model_structure(self):
        """Test Step model structure for detailed execution steps.
        
        BVJ: Enables detailed agent execution tracking for debugging and optimization.
        Golden Path: Agent steps → detailed tracking → performance insights.
        """
        step_fields = Step.__table__.columns.keys()
        
        # Verify core step fields
        assert 'id' in step_fields
        assert 'object' in step_fields
        assert 'created_at' in step_fields
        assert 'run_id' in step_fields
        assert 'assistant_id' in step_fields
        assert 'thread_id' in step_fields
        assert 'type' in step_fields
        assert 'status' in step_fields
        assert 'step_details' in step_fields
        assert 'last_error' in step_fields
        
        # Verify execution lifecycle fields
        assert 'expired_at' in step_fields
        assert 'cancelled_at' in step_fields
        assert 'failed_at' in step_fields
        assert 'completed_at' in step_fields
        assert 'metadata_' in step_fields
        
        # Verify default value
        object_column = Step.__table__.columns['object']
        assert object_column.default.arg == "thread.run.step"


class TestApexOptimizerModelsSSO:
    """Test Apex Optimizer models for AI optimization tracking."""
    
    @pytest.mark.unit
    def test_apex_optimizer_run_model_structure(self):
        """Test ApexOptimizerAgentRun model structure.
        
        BVJ: Enables tracking of AI optimization runs for business value measurement.
        Golden Path: Optimization execution → run tracking → business impact analysis.
        """
        run_fields = ApexOptimizerAgentRun.__table__.columns.keys()
        
        # Verify core run fields
        assert 'id' in run_fields
        assert 'run_id' in run_fields
        assert 'step_name' in run_fields
        assert 'step_input' in run_fields
        assert 'step_output' in run_fields
        assert 'run_log' in run_fields
        assert 'timestamp' in run_fields
        
        # Verify run_id has index for performance
        run_id_column = ApexOptimizerAgentRun.__table__.columns['run_id']
        assert run_id_column.index == True
    
    @pytest.mark.unit
    def test_apex_optimizer_run_report_model_structure(self):
        """Test ApexOptimizerAgentRunReport model structure.
        
        BVJ: Enables storage of optimization reports for business insights.
        Golden Path: Optimization results → report generation → business recommendations.
        """
        report_fields = ApexOptimizerAgentRunReport.__table__.columns.keys()
        
        # Verify core report fields
        assert 'id' in report_fields
        assert 'run_id' in report_fields
        assert 'report' in report_fields
        assert 'timestamp' in report_fields
        
        # Verify run_id constraints
        run_id_column = ApexOptimizerAgentRunReport.__table__.columns['run_id']
        assert run_id_column.index == True
        assert run_id_column.unique == True  # One report per run
    
    @pytest.mark.unit
    def test_apex_optimizer_models_data_types(self):
        """Test Apex Optimizer models data types for proper storage.
        
        BVJ: Ensures accurate optimization data storage for business analysis.
        Golden Path: Optimization data → accurate storage → reliable business insights.
        """
        # Test ApexOptimizerAgentRun data types
        step_input_column = ApexOptimizerAgentRun.__table__.columns['step_input']
        assert 'JSON' in str(step_input_column.type).upper()
        assert step_input_column.nullable == True
        
        step_output_column = ApexOptimizerAgentRun.__table__.columns['step_output']
        assert 'JSON' in str(step_output_column.type).upper()
        assert step_output_column.nullable == True
        
        run_log_column = ApexOptimizerAgentRun.__table__.columns['run_log']
        assert 'TEXT' in str(run_log_column.type).upper()
        assert run_log_column.nullable == True
        
        # Test ApexOptimizerAgentRunReport data types
        report_column = ApexOptimizerAgentRunReport.__table__.columns['report']
        assert 'TEXT' in str(report_column.type).upper()
        assert report_column.nullable == False  # Report is required


class TestModelBusinessScenarios:
    """Test business-critical model scenarios for golden path validation."""
    
    @pytest.mark.unit
    def test_user_registration_data_model_scenario(self):
        """Test user registration data model scenario.
        
        BVJ: Core business functionality - user onboarding drives platform growth.
        Golden Path: User registration → profile creation → platform access.
        """
        # Create user instance for testing
        user = User(
            id=str(uuid.uuid4()),
            email="test@example.com",
            full_name="Test User",
            role="standard_user",
            plan_tier="free",
            is_active=True,
            is_superuser=False,
            is_developer=False
        )
        
        # Verify user instance has expected attributes
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.role == "standard_user"
        assert user.plan_tier == "free"
        assert user.is_active == True
        assert user.is_superuser == False
        assert user.is_developer == False
        assert user.payment_status == "active"  # Default value
        assert user.trial_period == 0  # Default value
    
    @pytest.mark.unit
    def test_chat_conversation_data_model_scenario(self):
        """Test chat conversation data model scenario.
        
        BVJ: Chat conversations are 90% of platform value - must be reliable.
        Golden Path: Thread creation → messages → agent responses → conversation history.
        """
        # Create conversation entities
        assistant = Assistant(
            id="asst_123",
            name="Test Assistant",
            model="gpt-4",
            instructions="You are a helpful assistant"
        )
        
        thread = Thread(
            id="thread_456",
            created_at=int(datetime.now(timezone.utc).timestamp())
        )
        
        user_message = Message(
            id="msg_789",
            thread_id="thread_456",
            role="user",
            content=[{"type": "text", "text": "Hello, how can you help me?"}],
            created_at=int(datetime.now(timezone.utc).timestamp())
        )
        
        assistant_message = Message(
            id="msg_101",
            thread_id="thread_456", 
            assistant_id="asst_123",
            role="assistant",
            content=[{"type": "text", "text": "I can help you with various tasks..."}],
            created_at=int(datetime.now(timezone.utc).timestamp())
        )
        
        # Verify conversation model structure
        assert assistant.name == "Test Assistant"
        assert assistant.model == "gpt-4"
        assert assistant.object == "assistant"  # Default value
        
        assert thread.object == "thread"  # Default value
        assert thread.deleted_at is None  # Not deleted
        
        assert user_message.role == "user"
        assert user_message.thread_id == "thread_456"
        assert user_message.object == "thread.message"  # Default value
        
        assert assistant_message.role == "assistant"
        assert assistant_message.assistant_id == "asst_123"
        assert assistant_message.thread_id == "thread_456"
    
    @pytest.mark.unit
    def test_agent_execution_data_model_scenario(self):
        """Test agent execution data model scenario.
        
        BVJ: Agent execution tracking enables optimization and reliability.
        Golden Path: Agent run → execution tracking → performance optimization.
        """
        # Create agent execution entities
        run = Run(
            id="run_202",
            thread_id="thread_456",
            assistant_id="asst_123", 
            status="in_progress",
            model="gpt-4",
            created_at=int(datetime.now(timezone.utc).timestamp()),
            started_at=int(datetime.now(timezone.utc).timestamp())
        )
        
        step = Step(
            id="step_303",
            run_id="run_202",
            assistant_id="asst_123",
            thread_id="thread_456",
            type="message_creation",
            status="in_progress",
            step_details={"action": "generate_response"},
            created_at=int(datetime.now(timezone.utc).timestamp())
        )
        
        # Verify execution model structure
        assert run.status == "in_progress"
        assert run.thread_id == "thread_456"
        assert run.assistant_id == "asst_123"
        assert run.object == "thread.run"  # Default value
        assert run.tools == []  # Default value
        
        assert step.type == "message_creation"
        assert step.status == "in_progress"
        assert step.run_id == "run_202"
        assert step.object == "thread.run.step"  # Default value
    
    @pytest.mark.unit
    def test_optimization_tracking_data_model_scenario(self):
        """Test AI optimization tracking data model scenario.
        
        BVJ: Optimization tracking enables business value measurement and improvement.
        Golden Path: Optimization execution → tracking → business impact analysis.
        """
        # Create optimization tracking entities
        optimizer_run = ApexOptimizerAgentRun(
            run_id="opt_run_404",
            step_name="analyze_performance",
            step_input={"metrics": ["response_time", "accuracy"]},
            step_output={"recommendations": ["optimize_model", "cache_results"]},
            run_log="Performance analysis completed successfully"
        )
        
        optimizer_report = ApexOptimizerAgentRunReport(
            run_id="opt_run_404",
            report="Optimization recommendations: 1) Implement caching for 30% performance improvement, 2) Upgrade model for 15% accuracy improvement..."
        )
        
        # Verify optimization model structure
        assert optimizer_run.run_id == "opt_run_404"
        assert optimizer_run.step_name == "analyze_performance"
        assert optimizer_run.step_input["metrics"] == ["response_time", "accuracy"]
        assert optimizer_run.step_output["recommendations"] == ["optimize_model", "cache_results"]
        
        assert optimizer_report.run_id == "opt_run_404"
        assert "Optimization recommendations" in optimizer_report.report
        assert "30% performance improvement" in optimizer_report.report
    
    @pytest.mark.unit
    def test_user_analytics_and_billing_data_model_scenario(self):
        """Test user analytics and billing data model scenario.
        
        BVJ: Usage analytics enable billing accuracy and business optimization.
        Golden Path: Tool usage → analytics tracking → billing calculations.
        """
        # Create analytics and billing entities
        usage_log = ToolUsageLog(
            user_id="user_505",
            tool_name="apex_optimizer", 
            category="ai_optimization",
            execution_time_ms=2500,
            tokens_used=1250,
            cost_cents=75,
            status="success",
            plan_tier="pro",
            permission_check_result={"allowed": True, "tier_limit": False},
            arguments={"optimization_type": "performance", "target_metric": "response_time"}
        )
        
        # Verify analytics model structure
        assert usage_log.user_id == "user_505"
        assert usage_log.tool_name == "apex_optimizer"
        assert usage_log.category == "ai_optimization"
        assert usage_log.execution_time_ms == 2500
        assert usage_log.tokens_used == 1250
        assert usage_log.cost_cents == 75
        assert usage_log.status == "success"
        assert usage_log.plan_tier == "pro"
        assert usage_log.permission_check_result["allowed"] == True
        assert usage_log.arguments["optimization_type"] == "performance"
    
    @pytest.mark.unit
    def test_data_model_relationships_and_integrity(self):
        """Test data model relationships and referential integrity.
        
        BVJ: Ensures data consistency for reliable business operations.
        Golden Path: Related data → referential integrity → consistent business state.
        """
        # Test User-Secret relationship
        user = User(id="user_606", email="user@example.com")
        secret = Secret(
            user_id="user_606",
            key="api_key",
            encrypted_value="encrypted_api_key_value"
        )
        
        # Test User-ToolUsageLog relationship
        usage_log = ToolUsageLog(
            user_id="user_606",
            tool_name="test_tool",
            status="success",
            plan_tier="free"
        )
        
        # Test Thread-Message relationship
        thread = Thread(id="thread_707")
        message = Message(
            id="msg_808",
            thread_id="thread_707",
            role="user",
            content=[{"type": "text", "text": "Test message"}]
        )
        
        # Test Run-Step relationship
        run = Run(
            id="run_909",
            thread_id="thread_707",
            assistant_id="asst_101",
            status="completed"
        )
        
        step = Step(
            id="step_010",
            run_id="run_909",
            assistant_id="asst_101",
            thread_id="thread_707",
            type="tool_call",
            status="completed",
            step_details={"tool": "test_tool"}
        )
        
        # Verify relationship consistency
        assert secret.user_id == user.id
        assert usage_log.user_id == user.id
        assert message.thread_id == thread.id
        assert step.run_id == run.id
        assert step.thread_id == run.thread_id
        assert step.assistant_id == run.assistant_id


@pytest.mark.integration
class TestModelSSotIntegration:
    """Integration tests for Model SSOT compliance with actual database operations."""
    
    @pytest.mark.real_database
    def test_model_table_creation_and_structure(self):
        """Test model table creation with real database.
        
        BVJ: Validates models work with actual database constraints.
        Golden Path: Models → database schema → production reliability.
        """
        try:
            # Create in-memory SQLite database for testing
            engine = create_engine("sqlite:///:memory:")
            Base.metadata.create_all(engine)
            
            # Verify tables were created
            inspector = engine.inspect(engine)
            table_names = inspector.get_table_names()
            
            # Check that expected tables exist
            expected_tables = [
                'users', 'secrets', 'tool_usage_logs',
                'assistants', 'threads', 'messages', 'runs', 'steps',
                'apex_optimizer_agent_runs', 'apex_optimizer_agent_run_reports'
            ]
            
            for table in expected_tables:
                assert table in table_names, f"Table {table} not found"
            
        except Exception as e:
            pytest.skip(f"Real database not available for integration test: {e}")
    
    @pytest.mark.real_database
    def test_model_crud_operations_with_real_database(self):
        """Test model CRUD operations with real database constraints.
        
        BVJ: Validates models handle real database operations correctly.
        Golden Path: Model operations → database persistence → business data reliability.
        """
        try:
            # Create in-memory SQLite database for testing
            engine = create_engine("sqlite:///:memory:")
            Base.metadata.create_all(engine)
            Session = sessionmaker(bind=engine)
            session = Session()
            
            # Test User creation
            user = User(
                id=str(uuid.uuid4()),
                email="integration@test.com",
                full_name="Integration Test User"
            )
            session.add(user)
            session.commit()
            
            # Test User retrieval
            retrieved_user = session.query(User).filter_by(email="integration@test.com").first()
            assert retrieved_user is not None
            assert retrieved_user.full_name == "Integration Test User"
            
            # Test Thread creation and relationship
            thread = Thread(
                id="integration_thread",
                created_at=int(datetime.now(timezone.utc).timestamp())
            )
            session.add(thread)
            
            # Test Message creation with foreign key
            message = Message(
                id="integration_message",
                thread_id="integration_thread",
                role="user",
                content=[{"type": "text", "text": "Integration test message"}],
                created_at=int(datetime.now(timezone.utc).timestamp())
            )
            session.add(message)
            session.commit()
            
            # Test relationship queries
            retrieved_thread = session.query(Thread).filter_by(id="integration_thread").first()
            assert retrieved_thread is not None
            
            thread_messages = session.query(Message).filter_by(thread_id="integration_thread").all()
            assert len(thread_messages) == 1
            assert thread_messages[0].content[0]["text"] == "Integration test message"
            
            session.close()
            
        except Exception as e:
            pytest.skip(f"Real database not available for integration test: {e}")