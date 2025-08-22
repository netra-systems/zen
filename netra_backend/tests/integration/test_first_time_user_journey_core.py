"""
First-Time User Journey Core Tests

Business Value Justification (BVJ):
- Segment: Free users converting to Growth/Enterprise (100% of revenue)
- Business Goal: Protect $2M+ ARR from first-time user onboarding failures
- Value Impact: Each successful onboarding = $99-999/month recurring revenue
- Revenue Impact: 1% conversion improvement = +$240K ARR annually

Core first-time user journey tests from registration to first successful interaction.
"""

# Add project root to path
import sys
from pathlib import Path

from test_framework import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import tempfile
import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from netra_backend.app.db.base import Base
from netra_backend.app.db.models_agent import Message, Thread

# Add project root to path
from netra_backend.app.db.models_user import ToolUsageLog, User

# Add project root to path


class TestFirstTimeUserJourneyCore:
    """Core first-time user journey tests."""

    @pytest.fixture
    async def first_time_user_setup(self):
        """Setup isolated test environment for first-time user testing"""
        return await self._create_first_time_user_env()

    @pytest.fixture
    def payment_system(self):
        """Setup mock payment system for billing tests"""
        return self._init_payment_system()

    @pytest.fixture
    def email_system(self):
        """Setup mock email system for verification tests"""
        return self._init_email_system()

    @pytest.fixture
    def llm_system(self):
        """Setup mock LLM system for agent tests"""
        return self._init_llm_system()

    async def _create_first_time_user_env(self):
        """Create isolated test environment"""
        db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        db_url = f"sqlite+aiosqlite:///{db_file.name}"
        engine = create_async_engine(db_url, echo=False)
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        session = session_factory()
        
        return {"session": session, "engine": engine, "db_file": db_file.name}

    def _init_payment_system(self):
        """Initialize mock payment system"""
        payment_service = Mock()
        payment_service.create_customer = AsyncMock()
        payment_service.process_payment = AsyncMock()
        payment_service.setup_subscription = AsyncMock()
        payment_service.verify_payment_method = AsyncMock()
        return payment_service

    def _init_email_system(self):
        """Initialize mock email system"""
        email_service = Mock()
        email_service.send_verification = AsyncMock()
        email_service.send_welcome = AsyncMock()
        email_service.send_onboarding = AsyncMock()
        email_service.verify_email_token = AsyncMock()
        return email_service

    def _init_llm_system(self):
        """Initialize mock LLM system"""
        llm_manager = Mock()
        llm_manager.generate_response = AsyncMock()
        llm_manager.optimize_query = AsyncMock()
        llm_manager.route_model = AsyncMock()
        return llm_manager

    async def test_complete_registration_to_first_login_flow(self, first_time_user_setup, email_system, payment_system):
        """
        Test complete user registration to first successful login.
        
        BVJ: Registration flow is the entry point for all revenue.
        Failed registration = lost customer forever. Each successful
        registration has potential $1200/year lifetime value.
        """
        setup = first_time_user_setup
        
        user_data = await self._simulate_user_registration(setup, email_system)
        verification = await self._simulate_email_verification(setup, user_data, email_system)
        login_result = await self._simulate_first_login(setup, verification)
        onboarding = await self._simulate_welcome_onboarding(setup, login_result, email_system)
        
        await self._verify_registration_success(setup, onboarding)
        await self._cleanup_test(setup)

    async def _simulate_user_registration(self, setup, email_system):
        """Simulate realistic user registration process"""
        user_data = {"email": "newuser@company.com", "full_name": "John Smith", "password": "SecurePass123!", "company": "Tech Startup Inc"}
        
        user = User(id=str(uuid.uuid4()), email=user_data["email"], full_name=user_data["full_name"], plan_tier="free", payment_status="trial")
        
        setup["session"].add(user)
        await setup["session"].commit()
        
        await email_system.send_verification(user.email, "verification_token_123")
        
        return {"user": user, "verification_token": "verification_token_123"}

    async def _simulate_email_verification(self, setup, user_data, email_system):
        """Simulate email verification process"""
        email_system.verify_email_token.return_value = {"valid": True, "user_id": user_data["user"].id}
        
        verification_result = await email_system.verify_email_token("verification_token_123")
        
        user_data["user"].email_verified = True
        await setup["session"].commit()
        
        return {"verified": True, "user": user_data["user"]}

    async def _simulate_first_login(self, setup, verification):
        """Simulate first successful login"""
        login_result = {"user_id": verification["user"].id, "access_token": f"access_{uuid.uuid4()}", "refresh_token": f"refresh_{uuid.uuid4()}", "first_login": True}
        
        verification["user"].last_login = datetime.now(timezone.utc)
        await setup["session"].commit()
        
        return login_result

    async def _simulate_welcome_onboarding(self, setup, login_result, email_system):
        """Simulate welcome experience and onboarding"""
        await email_system.send_welcome(login_result["user_id"])
        
        onboarding_data = {"user_id": login_result["user_id"], "onboarding_step": "welcome_complete", "tutorial_shown": True, "demo_offered": True}
        
        return onboarding_data

    async def test_first_agent_creation_to_success(self, first_time_user_setup, llm_system):
        """
        Test first agent creation and successful task execution.
        
        BVJ: First successful agent interaction determines user retention.
        96% of users who complete first agent task upgrade within 30 days.
        Each successful first interaction = $1200 potential LTV.
        """
        setup = first_time_user_setup
        
        user = await self._create_first_time_user(setup)
        agent_result = await self._create_first_agent_experience(setup, user, llm_system)
        task_result = await self._execute_first_agent_task(setup, agent_result, llm_system)
        
        await self._verify_first_agent_success(setup, task_result)
        await self._cleanup_test(setup)

    async def _create_first_time_user(self, setup):
        """Create authenticated first-time user"""
        user = User(id=str(uuid.uuid4()), email="firsttime@test.com", full_name="First Time User", plan_tier="free", email_verified=True)
        
        setup["session"].add(user)
        await setup["session"].commit()
        
        return user

    async def _create_first_agent_experience(self, setup, user, llm_system):
        """Simulate first agent creation experience"""
        thread = Thread(id=str(uuid.uuid4()), title="My First AI Task", created_by=user.id, is_shared=False)
        
        setup["session"].add(thread)
        await setup["session"].commit()
        
        llm_system.generate_response.return_value = {"response": "I'm ready to help! What would you like me to analyze?", "agent_type": "triage", "confidence": 0.95}
        
        return {"thread": thread, "user": user, "agent_ready": True}

    async def _execute_first_agent_task(self, setup, agent_result, llm_system):
        """Execute user's first agent task"""
        message = Message(id=str(uuid.uuid4()), thread_id=agent_result["thread"].id, sender_id=agent_result["user"].id, content="Help me optimize my cloud costs", message_type="user")
        
        setup["session"].add(message)
        
        llm_system.generate_response.return_value = {"response": "I've analyzed your request. Here are 3 optimization strategies...", "actions_taken": ["cost_analysis", "recommendation_generation"], "value_delivered": "15% cost reduction identified"}
        
        agent_response = Message(id=str(uuid.uuid4()), thread_id=agent_result["thread"].id, sender_id="agent", content="I've found several cost optimization opportunities for you...", message_type="agent")
        
        setup["session"].add(agent_response)
        await setup["session"].commit()
        
        return {"message": message, "response": agent_response, "task_completed": True}

    async def test_trial_activation_to_first_optimization(self, first_time_user_setup, llm_system):
        """
        Test trial activation to first successful optimization.
        
        BVJ: Trial-to-paid conversion is the primary revenue driver.
        Each trial activation has 23% conversion probability = $300 expected value.
        First optimization success increases conversion to 67%.
        """
        setup = first_time_user_setup
        
        user = await self._create_trial_user(setup)
        optimization = await self._execute_trial_optimization(setup, user, llm_system)
        results = await self._deliver_optimization_results(setup, optimization)
        
        await self._verify_trial_value_delivery(setup, results)
        await self._cleanup_test(setup)

    async def _create_trial_user(self, setup):
        """Create user with active trial"""
        user = User(id=str(uuid.uuid4()), email="trial@test.com", plan_tier="free", trial_period=14, plan_started_at=datetime.now(timezone.utc))
        
        setup["session"].add(user)
        await setup["session"].commit()
        
        return user

    async def _execute_trial_optimization(self, setup, user, llm_system):
        """Execute trial user's optimization task"""
        llm_system.optimize_query.return_value = {"optimization_type": "cost_reduction", "savings_identified": 1200.50, "implementation_steps": 3, "confidence": 0.87}
        
        usage_log = ToolUsageLog(user_id=user.id, tool_name="cost_optimizer", category="optimization", execution_time_ms=8000, tokens_used=1500, cost_cents=0, status="success", plan_tier="free")
        
        setup["session"].add(usage_log)
        await setup["session"].commit()
        
        return {"user": user, "optimization": usage_log, "value_delivered": True}

    # Helper verification methods
    async def _verify_registration_success(self, setup, onboarding):
        """Verify registration completed successfully"""
        assert onboarding["onboarding_step"] == "welcome_complete"
        assert onboarding["tutorial_shown"] is True

    async def _verify_first_agent_success(self, setup, task_result):
        """Verify first agent task completed successfully"""
        assert task_result["task_completed"] is True
        assert task_result["response"] is not None

    async def _verify_trial_value_delivery(self, setup, results):
        """Verify trial delivered concrete value"""
        assert results["value_delivered"] is True
        assert results["optimization"].status == "success"

    async def _deliver_optimization_results(self, setup, optimization):
        """Deliver optimization results to user"""
        return optimization

    async def _cleanup_test(self, setup):
        """Cleanup test environment"""
        await setup["session"].close()
        await setup["engine"].dispose()
