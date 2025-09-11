#!/usr/bin/env python3
"""
Developer Training Generator - Level 4 Process & Training
CRITICAL: Prevents process gaps through comprehensive developer education

Business Value: Protects $500K+ ARR through systematic developer training
Revenue Impact: Eliminates knowledge gaps causing production failures
"""

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum


class TrainingLevel(Enum):
    """Training difficulty levels"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class TrainingFormat(Enum):
    """Training material formats"""
    MARKDOWN = "markdown"
    INTERACTIVE = "interactive"
    VIDEO_SCRIPT = "video_script"
    CHECKLIST = "checklist"
    DECISION_TREE = "decision_tree"


@dataclass
class TrainingModule:
    """Individual training module"""
    title: str
    description: str
    level: TrainingLevel
    format: TrainingFormat
    estimated_duration_minutes: int
    learning_objectives: List[str]
    content: str
    examples: List[Dict[str, str]]
    common_mistakes: List[Dict[str, str]]
    best_practices: List[str]
    assessment_questions: List[Dict[str, Any]]
    prerequisites: List[str] = None
    
    def __post_init__(self):
        if self.prerequisites is None:
            self.prerequisites = []


class AsyncPatternTrainingGenerator:
    """Generates comprehensive async pattern training materials"""
    
    def __init__(self):
        self.modules: List[TrainingModule] = []
    
    def generate_beginner_module(self) -> TrainingModule:
        """Generate beginner async/await training module"""
        content = """
# Python Async/Await Fundamentals for Netra Developers

## What is Asynchronous Programming?

Asynchronous programming allows your code to handle multiple operations concurrently without blocking. This is crucial for:
- WebSocket connections (real-time chat)
- Database operations (user data access)
- API calls (service-to-service communication)
- File I/O operations

## Basic Async/Await Syntax

### Async Function Declaration
```python
# ✅ CORRECT - Async function
async def fetch_user_data(user_id: str) -> UserData:
    # This function can use await
    user = await database.get_user(user_id)
    return user

# ❌ INCORRECT - Missing async keyword
def fetch_user_data(user_id: str) -> UserData:
    user = await database.get_user(user_id)  # SyntaxError!
    return user
```

### Calling Async Functions
```python
# ✅ CORRECT - Using await in async context
async def process_user_request(user_id: str):
    user_data = await fetch_user_data(user_id)
    return user_data

# ❌ INCORRECT - Missing await keyword
async def process_user_request(user_id: str):
    user_data = fetch_user_data(user_id)  # Returns coroutine object, not data!
    return user_data

# ❌ INCORRECT - Using await in non-async function
def process_user_request(user_id: str):
    user_data = await fetch_user_data(user_id)  # SyntaxError!
    return user_data
```

## The Golden Rule: await + async

**GOLDEN RULE**: If you see `await`, the containing function MUST be `async`

```python
# ✅ CORRECT
async def my_function():
    result = await some_async_operation()
    return result

# ❌ INCORRECT 
def my_function():
    result = await some_async_operation()  # Error!
    return result
```

## Common Netra Patterns

### WebSocket Event Handling
```python
# ✅ CORRECT - Async WebSocket handler
async def handle_websocket_message(websocket, message):
    result = await process_agent_request(message)
    await websocket.send_json(result)

# ❌ INCORRECT - Sync handler with async operations
def handle_websocket_message(websocket, message):
    result = await process_agent_request(message)  # Error!
    websocket.send_json(result)
```

### Agent Execution
```python
# ✅ CORRECT - Async agent execution
async def execute_agent(context: UserExecutionContext) -> AgentResult:
    agent = await create_agent(context)
    result = await agent.run()
    return result

# ❌ INCORRECT - Missing await on async operations
async def execute_agent(context: UserExecutionContext) -> AgentResult:
    agent = create_agent(context)  # Missing await!
    result = agent.run()           # Missing await!
    return result
```

## Debugging Async Issues

### Symptom: "coroutine was never awaited"
**Problem**: You called an async function without `await`
**Solution**: Add `await` keyword

### Symptom: "object has no attribute 'X'" 
**Problem**: You're working with a coroutine object instead of the actual result
**Solution**: Make sure you're using `await` on async function calls

