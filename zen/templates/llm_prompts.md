# Zen Orchestrator LLM Prompt Templates

This document provides templates and guidance for using LLMs to generate effective Zen Orchestrator configurations.

## Quick Start Template

```
I need help creating a Zen Orchestrator configuration for [YOUR USE CASE].

Zen Orchestrator is a multi-agent AI workflow tool that executes multiple AI instances in sequence or parallel to accomplish complex tasks. Each instance has:
- A specific command/task to execute
- Tool permissions (Read, Write, Edit, Bash, etc.)
- Token limits and session management
- Output format specifications

Please create a JSON configuration with 3-5 instances that will:
[DESCRIBE YOUR SPECIFIC GOAL IN DETAIL]

Include:
- Clear instance names that reflect their purpose
- Detailed commands that specify exactly what each instance should do
- Appropriate tool permissions for each task
- Reasonable token limits (5000-20000 based on complexity)
- Session management settings
- Pre-commands to set proper context

Format: Valid JSON that can be used directly with Zen Orchestrator
```

## Advanced Configuration Template

```
Create a comprehensive Zen Orchestrator configuration for [COMPLEX USE CASE].

## Context
Zen Orchestrator coordinates multiple specialized AI agents to complete complex workflows. Each agent:
- Has focused expertise and clear responsibilities
- Uses specific tools (Read, Write, Edit, MultiEdit, Bash, Grep, Glob, Task, WebSearch, WebFetch)
- Manages its own session context and token budget
- Can run sequentially or in parallel

## Requirements
Primary Goal: [DETAILED DESCRIPTION]
Success Criteria: [SPECIFIC MEASURABLE OUTCOMES]
Constraints: [TIME, RESOURCE, OR SCOPE LIMITATIONS]

## Workflow Design
Please design 4-7 specialized agents with:
1. **Logical Flow**: Clear sequence or parallel execution strategy
2. **Specialization**: Each agent has a distinct, focused role
3. **Integration**: Agents build on each other's work appropriately
4. **Validation**: Include quality checks and validation steps

## Configuration Specifications
- **Instance Names**: Use descriptive, role-based names (e.g., "security-analyzer", "test-generator")
- **Commands**: Detailed, specific instructions including expected inputs/outputs
- **Tools**: Minimal necessary permissions for each agent's role
- **Tokens**: 8000-20000 based on complexity (more for synthesis/reporting agents)
- **Sessions**: Separate sessions for different domains, shared where collaboration needed
- **Pre-commands**: Context-setting commands to focus each agent
- **Output Format**: stream-json for real-time feedback

## Best Practices to Include
- Start agents with clear context via pre-commands
- Use session management to maintain focus
- Allocate tokens based on expected output complexity
- Include validation and quality assurance steps
- Design for both success and failure scenarios

Format: Complete JSON configuration ready for immediate use
```

## Specialized Workflow Templates

### Code Analysis Workflow
```
Create a Zen Orchestrator configuration for comprehensive code analysis.

Goal: Analyze a codebase for [SECURITY/PERFORMANCE/QUALITY] issues
Scope: [SPECIFIC DIRECTORIES OR FILE TYPES]
Output: Detailed report with prioritized recommendations

Required Agents:
- Code scanner for automated issue detection
- Security specialist for vulnerability analysis
- Performance analyzer for optimization opportunities
- Quality assessor for maintainability review
- Report synthesizer for actionable recommendations

Include proper tool permissions, token allocation, and session management.
```

### Content Creation Workflow
```
Design a Zen Orchestrator configuration for creating [BLOG POST/DOCUMENTATION/TUTORIAL].

Topic: [SPECIFIC SUBJECT]
Audience: [TARGET READERS]
Length: [WORD COUNT OR SCOPE]
Style: [TECHNICAL/MARKETING/EDUCATIONAL]

Required Pipeline:
- Research specialist for gathering information
- Content strategist for structure and messaging
- Technical writer for content creation
- SEO optimizer for search optimization
- Quality editor for final review

Configure for sequential execution with proper context passing between agents.
```

