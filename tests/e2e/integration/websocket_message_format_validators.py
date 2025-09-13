"""

WebSocket Message Format Validators



Validators for WebSocket message format compliance.

"""



import json

from typing import Dict, Any, List



class WebSocketMessageValidator:

    """Validate WebSocket message formats."""

    

    def validate_message_structure(self, message: Dict[str, Any]) -> bool:

        """Validate basic message structure."""

        required_fields = ["type", "timestamp"]

        return all(field in message for field in required_fields)

    

    def validate_thread_message(self, message: Dict[str, Any]) -> bool:

        """Validate thread-related message."""

        if not self.validate_message_structure(message):

            return False

        

        if message.get("type") == "thread_update":

            return "thread_id" in message and "data" in message

        

        return True

    

    def validate_agent_message(self, message: Dict[str, Any]) -> bool:

        """Validate agent-related message."""

        if not self.validate_message_structure(message):

            return False

        

        if message.get("type") == "agent_response":

            return "agent_id" in message and "content" in message

        

        return True



class MessageFormatValidator:

    """Validator for WebSocket message formats (alias for compatibility)."""

    

    def __init__(self):

        self.validator = WebSocketMessageValidator()

    

    def validate_message(self, message: Dict[str, Any]) -> bool:

        """Validate a single message format."""

        return self.validator.validate_message_structure(message)

    

    def validate_thread_message(self, message: Dict[str, Any]) -> bool:

        """Validate thread message format."""

        return self.validator.validate_thread_message(message)

    

    def validate_agent_message(self, message: Dict[str, Any]) -> bool:

        """Validate agent message format."""

        return self.validator.validate_agent_message(message)

    

    def validate_message_batch(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:

        """Validate multiple messages and return results."""

        valid_count = 0

        errors = []

        

        for i, message in enumerate(messages):

            try:

                if self.validate_message(message):

                    valid_count += 1

                else:

                    errors.append(f"Message {i}: Invalid format")

            except Exception as e:

                errors.append(f"Message {i}: {str(e)}")

        

        return {

            "total": len(messages),

            "valid": valid_count,

            "invalid": len(messages) - valid_count,

            "errors": errors

        }



class MessageFormatTester:

    """Test message format compliance."""

    

    def __init__(self):

        self.validator = WebSocketMessageValidator()

    

    def test_message_formats(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:

        """Test multiple message formats."""

        results = {

            "total": len(messages),

            "valid": 0,

            "invalid": 0,

            "errors": []

        }

        

        for i, message in enumerate(messages):

            try:

                if self.validator.validate_message_structure(message):

                    results["valid"] += 1

                else:

                    results["invalid"] += 1

                    results["errors"].append(f"Message {i}: Invalid structure")

            except Exception as e:

                results["invalid"] += 1

                results["errors"].append(f"Message {i}: {str(e)}")

        

        return results





class FieldConsistencyChecker:

    """Check field consistency across WebSocket messages."""

    

    def __init__(self):

        self.field_patterns = {

            "timestamp": {"required": True, "type": (int, float, str)},

            "message_id": {"required": True, "type": str},

            "thread_id": {"required": False, "type": str},

            "user_id": {"required": False, "type": str},

            "type": {"required": True, "type": str}

        }

    

    def check_field_consistency(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:

        """Check field consistency across multiple messages.

        

        Args:

            messages: List of messages to check

            

        Returns:

            Consistency check results

        """

        results = {

            "total_messages": len(messages),

            "consistent_fields": [],

            "inconsistent_fields": [],

            "missing_required_fields": [],

            "field_coverage": {}

        }

        

        if not messages:

            return results

        

        # Analyze field patterns across all messages

        all_fields = set()

        field_counts = {}

        field_type_consistency = {}

        

        for msg in messages:

            for field_name, field_value in msg.items():

                all_fields.add(field_name)

                field_counts[field_name] = field_counts.get(field_name, 0) + 1

                

                # Track type consistency

                field_type = type(field_value).__name__

                if field_name not in field_type_consistency:

                    field_type_consistency[field_name] = set()

                field_type_consistency[field_name].add(field_type)

        

        # Calculate field coverage

        for field in all_fields:

            coverage_percent = (field_counts[field] / len(messages)) * 100

            results["field_coverage"][field] = {

                "count": field_counts[field],

                "percentage": coverage_percent,

                "type_consistency": len(field_type_consistency[field]) == 1,

                "types_found": list(field_type_consistency[field])

            }

            

            # Determine if field is consistent

            if coverage_percent == 100 and len(field_type_consistency[field]) == 1:

                results["consistent_fields"].append(field)

            else:

                results["inconsistent_fields"].append(field)

        

        # Check required fields

        for msg in messages:

            for field_name, pattern in self.field_patterns.items():

                if pattern["required"] and field_name not in msg:

                    if field_name not in results["missing_required_fields"]:

                        results["missing_required_fields"].append(field_name)

        

        return results

    

    def validate_field_types(self, message: Dict[str, Any]) -> List[str]:

        """Validate field types in a single message.

        

        Args:

            message: Message to validate

            

        Returns:

            List of validation errors

        """

        errors = []

        

        for field_name, pattern in self.field_patterns.items():

            if field_name in message:

                field_value = message[field_name]

                expected_types = pattern["type"] if isinstance(pattern["type"], tuple) else (pattern["type"],)

                

                if not isinstance(field_value, expected_types):

                    errors.append(

                        f"Field '{field_name}' has type {type(field_value).__name__}, "

                        f"expected {[t.__name__ for t in expected_types]}"

                    )

            elif pattern["required"]:

                errors.append(f"Required field '{field_name}' is missing")

        

        return errors





class CoroutineErrorDetector:

    """Detect common coroutine-related errors in WebSocket message handling."""

    

    def __init__(self):

        self.error_patterns = [

            "coroutine was never awaited",

            "RuntimeError: cannot be called from a running event loop",

            "Task was destroyed but it is pending",

            "Event loop is closed"

        ]

    

    def detect_coroutine_errors(self, error_messages: List[str]) -> Dict[str, Any]:

        """Detect coroutine-related errors from error messages.

        

        Args:

            error_messages: List of error messages to analyze

            

        Returns:

            Analysis results with detected errors

        """

        results = {

            "total_errors": len(error_messages),

            "coroutine_errors": [],

            "other_errors": [],

            "common_patterns": {}

        }

        

        for error_msg in error_messages:

            is_coroutine_error = False

            

            for pattern in self.error_patterns:

                if pattern.lower() in error_msg.lower():

                    results["coroutine_errors"].append({

                        "message": error_msg,

                        "pattern": pattern,

                        "severity": self._get_error_severity(pattern)

                    })

                    

                    # Count pattern frequency

                    if pattern not in results["common_patterns"]:

                        results["common_patterns"][pattern] = 0

                    results["common_patterns"][pattern] += 1

                    

                    is_coroutine_error = True

                    break

            

            if not is_coroutine_error:

                results["other_errors"].append(error_msg)

        

        return results

    

    def _get_error_severity(self, pattern: str) -> str:

        """Get severity level for error pattern."""

        high_severity = [

            "Event loop is closed",

            "RuntimeError: cannot be called from a running event loop"

        ]

        

        medium_severity = [

            "Task was destroyed but it is pending"

        ]

        

        if pattern in high_severity:

            return "high"

        elif pattern in medium_severity:

            return "medium"

        else:

            return "low"

    

    def suggest_fixes(self, coroutine_errors: List[Dict[str, Any]]) -> List[str]:

        """Suggest fixes for detected coroutine errors.

        

        Args:

            coroutine_errors: List of detected coroutine errors

            

        Returns:

            List of suggested fixes

        """

        suggestions = set()  # Use set to avoid duplicates

        

        for error in coroutine_errors:

            pattern = error["pattern"]

            

            if "coroutine was never awaited" in pattern:

                suggestions.add("Add 'await' before async function calls")

                suggestions.add("Use asyncio.create_task() for fire-and-forget operations")

                

            elif "cannot be called from a running event loop" in pattern:

                suggestions.add("Use asyncio.create_task() instead of asyncio.run()")

                suggestions.add("Avoid nested event loop calls")

                

            elif "Task was destroyed but it is pending" in pattern:

                suggestions.add("Properly await or cancel pending tasks before cleanup")

                suggestions.add("Use try/finally blocks to ensure task cleanup")

                

            elif "Event loop is closed" in pattern:

                suggestions.add("Check if event loop is running before scheduling tasks")

                suggestions.add("Create new event loop if needed")

        

        return list(suggestions)





class MessageStructureValidator:

    """Validate WebSocket message structure compliance."""

    

    def __init__(self):

        self.base_validator = WebSocketMessageValidator()

        self.required_structure = {

            "type": str,

            "timestamp": (int, float, str),

            "data": dict

        }

    

    def validate_message_structure(self, message: Dict[str, Any]) -> Dict[str, Any]:

        """Validate message structure against expected format.

        

        Args:

            message: Message to validate

            

        Returns:

            Validation results

        """

        results = {

            "valid": True,

            "errors": [],

            "warnings": [],

            "structure_score": 0

        }

        

        total_checks = len(self.required_structure)

        passed_checks = 0

        

        for field_name, expected_type in self.required_structure.items():

            if field_name not in message:

                results["errors"].append(f"Missing required field: {field_name}")

                results["valid"] = False

            else:

                field_value = message[field_name]

                expected_types = expected_type if isinstance(expected_type, tuple) else (expected_type,)

                

                if isinstance(field_value, expected_types):

                    passed_checks += 1

                else:

                    results["errors"].append(

                        f"Field '{field_name}' has incorrect type. "

                        f"Expected {[t.__name__ for t in expected_types]}, got {type(field_value).__name__}"

                    )

                    results["valid"] = False

        

        # Calculate structure score

        results["structure_score"] = (passed_checks / total_checks) * 100 if total_checks > 0 else 0

        

        # Add warnings for optional but recommended fields

        recommended_fields = ["message_id", "user_id"]

        for field in recommended_fields:

            if field not in message:

                results["warnings"].append(f"Recommended field missing: {field}")

        

        return results

    

    def validate_batch_structure(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:

        """Validate structure of multiple messages.

        

        Args:

            messages: List of messages to validate

            

        Returns:

            Batch validation results

        """

        batch_results = {

            "total_messages": len(messages),

            "valid_messages": 0,

            "invalid_messages": 0,

            "average_structure_score": 0,

            "common_errors": {},

            "individual_results": []

        }

        

        total_score = 0

        

        for i, message in enumerate(messages):

            result = self.validate_message_structure(message)

            batch_results["individual_results"].append(result)

            

            if result["valid"]:

                batch_results["valid_messages"] += 1

            else:

                batch_results["invalid_messages"] += 1

            

            total_score += result["structure_score"]

            

            # Track common errors

            for error in result["errors"]:

                if error not in batch_results["common_errors"]:

                    batch_results["common_errors"][error] = 0

                batch_results["common_errors"][error] += 1

        

        # Calculate average score

        if messages:

            batch_results["average_structure_score"] = total_score / len(messages)

        

        return batch_results