### Symptom: "'await' outside async function"
**Problem**: Using `await` in a non-async function
**Solution**: Make the function `async` or remove the `await`
"""

        examples = [
            {
                "title": "Correct WebSocket Handler",
                "code": """async def handle_chat_message(websocket, message):
    # Process the message asynchronously
    response = await agent_service.process_message(message)
    # Send response back
    await websocket.send_json(response)"""
            },
            {
                "title": "Correct Database Operation", 
                "code": """async def save_user_data(user_id: str, data: Dict):
    # Both operations need await
    user = await database.get_user(user_id)
    result = await database.save_user_data(user.id, data)
    return result"""
            }
        ]
        
        common_mistakes = [
            {
                "mistake": "Using await in sync function",
                "example": "def my_func(): result = await async_call()",
                "fix": "Make function async: async def my_func():"
            },
            {
                "mistake": "Missing await on async calls",
                "example": "async def my_func(): result = async_call()",
                "fix": "Add await: result = await async_call()"
            },
            {
                "mistake": "Calling async from sync without asyncio.run",
                "example": "result = my_async_function()",
                "fix": "Use: result = asyncio.run(my_async_function())"
            }
        ]
        
        assessment_questions = [
            {
                "question": "What keyword must you use when calling an async function from another async function?",
                "options": ["wait", "await", "async", "call"],
                "correct": 1,
                "explanation": "The 'await' keyword is required to call async functions and get their result."
            },
            {
                "question": "Can you use 'await' in a regular (non-async) function?",
                "options": ["Yes, always", "No, never", "Only with try/except", "Only in main()"],
                "correct": 1,
                "explanation": "'await' can only be used inside async functions. Using it elsewhere causes a SyntaxError."
            }
        ]
        
        return TrainingModule(
            title="Async/Await Fundamentals for Netra Platform",
            description="Essential async programming concepts for Netra developers",
            level=TrainingLevel.BEGINNER,
            format=TrainingFormat.MARKDOWN,
            estimated_duration_minutes=30,
            learning_objectives=[
                "Understand when to use async/await",
                "Identify correct async function syntax", 
                "Recognize common async pattern mistakes",
                "Debug basic async/await issues"
            ],
            content=content,
            examples=examples,
            common_mistakes=common_mistakes,
            best_practices=[
                "Always use await when calling async functions",
                "Make functions async if they contain await",
                "Use asyncio.run() to call async functions from sync code",
                "Check function signatures to know if they're async"
            ],
            assessment_questions=assessment_questions
        )
    
    def generate_intermediate_module(self) -> TrainingModule:
        """Generate intermediate async patterns training"""
        content = """
# Advanced Async Patterns in Netra Architecture

## WebSocket Event Patterns

### Correct Event Handler Patterns
```python
# ✅ CORRECT - Full async WebSocket handler
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    try:
        while True:
            # Receive message asynchronously
            message = await websocket.receive_json()
            
            # Process with proper async context
            context = await create_user_context(message.get('user_id'))
            response = await agent_service.process_message(context, message)
            
            # Send response asynchronously
            await websocket.send_json(response)
            
    except WebSocketDisconnect:
        # Handle disconnection
        await cleanup_user_session(context.user_id)
```

### Anti-patterns to Avoid
```python
# ❌ INCORRECT - Mixed sync/async patterns
def websocket_endpoint(websocket: WebSocket):
    asyncio.run(websocket.accept())  # Bad: nested event loop
    
    message = websocket.receive_json()  # Bad: should be await
    response = process_message(message)  # Bad: should be async
    
    asyncio.run(websocket.send_json(response))  # Bad: nested event loop
```

## Agent Execution Patterns

### Proper Agent Orchestration
```python
# ✅ CORRECT - Async agent execution with proper context
async def execute_agent_pipeline(user_context: UserExecutionContext) -> AgentResult:
    # Initialize agent asynchronously
    agent = await agent_factory.create_agent(user_context)
    
    # Execute with proper async monitoring
    execution_tracker = await get_execution_tracker(user_context.user_id)
    
    try:
        # Start execution tracking
        await execution_tracker.start_execution(agent.id)
        
        # Run agent asynchronously
        result = await agent.run()
        
        # Complete execution tracking
        await execution_tracker.complete_execution(agent.id, result)
        
        return result
        
    except Exception as e:
        # Handle failure asynchronously
        await execution_tracker.fail_execution(agent.id, str(e))
        raise
```

## Database Operation Patterns

### Transaction Handling
```python
# ✅ CORRECT - Async database transactions
async def save_agent_results(user_id: str, results: List[AgentResult]):
    async with database.transaction():
        # All operations in transaction
        user = await database.get_user(user_id)
        
        for result in results:
            await database.save_result(user.id, result)
            await database.update_user_stats(user.id, result.metrics)
        
        # Transaction auto-commits on success
```

## Error Handling in Async Context

### Proper Exception Handling
```python
# ✅ CORRECT - Async exception handling
async def robust_agent_execution(context: UserExecutionContext):
    try:
        # Multiple async operations that might fail
        agent = await create_agent(context)
        validation_result = await validate_agent_context(agent, context)
        
        if not validation_result.is_valid:
            raise ValidationError(validation_result.error_message)
        
        result = await agent.run()
        await save_execution_result(context.user_id, result)
        
        return result
        
    except ValidationError as e:
        # Log validation errors asynchronously
        await log_validation_error(context.user_id, str(e))
        raise
        
    except Exception as e:
        # Handle unexpected errors asynchronously
        await log_unexpected_error(context.user_id, str(e))
        raise AgentExecutionError("Agent execution failed") from e
```

