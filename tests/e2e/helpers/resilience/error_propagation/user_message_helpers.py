"""User-Friendly Message Validation



This module contains utilities for validating user-friendly error messages

and cross-service tracking validation.

"""



import json

import logging



# Add project root to path for imports

import sys

from pathlib import Path

from typing import Any, Dict, List





from tests.e2e.helpers.resilience.error_propagation.error_generators import (

    ErrorCorrelationContext,

    ErrorInjectionHelper,

    RealErrorPropagationTester,

)



logger = logging.getLogger(__name__)





class UserFriendlyMessageValidator:

    """Validates users receive actionable, user-friendly error messages."""

    

    def __init__(self, tester: RealErrorPropagationTester):

        self.tester = tester

        self.message_quality_tests: List[Dict[str, Any]] = []

    

    async def test_user_friendly_error_messages(self) -> Dict[str, Any]:

        """Test that all error messages are user-friendly and actionable."""

        context = self.tester._create_correlation_context("user_friendly_messages")

        

        # Test various error scenarios for user-friendly messaging

        auth_result = await self._test_auth_error_messages(context)

        validation_result = await self._test_validation_error_messages(context)

        service_result = await self._test_service_error_messages(context)

        

        # Analyze overall message quality

        overall_quality = self._analyze_overall_message_quality(

            auth_result, validation_result, service_result

        )

        

        return {

            "test_type": "user_friendly_error_messages",

            "request_id": context.request_id,

            "auth_messages": auth_result,

            "validation_messages": validation_result,

            "service_messages": service_result,

            "overall_quality": overall_quality

        }

    

    async def _test_auth_error_messages(self, context: ErrorCorrelationContext) -> Dict[str, Any]:

        """Test auth error messages for user-friendliness."""

        context.service_chain.append("auth_messages")

        

        try:

            invalid_creds = ErrorInjectionHelper.create_invalid_credentials()

            response = await self.tester.http_client.post("/auth/token", json=invalid_creds)

            return {"unexpected_success": True}

            

        except Exception as e:

            return self._analyze_message_user_friendliness(str(e), "auth_error")

    

    async def _test_validation_error_messages(self, context: ErrorCorrelationContext) -> Dict[str, Any]:

        """Test validation error messages for user-friendliness."""

        context.service_chain.append("validation_messages")

        

        try:

            incomplete_data = ErrorInjectionHelper.create_malformed_request()

            response = await self.tester.http_client.post("/auth/token", json=incomplete_data)

            return {"unexpected_success": True}

            

        except Exception as e:

            return self._analyze_message_user_friendliness(str(e), "validation_error")

    

    async def _test_service_error_messages(self, context: ErrorCorrelationContext) -> Dict[str, Any]:

        """Test service error messages for user-friendliness."""

        context.service_chain.append("service_messages")

        

        try:

            response = await self.tester.http_client.get("/nonexistent/endpoint")

            return {"unexpected_success": True}

            

        except Exception as e:

            return self._analyze_message_user_friendliness(str(e), "service_error")

    

    def _analyze_message_user_friendliness(self, message: str, error_type: str) -> Dict[str, Any]:

        """Analyze error message for user-friendliness criteria."""

        message_lower = message.lower()

        

        # User-friendly language indicators

        friendly_indicators = self._get_friendly_indicators()

        user_friendly_count = sum(1 for indicator in friendly_indicators if indicator in message_lower)

        

        # Technical jargon that users shouldn't see

        technical_jargon = self._get_technical_jargon_indicators()

        technical_count = sum(1 for jargon in technical_jargon if jargon in message_lower)

        

        # Actionable guidance indicators

        actionable_indicators = self._get_actionable_indicators()

        actionable_count = sum(1 for indicator in actionable_indicators if indicator in message_lower)

        

        # Generate improvement suggestions

        improvement_suggestions = self._generate_improvement_suggestions(

            user_friendly_count, technical_count, actionable_count

        )

        

        return {

            "error_type": error_type,

            "user_friendly_score": user_friendly_count,

            "technical_jargon_score": technical_count,

            "actionable_guidance_score": actionable_count,

            "overall_user_friendly": (user_friendly_count > 0 and technical_count == 0),

            "actionable": actionable_count > 0,

            "improvement_suggestions": improvement_suggestions,

            "message": message

        }

    

    def _get_friendly_indicators(self) -> List[str]:

        """Get list of user-friendly language indicators."""

        return [

            "please", "try again", "contact support", "invalid", "check", "verify",

            "expired", "login", "refresh", "help", "assistance"

        ]

    

    def _get_technical_jargon_indicators(self) -> List[str]:

        """Get list of technical jargon that users shouldn't see."""

        return [

            "traceback", "exception", "stack trace", "null pointer", "internal server error",

            "500", "502", "503", "database", "connection pool", "timeout", "none", "null"

        ]

    

    def _get_actionable_indicators(self) -> List[str]:

        """Get list of actionable guidance indicators."""

        return [

            "try again", "contact", "check", "verify", "login", "refresh",

            "go to", "visit", "click", "enter", "provide"

        ]

    

    def _generate_improvement_suggestions(self, friendly_count: int, technical_count: int, actionable_count: int) -> List[str]:

        """Generate specific improvement suggestions for error messages."""

        suggestions = []

        

        if technical_count > 0:

            suggestions.append("reduce_technical_jargon")

        if friendly_count == 0:

            suggestions.append("add_friendly_language")

        if actionable_count == 0:

            suggestions.append("provide_actionable_steps")

        

        return suggestions

    

    def _analyze_overall_message_quality(self, *message_results) -> Dict[str, Any]:

        """Analyze overall quality of error messages across all scenarios."""

        total_tests = len(message_results)

        

        user_friendly_count = sum(1 for result in message_results 

                                if result.get("overall_user_friendly", False))

        actionable_count = sum(1 for result in message_results 

                             if result.get("actionable", False))

        

        # Collect all improvement suggestions

        all_suggestions = self._collect_improvement_suggestions(message_results)

        unique_suggestions = list(set(all_suggestions))

        

        return {

            "total_message_tests": total_tests,

            "user_friendly_messages": user_friendly_count,

            "actionable_messages": actionable_count,

            "user_friendly_percentage": self._calculate_percentage(user_friendly_count, total_tests),

            "actionable_percentage": self._calculate_percentage(actionable_count, total_tests),

            "improvement_needed": unique_suggestions,

            "message_quality_acceptable": (user_friendly_count >= total_tests * 0.6)  # 60% threshold

        }

    

    def _collect_improvement_suggestions(self, message_results) -> List[str]:

        """Collect all improvement suggestions from message results."""

        all_suggestions = []

        for result in message_results:

            if isinstance(result, dict) and "improvement_suggestions" in result:

                all_suggestions.extend(result["improvement_suggestions"])

        return all_suggestions

    

    def _calculate_percentage(self, count: int, total: int) -> float:

        """Calculate percentage safely."""

        return (count / total * 100) if total > 0 else 0





