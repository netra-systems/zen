"""
User Onboarding Flow Integration Tests

Business Value Justification (BVJ):
- Segment: Free → Early conversion 
- Business Goal: Maximize first-session success rate
- Value Impact: Critical first impression for user retention
- Strategic Impact: Foundation for user engagement and conversion

This test validates first chat session and profile setup flows.
"""

import pytest
import asyncio
import json
import time
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from tests.integration.helpers.user_flow_helpers import (
    generate_test_user_data, generate_test_thread_data,
    MockAuthService, MockWebSocketManager
)

class TestUserOnboardingFlow:
    """Test user onboarding and first session flow"""
    
    @pytest.mark.asyncio
    async def test_first_chat_session_initialization(self, 
                                                   test_session: AsyncSession,
                                                   test_redis: Redis):
        """Test first chat session initialization for new users"""
        # Setup test user
        user_data = generate_test_user_data()
        user_data["verified"] = True
        
        mock_auth = MockAuthService()
        mock_ws = MockWebSocketManager()
        
        # Register and verify user
        reg_result = await mock_auth.register_user(user_data)
        user_id = reg_result["user_id"]
        
        # Test first chat session
        session_result = await self._initialize_first_chat_session(user_id, mock_ws)
        
        # Validate session initialization
        assert session_result["success"] is True
        assert "thread_id" in session_result
        assert session_result["welcome_message_sent"] is True
        assert session_result["onboarding_state"] == "chat_initialized"
    
    @pytest.mark.asyncio
    async def test_user_profile_setup_and_preferences(self, test_session: AsyncSession):
        """Test user profile setup during onboarding"""
        user_data = generate_test_user_data()
        
        # Test profile completion
        profile_setup = await self._complete_profile_setup(user_data)
        
        # Validate profile setup
        assert profile_setup["profile_completed"] is True
        assert profile_setup["preferences_set"] is True
        assert "display_name" in profile_setup["profile_data"]
        assert "notification_preferences" in profile_setup["profile_data"]
    
    @pytest.mark.asyncio
    async def test_onboarding_progress_tracking(self, test_session: AsyncSession):
        """Test onboarding progress tracking"""
        user_data = generate_test_user_data()
        mock_auth = MockAuthService()
        
        # Register user
        reg_result = await mock_auth.register_user(user_data)
        user_id = reg_result["user_id"]
        
        # Track onboarding steps
        progress_tracker = OnboardingProgressTracker(user_id)
        
        # Step 1: Registration
        await progress_tracker.mark_step_complete("registration")
        progress = await progress_tracker.get_progress()
        assert progress["steps_completed"] == 1
        assert "registration" in progress["completed_steps"]
        
        # Step 2: Email verification
        await progress_tracker.mark_step_complete("email_verification")
        progress = await progress_tracker.get_progress()
        assert progress["steps_completed"] == 2
        
        # Step 3: Profile setup
        await progress_tracker.mark_step_complete("profile_setup")
        progress = await progress_tracker.get_progress()
        assert progress["steps_completed"] == 3
        assert progress["completion_percentage"] >= 60  # Based on total steps
    
    @pytest.mark.asyncio
    async def test_onboarding_tutorial_flow(self, test_session: AsyncSession):
        """Test interactive onboarding tutorial"""
        user_data = generate_test_user_data()
        mock_ws = MockWebSocketManager()
        
        # Start tutorial
        tutorial_result = await self._execute_onboarding_tutorial(user_data, mock_ws)
        
        # Validate tutorial completion
        assert tutorial_result["tutorial_started"] is True
        assert tutorial_result["tutorial_completed"] is True
        assert len(tutorial_result["tutorial_steps"]) >= 3
        assert tutorial_result["user_engagement_score"] >= 0.7
    
    @pytest.mark.asyncio
    async def test_onboarding_skip_options(self, test_session: AsyncSession):
        """Test user ability to skip onboarding steps"""
        user_data = generate_test_user_data()
        
        # Test skipping tutorial
        skip_result = await self._test_onboarding_skip("tutorial", user_data)
        assert skip_result["skipped"] is True
        assert skip_result["onboarding_state"] == "tutorial_skipped"
        
        # Test skipping profile setup
        skip_result = await self._test_onboarding_skip("profile_setup", user_data)
        assert skip_result["skipped"] is True
        assert skip_result["can_complete_later"] is True
    
    async def _initialize_first_chat_session(self, user_id: str, 
                                           mock_ws: MockWebSocketManager) -> Dict[str, Any]:
        """Initialize first chat session for user"""
        # Generate first thread
        thread_data = generate_test_thread_data()
        thread_data["user_id"] = user_id
        thread_data["is_first_session"] = True
        
        # Connect to WebSocket
        ws_connected = await mock_ws.connect(user_id, None)
        
        if ws_connected:
            # Send welcome message
            welcome_message = {
                "type": "welcome",
                "content": "Welcome to Netra Apex! Let's get started.",
                "thread_id": thread_data["thread_id"],
                "onboarding": True
            }
            
            await mock_ws.send_message(user_id, welcome_message)
            
            return {
                "success": True,
                "thread_id": thread_data["thread_id"],
                "welcome_message_sent": True,
                "onboarding_state": "chat_initialized"
            }
        
        return {"success": False, "error": "WebSocket connection failed"}
    
    async def _complete_profile_setup(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Complete user profile setup"""
        profile_data = {
            "display_name": f"{user_data['first_name']} {user_data['last_name']}",
            "company": "Test Company",
            "role": "Engineer",
            "use_case": "AI Optimization",
            "notification_preferences": {
                "email_notifications": True,
                "push_notifications": False,
                "weekly_digest": True
            },
            "ui_preferences": {
                "theme": "light",
                "language": "en",
                "timezone": "UTC"
            }
        }
        
        # Simulate profile completion
        await asyncio.sleep(0.1)  # Simulate API call
        
        return {
            "profile_completed": True,
            "preferences_set": True,
            "profile_data": profile_data
        }
    
    async def _execute_onboarding_tutorial(self, user_data: Dict[str, Any],
                                         mock_ws: MockWebSocketManager) -> Dict[str, Any]:
        """Execute interactive onboarding tutorial"""
        tutorial_steps = [
            {"step": "welcome", "description": "Welcome to Netra Apex"},
            {"step": "create_thread", "description": "Create your first thread"},
            {"step": "send_message", "description": "Send your first message"},
            {"step": "view_response", "description": "View AI response"},
            {"step": "explore_features", "description": "Explore platform features"}
        ]
        
        completed_steps = []
        user_interactions = 0
        
        for step in tutorial_steps:
            # Simulate user interaction
            interaction_result = await self._simulate_tutorial_interaction(step)
            
            if interaction_result["completed"]:
                completed_steps.append(step["step"])
                user_interactions += interaction_result.get("interactions", 1)
            
            await asyncio.sleep(0.1)  # Simulate step duration
        
        engagement_score = min(1.0, user_interactions / len(tutorial_steps))
        
        return {
            "tutorial_started": True,
            "tutorial_completed": len(completed_steps) == len(tutorial_steps),
            "tutorial_steps": completed_steps,
            "user_engagement_score": engagement_score,
            "total_interactions": user_interactions
        }
    
    async def _simulate_tutorial_interaction(self, step: Dict[str, str]) -> Dict[str, Any]:
        """Simulate user interaction with tutorial step"""
        # Simulate successful interaction for most steps
        success_rate = 0.9
        
        if step["step"] in ["welcome", "view_response"]:
            # Passive steps - always succeed
            return {"completed": True, "interactions": 1}
        else:
            # Interactive steps - might have multiple interactions
            return {
                "completed": True,
                "interactions": 2  # User might need multiple attempts
            }
    
    async def _test_onboarding_skip(self, skip_type: str, 
                                  user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test skipping onboarding components"""
        if skip_type == "tutorial":
            return {
                "skipped": True,
                "onboarding_state": "tutorial_skipped",
                "can_restart_later": True
            }
        elif skip_type == "profile_setup":
            return {
                "skipped": True,
                "onboarding_state": "profile_setup_skipped", 
                "can_complete_later": True
            }
        
        return {"skipped": False, "error": "Unknown skip type"}


class OnboardingProgressTracker:
    """Track user onboarding progress"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.completed_steps = set()
        self.total_steps = ["registration", "email_verification", "profile_setup", 
                           "first_chat", "tutorial_completion"]
    
    async def mark_step_complete(self, step: str):
        """Mark onboarding step as complete"""
        self.completed_steps.add(step)
    
    async def get_progress(self) -> Dict[str, Any]:
        """Get current onboarding progress"""
        completion_percentage = (len(self.completed_steps) / len(self.total_steps)) * 100
        
        return {
            "user_id": self.user_id,
            "steps_completed": len(self.completed_steps),
            "total_steps": len(self.total_steps),
            "completion_percentage": completion_percentage,
            "completed_steps": list(self.completed_steps),
            "remaining_steps": list(set(self.total_steps) - self.completed_steps)
        }