## Performance Considerations

### Concurrent Execution
```python
# ✅ CORRECT - Concurrent async operations
async def process_multiple_users(user_ids: List[str]):
    # Create tasks for concurrent execution
    tasks = [
        process_user_data(user_id) 
        for user_id in user_ids
    ]
    
    # Wait for all to complete concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Handle results and exceptions
    successful_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            await log_processing_error(user_ids[i], result)
        else:
            successful_results.append(result)
    
    return successful_results
```

### Avoiding Blocking Operations
```python
# ❌ INCORRECT - Blocking operations in async function
async def bad_async_function():
    result = requests.get("https://api.example.com")  # Blocks!
    time.sleep(1)  # Blocks!
    return result.json()

# ✅ CORRECT - Non-blocking alternatives
async def good_async_function():
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.example.com")
    
    await asyncio.sleep(1)  # Non-blocking sleep
    return response.json()
```
"""

        return TrainingModule(
            title="Advanced Async Patterns in Netra Architecture",
            description="Intermediate async patterns for WebSocket, agents, and database operations",
            level=TrainingLevel.INTERMEDIATE,
            format=TrainingFormat.MARKDOWN,
            estimated_duration_minutes=45,
            learning_objectives=[
                "Implement proper WebSocket async patterns",
                "Handle agent execution with async contexts",
                "Manage database transactions asynchronously",
                "Handle errors in async functions correctly",
                "Optimize performance with concurrent execution"
            ],
            content=content,
            examples=[
                {
                    "title": "WebSocket Handler with Error Handling",
                    "code": """async def websocket_handler(websocket: WebSocket, user_id: str):
    context = await create_user_context(user_id)
    
    try:
        await websocket.accept()
        
        async for message in websocket.iter_json():
            try:
                response = await process_message(context, message)
                await websocket.send_json(response)
            except ProcessingError as e:
                await websocket.send_json({"error": str(e)})
                
    except WebSocketDisconnect:
        await cleanup_context(context)"""
                }
            ],
            common_mistakes=[
                {
                    "mistake": "Using blocking operations in async functions",
                    "example": "async def bad(): return requests.get(url)",
                    "fix": "Use async HTTP client: async with httpx.AsyncClient() as client: return await client.get(url)"
                },
                {
                    "mistake": "Not handling async exceptions properly",
                    "example": "try: await async_op() except: pass",
                    "fix": "Handle specific exceptions and log asynchronously"
                }
            ],
            best_practices=[
                "Use asyncio.gather() for concurrent operations",
                "Always use async context managers for resources",
                "Handle exceptions at the appropriate async level",
                "Avoid mixing sync and async operations",
                "Use async logging for error reporting"
            ],
            assessment_questions=[
                {
                    "question": "What's the correct way to make multiple async calls concurrently?",
                    "options": ["for loop with await", "asyncio.gather()", "threading", "multiprocessing"],
                    "correct": 1,
                    "explanation": "asyncio.gather() runs multiple coroutines concurrently in a single thread."
                }
            ],
            prerequisites=["Async/Await Fundamentals"]
        )
    
    def generate_code_review_checklist(self) -> TrainingModule:
        """Generate async pattern code review checklist"""
        content = """
# Async Pattern Code Review Checklist

Use this checklist when reviewing code changes that involve async/await patterns.

## Pre-Review Setup
- [ ] Identify all functions that were changed
- [ ] Check if any function signatures changed from sync to async (or vice versa)
- [ ] Look for new async dependencies or imports

## Function Signature Review

### For Each Function:
- [ ] **Async Declaration**: If function contains `await`, is it declared `async`?
- [ ] **Return Type**: Does return type annotation match async/sync nature?
  - Async functions should return `Coroutine[Any, Any, ReturnType]` or just `ReturnType`
  - Sync functions should not return coroutine types
- [ ] **Parameter Types**: Do parameter types support async operations correctly?

### Examples to Check:
```python
# ✅ GOOD - Consistent async function
async def process_data(data: Dict) -> ProcessResult:
    result = await database.save(data)
    return result

# ❌ BAD - Missing async keyword
def process_data(data: Dict) -> ProcessResult:
    result = await database.save(data)  # Will cause SyntaxError
    return result

# ❌ BAD - Wrong return type
async def process_data(data: Dict) -> Coroutine[Any, Any, ProcessResult]:
    result = await database.save(data)
    return result  # Type mismatch - should just be ProcessResult
```

## Function Call Review

