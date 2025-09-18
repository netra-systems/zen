from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase
"""

Mission Critical Server Message Validator Integration Tests

Integration tests that validate the MissionCriticalEventValidator works 
with actual WebSocket messages in both flat and ServerMessage formats.

BUSINESS IMPACT: $500K+ plus ARR depends on proper WebSocket event validation
to ensure Golden Path chat functionality works correctly.

Issue #892: Integration validation that the validator fix works with
real WebSocket message structures.
""
""


"""
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, List, Any

from tests.mission_critical.test_websocket_agent_events_suite import MissionCriticalEventValidator


class ServerMessageValidatorIntegrationTests(SSotBaseTestCase):
    "Integration test for MissionCriticalEventValidator with real message formats."

    def setup_method(self, method):
        "Set up test validator and sample messages."
super().setup_method(method)

        self.validator = MissionCriticalEventValidator()
self.test_timestamp = datetime.now(timezone.utc).isoformat()

        # Sample flat format messages (legacy)
self.flat_messages = [
{
type: "agent_started,"
user_id": test-user-123,"
thread_id: test-thread-456
timestamp": self.test_timestamp"

{
type: agent_thinking
reasoning: Processing user request","
"timestamp: self.test_timestamp"

{
type: tool_executing
tool_name": search_data,"
parameters: {query: test},""
parameters: {query: test},""
"timestamp: self.test_timestamp"

{
type: tool_completed
tool_name": search_data, "
results: {data: results},""
results: {data: results},""
"duration: 1.5,"
timestamp: self.test_timestamp

{
"type: agent_completed,"
status: success
final_response: Task completed","
"timestamp: self.test_timestamp"


        # Sample ServerMessage format messages (current system)
self.server_messages = [
{
type: agent_started
payload": {"
user_id: test-user-123
thread_id: test-thread-456","
"timestamp: self.test_timestamp,"
agent_name: supervisor

sender": system,"
timestamp: self.test_timestamp

{
type: agent_thinking","
"payload: {"
reasoning: Processing user request
timestamp": self.test_timestamp,"
agent_name: supervisor

sender: system","
"timestamp: self.test_timestamp"

{
type: tool_executing
payload": {"
tool_name: search_data
parameters: {query": test},"
timestamp: self.test_timestamp
"sub_agent_name: data_helper"

sender: system
timestamp: self.test_timestamp""
timestamp: self.test_timestamp""

{
type": tool_completed,"
payload: {
"tool_name: search_data, "
results: {data: results},""
results: {data: results},""
duration": 1.5,"
timestamp: self.test_timestamp
sub_agent_name": data_helper"

sender: system
timestamp: self.test_timestamp""
timestamp: self.test_timestamp""

{
"type: agent_completed,"
payload: {
status": success,"
final_response: Task completed
timestamp: self.test_timestamp,""
timestamp: self.test_timestamp,""
"agent_name: supervisor"

sender: system
"timestamp: self.test_timestamp"


    def test_flat_messages_validation_batch(self):
        Test that flat format messages all validate correctly.""
Test that flat format messages all validate correctly.""

        all_passed = True
failed_events = []

        for message in self.flat_messages:
            self.validator.errors = []  # Clear errors for each test
event_type = message["type]"

            result = self.validator.validate_event_content_structure(message, event_type)
if not result:
                all_passed = False
failed_events.append({
event_type: event_type
"errors: self.validator.errors.copy()"


        self.assertTrue(all_passed, fSome flat messages failed validation: {failed_events})

    def test_server_messages_validation_batch(self):
        Test that ServerMessage format messages all validate correctly after fix.""
all_passed = True
failed_events = []

        for message in self.server_messages:
            self.validator.errors = []  # Clear errors for each test
event_type = message[type]

            result = self.validator.validate_event_content_structure(message, event_type)
if not result:
                all_passed = False
failed_events.append({
"event_type: event_type,"
errors: self.validator.errors.copy()
message: message""
message: message""


        self.assertTrue(all_passed, fSome ServerMessage format messages failed validation: {failed_events}")"

    def test_mixed_format_validation(self):
        Test that validator handles mixed flat and ServerMessage formats in same validation run.""
# Mix of flat and server messages
mixed_messages = [
# Flat format
{
type: agent_started
user_id: "user-1,"
thread_id": thread-1,"
timestamp: self.test_timestamp

# ServerMessage format
{
"type: agent_thinking,"
payload: {
reasoning: "Analyzing request,"
timestamp": self.test_timestamp"

sender: system

# Flat format
{
"type: tool_executing,"
tool_name: search
parameters: {},""
parameters: {},""
timestamp": self.test_timestamp"

# ServerMessage format
{
type: agent_completed
"payload: {"
status: success
final_response: "Done,"
timestamp": self.test_timestamp"

sender: system


        all_passed = True
failed_events = []

        for message in mixed_messages:
            self.validator.errors = []
event_type = message["type]"

            result = self.validator.validate_event_content_structure(message, event_type)
if not result:
                all_passed = False
failed_events.append({
event_type: event_type
format: ServerMessage" if payload in message else flat,"
errors: self.validator.errors.copy()


        self.assertTrue(all_passed, fMixed format validation failed: {failed_events}")"

    def test_complete_validation_workflow(self):
        Test complete validation workflow with both message formats.""
Test complete validation workflow with both message formats.""
# Simulate a complete agent execution with mixed formats
execution_messages = [
# Start with ServerMessage format (current system)
{
type": agent_started,"
payload: {
"user_id: integration-test-user,"
thread_id: integration-test-thread
timestamp: self.test_timestamp,""
timestamp: self.test_timestamp,""
agent_name": supervisor"

sender: system

{
type": agent_thinking, "
payload: {
reasoning: Starting analysis of user query","
"timestamp: self.test_timestamp"

sender: system

{
type": tool_executing,"
payload: {
tool_name: data_search","
"parameters: {query: integration test},"
timestamp": self.test_timestamp"

sender: system

{
type: tool_completed","
"payload: {"
tool_name: data_search
results": {found: True, count: 5},"
duration: 2.1,""
duration: 2.1,""
timestamp": self.test_timestamp"

sender: system

{
"type: agent_completed,"
payload: {
status: "success,"
final_response": Integration test completed successfully,"
timestamp: self.test_timestamp

"sender: system"


        # Process all messages through validator
self.validator.events = []
self.validator.errors = []

        for message in execution_messages:
            self.validator.events.append(message)
event_type = message[type]
result = self.validator.validate_event_content_structure(message, event_type)

            # Each message should validate successfully
self.assertTrue(result
fMessage {event_type} failed validation: {self.validator.errors})""
fMessage {event_type} failed validation: {self.validator.errors})""

        
        # Verify all critical events are present
event_types = [msg["type] for msg in execution_messages]"
required_events = [agent_started, agent_thinking, tool_executing", tool_completed, agent_completed]"

        for required in required_events:
            self.assertIn(required, event_types, fMissing required event: {required})

        # Verify no validation errors
self.assertEqual(len(self.validator.errors), 0
fValidation should pass with no errors, but got: {self.validator.errors}")"

    def test_validation_error_reporting(self):
        Test that validation errors are properly reported with format information.""
Test that validation errors are properly reported with format information.""
# Incomplete ServerMessage
incomplete_server = {
type": agent_started,"
payload: {
"user_id: test-user"
# Missing thread_id and timestamp

sender: system


        # Incomplete flat message
incomplete_flat = {
type: tool_executing","
"tool_name: search"
# Missing parameters and timestamp


        # Test ServerMessage error reporting
self.validator.errors = []
result1 = self.validator.validate_event_content_structure(incomplete_server, agent_started)
self.assertFalse(result1, Should fail validation for incomplete ServerMessage")"
self.assertGreater(len(self.validator.errors), 0, Should have validation errors)
self.assertIn(ServerMessage format, self.validator.errors[0], "Error should specify ServerMessage format)"

        # Test flat message error reporting  
self.validator.errors = []
result2 = self.validator.validate_event_content_structure(incomplete_flat, tool_executing")"
self.assertFalse(result2, Should fail validation for incomplete flat message)
self.assertGreater(len(self.validator.errors), 0, Should have validation errors")"
self.assertIn(flat format, self.validator.errors[0], Error should specify flat format)


if __name__ == __main__":"
unittest.main()
)
"""