class CrossServiceTrackingValidator:

    """Validates error tracking across service boundaries."""

    

    def __init__(self, tester: RealErrorPropagationTester):

        self.tester = tester

    

    def validate_error_flow_tracking(self, context: ErrorCorrelationContext, error_responses: List[Dict[str, Any]]) -> Dict[str, Any]:

        """Validate error flow tracking across services."""

        tracking_indicators = []

        

        for response in error_responses:

            if self._has_tracking_info(response, context):

                tracking_indicators.append("tracking_preserved")

            if self._has_service_info(response):

                tracking_indicators.append("service_identified")

            if self._has_timestamp_info(response):

                tracking_indicators.append("timestamp_preserved")

        

        return {

            "tracking_indicators": tracking_indicators,

            "tracking_score": len(set(tracking_indicators)),

            "tracking_effective": len(set(tracking_indicators)) >= 2

        }

    

    def _has_tracking_info(self, response: Dict[str, Any], context: ErrorCorrelationContext) -> bool:

        """Check if response contains tracking information."""

        response_str = json.dumps(response).lower()

        return (

            context.request_id.lower() in response_str or

            context.session_id.lower() in response_str

        )

    

    def _has_service_info(self, response: Dict[str, Any]) -> bool:

        """Check if response contains service identification."""

        response_str = json.dumps(response).lower()

        service_indicators = ["service", "component", "module", "handler"]

        return any(indicator in response_str for indicator in service_indicators)

    

    def _has_timestamp_info(self, response: Dict[str, Any]) -> bool:

        """Check if response contains timestamp information."""

        response_str = json.dumps(response).lower()

        timestamp_indicators = ["timestamp", "time", "created", "occurred"]

        return any(indicator in response_str for indicator in timestamp_indicators)





class MessageQualityAnalyzer:

    """Utility for analyzing message quality patterns."""

    

    @staticmethod

    def analyze_message_patterns(messages: List[str]) -> Dict[str, Any]:

        """Analyze patterns across multiple error messages."""

        if not messages:

            return {"error": "No messages provided"}

        

        pattern_analysis = {

            "total_messages": len(messages),

            "avg_length": sum(len(msg) for msg in messages) / len(messages),

            "common_patterns": MessageQualityAnalyzer._find_common_patterns(messages),

            "quality_distribution": MessageQualityAnalyzer._analyze_quality_distribution(messages)

        }

        

        return pattern_analysis

    

    @staticmethod

    def _find_common_patterns(messages: List[str]) -> Dict[str, int]:

        """Find common patterns in error messages."""

        patterns = {}

        common_words = ["error", "failed", "invalid", "please", "try", "again"]

        

        for word in common_words:

            count = sum(1 for msg in messages if word.lower() in msg.lower())

            if count > 0:

                patterns[word] = count

        

        return patterns

    

    @staticmethod

    def _analyze_quality_distribution(messages: List[str]) -> Dict[str, int]:

        """Analyze quality distribution of messages."""

        quality_levels = {"high": 0, "medium": 0, "low": 0}

        

        for message in messages:

            score = MessageQualityAnalyzer._calculate_message_quality_score(message)

            if score >= 3:

                quality_levels["high"] += 1

            elif score >= 1:

                quality_levels["medium"] += 1

            else:

                quality_levels["low"] += 1

        

        return quality_levels

    

    @staticmethod

    def _calculate_message_quality_score(message: str) -> int:

        """Calculate quality score for a single message."""

        message_lower = message.lower()

        score = 0

        

        # Positive indicators

        if any(word in message_lower for word in ["please", "try", "help"]):

            score += 1

        if any(word in message_lower for word in ["check", "verify", "contact"]):

            score += 1

        if len(message) < 100:  # Concise messages

            score += 1

        

        # Negative indicators

        if any(word in message_lower for word in ["error", "exception", "failed"]):

            score -= 1

        if any(word in message_lower for word in ["internal", "null", "undefined"]):

            score -= 1

        

        return max(0, score)  # Ensure non-negative score