### For Each Function Call:
- [ ] **Await Usage**: Are async functions called with `await`?
- [ ] **Missing Await**: Are sync functions called without `await`?
- [ ] **Context Consistency**: Are calls made from appropriate async/sync context?

### Red Flags:
- `await` used on known sync functions
- Missing `await` on known async functions  
- Mixing `asyncio.run()` calls within async functions

## WebSocket Handler Review

### Required Patterns:
- [ ] WebSocket acceptance is awaited: `await websocket.accept()`
- [ ] Message receiving is awaited: `await websocket.receive_json()`
- [ ] Message sending is awaited: `await websocket.send_json()`
- [ ] Proper error handling for disconnections
- [ ] Context cleanup in finally blocks

### Example Good Pattern:
```python
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    context = None
    
    try:
        context = await create_context(websocket.headers)
        
        while True:
            message = await websocket.receive_json()
            response = await process_message(context, message)
            await websocket.send_json(response)
            
    except WebSocketDisconnect:
        pass  # Normal disconnection
    finally:
        if context:
            await cleanup_context(context)
```

## Agent Execution Review

### Required Patterns:
- [ ] Agent creation is awaited: `agent = await create_agent()`
- [ ] Agent execution is awaited: `result = await agent.run()`
- [ ] Context management is async: `await context.initialize()`
- [ ] State tracking uses async methods: `await tracker.update_state()`

### Common Issues to Check:
- Agent factory methods not awaited
- Missing await on context operations
- Synchronous state updates in async agent flows

## Database Operation Review

### Transaction Patterns:
- [ ] Async context managers: `async with db.transaction():`
- [ ] All queries awaited: `await db.execute()`
- [ ] Connection management is async
- [ ] Error handling preserves transaction state

### Performance Considerations:
- [ ] Concurrent queries use `asyncio.gather()` when appropriate
- [ ] No unnecessary sequential waits
- [ ] Connection pooling used correctly

## Error Handling Review

### Async Exception Patterns:
- [ ] Exceptions caught at appropriate async level
- [ ] Error logging uses async methods when available
- [ ] Resource cleanup in finally blocks uses await
- [ ] Exception chaining preserves original async context

### Anti-patterns to Flag:
```python
# ❌ BAD - Sync exception handling in async context
async def bad_error_handling():
    try:
        await async_operation()
    except Exception as e:
        print(f"Error: {e}")  # Should be async logging
        
# ✅ GOOD - Proper async error handling  
async def good_error_handling():
    try:
        await async_operation()
    except Exception as e:
        await async_logger.error(f"Error: {e}")
```

## Testing Review

### Async Test Patterns:
- [ ] Test functions are declared `async` when testing async code
- [ ] Test framework supports async (pytest-asyncio)
- [ ] Mocks handle async patterns correctly
- [ ] Integration tests use real async services

## Performance Review

### Concurrency Opportunities:
- [ ] Independent async operations use concurrent execution
- [ ] No unnecessary sequential awaits
- [ ] Proper use of `asyncio.gather()`, `asyncio.create_task()`

### Blocking Operation Detection:
- [ ] No `time.sleep()` in async functions (should be `asyncio.sleep()`)
- [ ] No sync HTTP calls (`requests`) in async functions (should be `httpx` or `aiohttp`)
- [ ] No sync file operations in async functions (should be `aiofiles`)

## Documentation Review

### Required Documentation:
- [ ] Function docstrings mention async behavior
- [ ] Type hints accurately reflect async/sync nature
- [ ] Usage examples show correct await patterns
- [ ] Breaking changes to function signatures are documented

## Final Checklist

### Before Approval:
- [ ] All async functions properly awaited
- [ ] No sync functions incorrectly awaited  
- [ ] Error handling appropriate for async context
- [ ] Performance implications considered
- [ ] Tests cover async behavior
- [ ] Documentation updated for any signature changes

### Red Light Conditions (Block PR):
- SyntaxError due to await in sync function
- Missing await on async function calls in critical paths
- WebSocket handlers not properly async
- Agent execution patterns broken
- Database transactions not properly async

### Yellow Light Conditions (Request Changes):
- Inconsistent async patterns
- Performance opportunities missed
- Error handling could be improved
- Documentation insufficient

### Green Light Conditions (Approve):
- All async patterns consistent and correct
- Good error handling practices
- Performance considerations addressed
- Comprehensive test coverage
- Clear documentation
"""

        return TrainingModule(
            title="Async Pattern Code Review Checklist",
            description="Comprehensive checklist for reviewing async/await code changes",
            level=TrainingLevel.INTERMEDIATE,
            format=TrainingFormat.CHECKLIST,
            estimated_duration_minutes=20,
            learning_objectives=[
                "Systematically review async pattern implementations",
                "Identify common async/await mistakes in code review",
                "Ensure consistent async patterns across codebase",
                "Verify proper error handling in async contexts"
            ],
            content=content,
            examples=[],
            common_mistakes=[],
            best_practices=[
                "Review function signatures first",
                "Check every await usage",
                "Verify error handling patterns",
                "Test async code paths",
                "Document breaking changes"
            ],
            assessment_questions=[],
            prerequisites=["Async/Await Fundamentals", "Advanced Async Patterns"]
        )
    
    def generate_decision_tree(self) -> TrainingModule:
        """Generate async pattern decision tree"""
        content = """