### Testing and QA Workflow
```
Create a Zen Orchestrator configuration for comprehensive testing workflow.

Target: [APPLICATION/MODULE/FEATURE]
Test Types: [UNIT/INTEGRATION/E2E/PERFORMANCE]
Environment: [LOCAL/STAGING/CI/CD]

Required Components:
- Test executor for running test suites
- Failure analyzer for diagnosing issues
- Coverage analyst for gap identification
- Performance monitor for optimization
- Improvement planner for actionable roadmap

Include error handling, reporting, and continuous improvement focus.
```

## Configuration Optimization Templates

### Budget Optimization
```
I have a Zen Orchestrator workflow that's using too many tokens. Please optimize this configuration:

[PASTE YOUR CURRENT CONFIG]

Optimization Goals:
- Reduce token usage by 30-50%
- Maintain output quality
- Improve execution efficiency
- Better resource allocation

Please suggest:
- Token redistribution strategies
- Command optimization techniques
- Session management improvements
- Tool permission adjustments
```

### Performance Optimization
```
My Zen Orchestrator workflow is taking too long to complete. Please optimize for speed:

[PASTE YOUR CURRENT CONFIG]

Current Issues:
- [SPECIFIC PERFORMANCE PROBLEMS]
- [BOTTLENECKS IDENTIFIED]

Optimization Targets:
- Parallel execution where possible
- Reduced redundancy
- Streamlined commands
- Efficient tool usage

Maintain quality while improving execution time.
```

## Error Resolution Templates

### Debugging Template
```
My Zen Orchestrator configuration isn't working as expected. Please help debug:

**Configuration:**
[PASTE YOUR CONFIG]

**Expected Behavior:**
[WHAT SHOULD HAPPEN]

**Actual Behavior:**
[WHAT IS HAPPENING]

**Error Messages:**
[ANY ERROR OUTPUT]

**Environment:**
[SYSTEM DETAILS, FILE STRUCTURE, ETC.]

Please analyze and suggest fixes for:
- Configuration syntax issues
- Tool permission problems
- Command specification errors
- Session management issues
- Token allocation problems
```

## Best Practices for LLM Configuration Generation

### 1. Be Specific About Your Goals
- Define exact outcomes you want
- Specify input data and expected outputs
- Include success criteria and constraints

### 2. Provide Context About Your Environment
- Available files and directory structure
- System capabilities and limitations
- Integration requirements

### 3. Request Explanation and Rationale
- Ask for comments explaining design decisions
- Request alternative approaches where applicable
- Include best practices and common pitfalls

### 4. Iterate and Refine
- Start with basic configuration
- Test and gather feedback
- Request optimizations and improvements

### 5. Validate and Test
- Always test generated configurations
- Verify tool permissions and token limits
- Adjust based on actual performance

## Common Pitfalls to Avoid

1. **Overly Complex Commands**: Keep commands focused and specific
2. **Insufficient Context**: Provide enough background for quality generation
3. **Poor Token Allocation**: Consider the complexity of each agent's task
4. **Missing Error Handling**: Include validation and fallback strategies
5. **Unclear Dependencies**: Specify how agents should coordinate

## Example Request
```
Create a Zen Orchestrator configuration for analyzing a Python web application's security vulnerabilities.

Context:
- Flask application with 50+ files
- Database integration (PostgreSQL)
- Authentication system present
- API endpoints for user management
- Need comprehensive security audit

Goals:
- Identify SQL injection vulnerabilities
- Check authentication/authorization flaws
- Analyze input validation
- Review session management
- Generate prioritized security report

Constraints:
- Complete analysis in under 30 minutes
- Generate actionable recommendations
- Include code examples for fixes
- Format suitable for stakeholder review
```

This approach will generate a well-structured, comprehensive Zen Orchestrator configuration tailored to your specific security analysis needs.