# Async Pattern Decision Tree

Use this decision tree when implementing new functions or modifying existing ones.

## Decision Flow

### 1. Does your function need to call any async operations?

**Async operations include:**
- Database queries (`await db.execute()`)
- HTTP requests with async clients (`await client.get()`)
- WebSocket operations (`await websocket.send()`)
- File I/O with aiofiles (`await aiofiles.open()`)
- Sleep operations (`await asyncio.sleep()`)
- Other async functions (`await some_async_func()`)

```
Does your function call any async operations?
├── YES → Go to Step 2
└── NO → Make function SYNC (regular function)
```

### 2. Will your function be called from async contexts?

**Async contexts include:**
- WebSocket handlers
- Agent execution functions
- Database operation handlers
- Other async functions

```
Will your function be called from async contexts?
├── YES → Make function ASYNC
└── NO → Go to Step 3
```

### 3. Do you need the function to be awaitable for future extensibility?

**Consider making async if:**
- Function might need async operations in the future
- Function is part of an interface that other async functions implement
- Function is a public API that should be consistent with other async functions

```
Should function be awaitable for consistency/future?
├── YES → Make function ASYNC
└── NO → Make function SYNC
```

## Implementation Patterns

### Pattern 1: Sync Function (No async operations)
```python
def calculate_metrics(data: List[Dict]) -> MetricsResult:
    # Pure computation, no I/O
    total = sum(item['value'] for item in data)
    average = total / len(data) if data else 0
    
    return MetricsResult(
        total=total,
        average=average,
        count=len(data)
    )

# Usage:
result = calculate_metrics(user_data)  # No await needed
```

### Pattern 2: Async Function (Has async operations)
```python
async def fetch_user_metrics(user_id: str) -> MetricsResult:
    # Async database operations
    user_data = await database.get_user_data(user_id)
    recent_activity = await database.get_recent_activity(user_id, days=30)
    
    # Sync computation
    metrics = calculate_metrics(user_data + recent_activity)
    
    # Async save operation
    await database.save_metrics(user_id, metrics)
    
    return metrics

# Usage:
result = await fetch_user_metrics("user123")  # Must use await
```

### Pattern 3: Mixed Sync/Async (Conditional async)
When you have operations that might be sync or async:

```python
async def process_data(data: List[Dict], save_to_db: bool = True) -> ProcessResult:
    # Always sync processing
    processed = [process_item(item) for item in data]
    
    result = ProcessResult(processed_data=processed)
    
    # Conditionally async operation
    if save_to_db:
        await database.save_results(result)  # Async
    
    return result

# Usage - always use await even if async operations are conditional:
result = await process_data(data, save_to_db=False)
```

## Common Decision Points

### WebSocket Functions
```
Creating a WebSocket handler?
└── YES → ALWAYS make it async
    └── WebSocket operations are inherently async
```

**Example:**
```python
# ✅ CORRECT
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    # ... rest of handler
```

### Database Functions
```
Function accesses database?
├── YES → Make function ASYNC
│   └── Database operations should be awaitable
└── NO → Can be SYNC
```

**Example:**
```python
# ✅ CORRECT
async def get_user_profile(user_id: str) -> UserProfile:
    user = await database.get_user(user_id)
    profile = await database.get_profile(user.profile_id)
    return profile
```

### Agent Functions
```
Function involved in agent execution?
├── YES → Make function ASYNC
│   └── Agent operations are async by design
└── NO → Can be SYNC
```

**Example:**
```python
# ✅ CORRECT  
async def execute_agent(context: UserExecutionContext) -> AgentResult:
    agent = await agent_factory.create(context.agent_type)
    result = await agent.run(context)
    return result
```

### Utility Functions
```
Pure utility function (no I/O, no external calls)?
├── YES → Make function SYNC
│   └── No async operations needed
└── NO → Consider async needs
```

**Example:**
```python
# ✅ CORRECT - Pure utility, no I/O
def format_currency(amount: float, currency: str = "USD") -> str:
    return f"{amount:.2f} {currency}"

# Usage:
formatted = format_currency(123.45)  # No await
```

## Troubleshooting Guide

### Issue: "coroutine was never awaited"
**Diagnosis Tree:**
```
Got "coroutine was never awaited" warning?
├── Function call missing await?
│   └── Solution: Add await keyword
├── Function called from sync context?
│   └── Solution: Use asyncio.run() or make caller async
└── Function should be sync?
    └── Solution: Remove async from function definition
```

### Issue: "await outside async function"
**Diagnosis Tree:**
```
Got "await outside async function" error?
├── Function needs to be async?
│   └── Solution: Add async keyword to function definition
├── Called from sync context?
│   └── Solution: Use asyncio.run() to call async function
└── Operation should be sync?
    └── Solution: Remove await and use sync version
```

### Issue: Performance Problems
**Diagnosis Tree:**
```
Async function running slowly?
├── Sequential awaits that could be concurrent?
│   └── Solution: Use asyncio.gather() or create_task()
├── Blocking operations in async function?
│   └── Solution: Replace with async alternatives
└── Too many context switches?
    └── Solution: Batch operations or use sync approach
```

## Quick Reference

### Make Function ASYNC if:
- ✅ Calls any async operations (database, HTTP, WebSocket, file I/O)
- ✅ Called from async contexts (WebSocket handlers, other async functions)
- ✅ Part of agent execution pipeline
- ✅ Needs to be consistent with interface that has other async functions

### Keep Function SYNC if:
- ✅ Pure computation, no I/O operations
- ✅ Only called from sync contexts
- ✅ Performance-critical code that doesn't need async
- ✅ Simple utility functions

### Always Use ASYNC for:
- ✅ WebSocket handlers and operations
- ✅ Database queries and transactions  
- ✅ Agent creation and execution
- ✅ HTTP API calls
- ✅ File I/O operations
- ✅ Time-based operations (sleep, delays)

### Red Flags (Always Wrong):
- ❌ `await` in non-async function
- ❌ Missing `await` on async function calls
- ❌ `asyncio.run()` inside async function
- ❌ Sync I/O operations in async functions
- ❌ `time.sleep()` in async functions (use `asyncio.sleep()`)
"""

        return TrainingModule(
            title="Async Pattern Decision Tree",
            description="Step-by-step decision guide for choosing sync vs async patterns",
            level=TrainingLevel.INTERMEDIATE,
            format=TrainingFormat.DECISION_TREE,
            estimated_duration_minutes=15,
            learning_objectives=[
                "Systematically decide when to use async vs sync",
                "Follow consistent decision-making process",
                "Avoid common async/sync pattern mistakes",
                "Troubleshoot async pattern issues"
            ],
            content=content,
            examples=[],
            common_mistakes=[],
            best_practices=[
                "Follow the decision tree systematically",
                "Consider future extensibility needs",
                "Always be consistent with interface patterns",
                "Document your async/sync decisions"
            ],
            assessment_questions=[],
            prerequisites=["Async/Await Fundamentals"]
        )
    
    def generate_all_modules(self) -> List[TrainingModule]:
        """Generate all training modules"""
        modules = [
            self.generate_beginner_module(),
            self.generate_intermediate_module(),
            self.generate_code_review_checklist(),
            self.generate_decision_tree()
        ]
        
        self.modules.extend(modules)
        return modules


class DeveloperTrainingGenerator:
    """Main generator for developer training materials"""
    
    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or Path('docs/developer_training')
        self.async_generator = AsyncPatternTrainingGenerator()
        
    def generate_all_training_materials(self) -> List[TrainingModule]:
        """Generate all training materials"""
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate async pattern training
        modules = self.async_generator.generate_all_modules()
        
        # Save modules to files
        for module in modules:
            self._save_module_to_file(module)
        
        # Generate index file
        self._generate_training_index(modules)
        
        # Generate assessment system
        self._generate_assessment_system(modules)
        
        return modules
    
    def _save_module_to_file(self, module: TrainingModule) -> None:
        """Save training module to file"""
        filename = module.title.lower().replace(' ', '_').replace('/', '_') + '.md'
        file_path = self.output_dir / filename
        
        content = f"""# {module.title}

**Level:** {module.level.value.title()}  
**Format:** {module.format.value.title()}  
**Duration:** {module.estimated_duration_minutes} minutes  
**Prerequisites:** {', '.join(module.prerequisites) if module.prerequisites else 'None'}

## Learning Objectives
{chr(10).join(f"- {obj}" for obj in module.learning_objectives)}

## Description
{module.description}

{module.content}

## Examples

{chr(10).join(f"### {ex['title']}" + chr(10) + f"```python" + chr(10) + ex['code'] + chr(10) + "```" + chr(10) for ex in module.examples)}

## Common Mistakes

{chr(10).join(f"### {mistake['mistake']}" + chr(10) + f"**Example:** `{mistake['example']}`" + chr(10) + f"**Fix:** {mistake['fix']}" + chr(10) for mistake in module.common_mistakes)}

## Best Practices

{chr(10).join(f"- {practice}" for practice in module.best_practices)}

## Assessment Questions

{chr(10).join(f"{i+1}. {q['question']}" + chr(10) + chr(10).join(f"   {chr(ord('A') + j)}. {opt}" for j, opt in enumerate(q['options'])) + chr(10) + f"   **Answer:** {chr(ord('A') + q['correct'])} - {q['explanation']}" + chr(10) for i, q in enumerate(module.assessment_questions))}

---
*Generated by Netra Developer Training System*
"""
        
        with open(file_path, 'w') as f:
            f.write(content)
    
    def _generate_training_index(self, modules: List[TrainingModule]) -> None:
        """Generate training index file"""
        index_content = f"""# Netra Developer Training Index

Welcome to the Netra Developer Training System. This comprehensive training program ensures all developers understand critical async/await patterns and best practices.

## Training Path

Follow this recommended learning path:

"""
        
        # Group modules by level
        by_level = {}
        for module in modules:
            level = module.level.value
            if level not in by_level:
                by_level[level] = []
            by_level[level].append(module)
        
        level_order = ['beginner', 'intermediate', 'advanced', 'expert']
        
        for level in level_order:
            if level in by_level:
                index_content += f"\n### {level.title()} Level\n\n"
                for module in by_level[level]:
                    filename = module.title.lower().replace(' ', '_').replace('/', '_') + '.md'
                    index_content += f"- **[{module.title}]({filename})** ({module.estimated_duration_minutes} min)\n"
                    index_content += f"  {module.description}\n\n"
        
        index_content += f"""
## Quick Reference

### For Code Reviews
- [Async Pattern Code Review Checklist](async_pattern_code_review_checklist.md)

### For Implementation Decisions  
- [Async Pattern Decision Tree](async_pattern_decision_tree.md)

### For Beginners
- [Async/Await Fundamentals](async_await_fundamentals_for_netra_platform.md)

### For Advanced Patterns
- [Advanced Async Patterns](advanced_async_patterns_in_netra_architecture.md)

## Training Statistics

- **Total Modules:** {len(modules)}
- **Estimated Total Time:** {sum(m.estimated_duration_minutes for m in modules)} minutes
- **Assessment Questions:** {sum(len(m.assessment_questions) for m in modules)}

## Compliance Requirements

All developers working on async-related code must complete:
1. Beginner level training (mandatory)
2. At least one intermediate module relevant to their work area
3. Pass assessment with 80% or higher

## Getting Started

1. Start with [Async/Await Fundamentals](async_await_fundamentals_for_netra_platform.md)
2. Complete the assessment questions
3. Progress to intermediate materials based on your role:
   - **WebSocket Development:** Focus on Advanced Async Patterns
   - **Code Review:** Complete the Code Review Checklist module
   - **Architecture Decisions:** Study the Decision Tree module

---
*Generated by Netra Developer Training System*
"""
        
        index_path = self.output_dir / 'README.md'
        with open(index_path, 'w') as f:
            f.write(index_content)
    
    def _generate_assessment_system(self, modules: List[TrainingModule]) -> None:
        """Generate assessment system"""
        assessment_data = {
            'modules': [],
            'total_questions': 0,
            'passing_score': 0.8,
            'requirements': {
                'beginner_required': True,
                'intermediate_modules_required': 1,
                'minimum_total_score': 0.8
            }
        }
        
        for module in modules:
            if module.assessment_questions:
                module_data = {
                    'title': module.title,
                    'level': module.level.value,
                    'questions': module.assessment_questions,
                    'question_count': len(module.assessment_questions)
                }
                assessment_data['modules'].append(module_data)
                assessment_data['total_questions'] += len(module.assessment_questions)
        
        assessment_path = self.output_dir / 'assessment_system.json'
        with open(assessment_path, 'w') as f:
            json.dump(assessment_data, f, indent=2)
        
        # Generate assessment script
        assessment_script = """#!/usr/bin/env python3
\"\"\"
Developer Training Assessment System
Run assessments and track completion
\"\"\"

import json
import random
from pathlib import Path

def load_assessment_data():
    \"\"\"Load assessment data\"\"\"
    assessment_path = Path(__file__).parent / 'assessment_system.json'
    with open(assessment_path, 'r') as f:
        return json.load(f)

def run_module_assessment(module_data):
    \"\"\"Run assessment for a single module\"\"\"
    print(f"\\n=== {module_data['title']} Assessment ===")
    print(f"Level: {module_data['level']}")
    print(f"Questions: {module_data['question_count']}")
    print()
    
    questions = module_data['questions'].copy()
    random.shuffle(questions)
    
    correct = 0
    total = len(questions)
    
    for i, question in enumerate(questions):
        print(f"Question {i+1}/{total}:")
        print(question['question'])
        print()
        
        for j, option in enumerate(question['options']):
            print(f"  {chr(ord('A') + j)}. {option}")
        
        while True:
            answer = input("\\nYour answer (A, B, C, D): ").upper()
            if answer in ['A', 'B', 'C', 'D']:
                answer_index = ord(answer) - ord('A')
                break
            print("Please enter A, B, C, or D")
        
        if answer_index == question['correct']:
            print("✅ Correct!")
            correct += 1
        else:
            correct_answer = chr(ord('A') + question['correct'])
            print(f"❌ Incorrect. The correct answer is {correct_answer}")
            print(f"Explanation: {question['explanation']}")
        
        print()
    
    score = correct / total
    print(f"Final Score: {correct}/{total} ({score:.1%})")
    
    return score

def main():
    \"\"\"Main assessment runner\"\"\"
    data = load_assessment_data()
    
    print("Netra Developer Training Assessment System")
    print("=" * 50)
    
    available_modules = data['modules']
    
    print("\\nAvailable assessments:")
    for i, module in enumerate(available_modules):
        print(f"{i+1}. {module['title']} ({module['level']}) - {module['question_count']} questions")
    
    print("\\nSelect assessment (enter number):")
    choice = int(input()) - 1
    
    if 0 <= choice < len(available_modules):
        score = run_module_assessment(available_modules[choice])
        
        passing_score = data['passing_score']
        if score >= passing_score:
            print(f"\\n🎉 PASSED! You scored {score:.1%} (required: {passing_score:.1%})")
        else:
            print(f"\\n📚 Study more. You scored {score:.1%} (required: {passing_score:.1%})")
    else:
        print("Invalid selection")

if __name__ == "__main__":
    main()
"""
        
        script_path = self.output_dir / 'run_assessment.py'
        with open(script_path, 'w') as f:
            f.write(assessment_script)


def create_argument_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser"""
    parser = argparse.ArgumentParser(
        description="Developer Training Generator - Creates comprehensive training materials"
    )
    
    # Main actions
    parser.add_argument('--create-materials', action='store_true',
                       help='Create all training materials')
    parser.add_argument('--output-dir', type=str, default='docs/developer_training',
                       help='Output directory for training materials')
    
    # Specific module generation
    parser.add_argument('--beginner-only', action='store_true',
                       help='Generate only beginner materials')
    parser.add_argument('--intermediate-only', action='store_true',
                       help='Generate only intermediate materials')
    parser.add_argument('--checklist-only', action='store_true',
                       help='Generate only code review checklist')
    parser.add_argument('--decision-tree-only', action='store_true',
                       help='Generate only decision tree')
    
    # Output format options
    parser.add_argument('--json-summary', action='store_true',
                       help='Output summary in JSON format')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    return parser


def main() -> int:
    """Main training generator orchestrator"""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    generator = DeveloperTrainingGenerator(output_dir)
    
    if args.create_materials:
        print("Creating comprehensive developer training materials...")
        modules = generator.generate_all_training_materials()
        
        print(f"✅ Generated {len(modules)} training modules")
        print(f"📁 Output directory: {output_dir}")
        print(f"📚 Total estimated training time: {sum(m.estimated_duration_minutes for m in modules)} minutes")
        print(f"❓ Total assessment questions: {sum(len(m.assessment_questions) for m in modules)}")
        
        if args.json_summary:
            summary = {
                'modules_generated': len(modules),
                'output_directory': str(output_dir),
                'total_duration_minutes': sum(m.estimated_duration_minutes for m in modules),
                'total_questions': sum(len(m.assessment_questions) for m in modules),
                'modules': [
                    {
                        'title': m.title,
                        'level': m.level.value,
                        'duration': m.estimated_duration_minutes,
                        'questions': len(m.assessment_questions)
                    } for m in modules
                ]
            }
            print("\nJSON Summary:")
            print(json.dumps(summary, indent=2))
        
        return 0
    
    # Handle specific module generation
    async_generator = AsyncPatternTrainingGenerator()
    modules_to_generate = []
    
    if args.beginner_only:
        modules_to_generate.append(async_generator.generate_beginner_module())
    if args.intermediate_only:
        modules_to_generate.append(async_generator.generate_intermediate_module())
    if args.checklist_only:
        modules_to_generate.append(async_generator.generate_code_review_checklist())
    if args.decision_tree_only:
        modules_to_generate.append(async_generator.generate_decision_tree())
    
    if modules_to_generate:
        output_dir.mkdir(parents=True, exist_ok=True)
        for module in modules_to_generate:
            generator._save_module_to_file(module)
        
        print(f"✅ Generated {len(modules_to_generate)} specific modules")
        return 0
    
    # Default: show help
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())