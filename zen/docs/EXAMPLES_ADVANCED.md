# Advanced ZEN Examples and Patterns

This document provides advanced patterns and comprehensive examples for Zen Orchestrator workflows.

## Configuration Pattern Library

### 1. Data Pipeline Pattern

**Use Case**: Multi-stage data processing with validation

```json
{
  "// Pattern": "Sequential data pipeline with quality gates",
  "instances": [
    {
      "name": "data-ingester",
      "command": "/ingest-data; Validate data sources and load raw data; Check for completeness and format compliance",
      "description": "Ingests and validates raw data sources",
      "max_tokens_per_command": 8000,
      "allowed_tools": ["Read", "Write", "Bash", "Task"],
      "session_id": "data_pipeline",
      "pre_commands": ["Set context: Data ingestion and validation phase"]
    },
    {
      "name": "data-transformer",
      "command": "/transform-data; Clean, normalize, and transform data; Apply business rules and data quality checks",
      "description": "Transforms and cleans ingested data",
      "max_tokens_per_command": 12000,
      "allowed_tools": ["Read", "Write", "Edit", "Task"],
      "session_id": "data_pipeline",
      "pre_commands": ["Set context: Data transformation and cleaning phase"]
    },
    {
      "name": "data-validator",
      "command": "/validate-pipeline; Verify data quality and integrity; Generate quality metrics and alerts",
      "description": "Validates final data quality",
      "max_tokens_per_command": 10000,
      "allowed_tools": ["Read", "Write", "Task"],
      "session_id": "data_pipeline",
      "pre_commands": ["Set context: Final data validation and quality assurance"]
    }
  ]
}
```

### 2. Research and Analysis Pattern

**Use Case**: Comprehensive research with multiple perspectives

```json
{
  "// Pattern": "Parallel research with synthesis",
  "instances": [
    {
      "name": "academic-researcher",
      "command": "/research-academic; Find peer-reviewed papers and academic sources; Focus on recent publications and authoritative sources",
      "description": "Conducts academic literature research",
      "max_tokens_per_command": 15000,
      "allowed_tools": ["WebSearch", "WebFetch", "Write", "Task"],
      "session_id": "academic_research",
      "pre_commands": ["Set context: Academic research with focus on peer-reviewed sources"]
    },
    {
      "name": "industry-analyst",
      "command": "/research-industry; Analyze industry reports, market trends, and business applications; Focus on practical implementations",
      "description": "Analyzes industry trends and applications",
      "max_tokens_per_command": 15000,
      "allowed_tools": ["WebSearch", "WebFetch", "Write", "Task"],
      "session_id": "industry_research",
      "pre_commands": ["Set context: Industry analysis with focus on market trends and applications"]
    },
    {
      "name": "technical-evaluator",
      "command": "/evaluate-technical; Assess technical feasibility, implementation challenges, and solution architecture",
      "description": "Evaluates technical aspects and feasibility",
      "max_tokens_per_command": 12000,
      "allowed_tools": ["Read", "Write", "Task"],
      "session_id": "technical_evaluation",
      "pre_commands": ["Set context: Technical evaluation and feasibility analysis"]
    },
    {
      "name": "research-synthesizer",
      "command": "/synthesize-research; Combine findings from academic, industry, and technical research; Create comprehensive analysis with recommendations",
      "description": "Synthesizes all research findings",
      "max_tokens_per_command": 20000,
      "allowed_tools": ["Read", "Write", "Edit", "MultiEdit", "Task"],
      "session_id": "synthesis",
      "pre_commands": ["Set context: Research synthesis combining academic, industry, and technical perspectives"]
    }
  ]
}
```

### 3. Quality Assurance Pattern

**Use Case**: Multi-layered quality validation

```json
{
  "// Pattern": "Comprehensive quality assurance with multiple validation layers",
  "instances": [
    {
      "name": "content-reviewer",
      "command": "/review-content; Check for accuracy, completeness, and clarity; Verify facts and sources",
      "description": "Reviews content for accuracy and completeness",
      "max_tokens_per_command": 12000,
      "allowed_tools": ["Read", "Write", "WebSearch", "Task"],
      "session_id": "content_review",
      "pre_commands": ["Set context: Content accuracy and completeness review"]
    },
    {
      "name": "style-editor",
      "command": "/edit-style; Improve writing style, grammar, and readability; Ensure consistent tone and voice",
      "description": "Edits for style, grammar, and readability",
      "max_tokens_per_command": 10000,
      "allowed_tools": ["Read", "Edit", "MultiEdit", "Task"],
      "session_id": "style_editing",
      "pre_commands": ["Set context: Style editing and language improvement"]
    },
    {
      "name": "technical-validator",
      "command": "/validate-technical; Verify technical accuracy, test procedures, and implementation details",
      "description": "Validates technical accuracy and procedures",
      "max_tokens_per_command": 14000,
      "allowed_tools": ["Read", "Write", "Bash", "Task"],
      "session_id": "technical_validation",
      "pre_commands": ["Set context: Technical accuracy and procedure validation"]
    },
    {
      "name": "final-approver",
      "command": "/final-approval; Conduct final review integrating all feedback; Make final recommendations and approve for publication",
      "description": "Conducts final integrated review and approval",
      "max_tokens_per_command": 16000,
      "allowed_tools": ["Read", "Write", "Edit", "Task"],
      "session_id": "final_approval",
      "pre_commands": ["Set context: Final integrated review and publication approval"]
    }
  ]
}
```

## Advanced Configuration Techniques

### Session Management Strategies

#### 1. Isolated Sessions (Parallel Processing)
Each agent works independently:
```json
"session_id": "unique_session_name"
```

#### 2. Shared Sessions (Sequential Building)
Agents build on each other's work:
```json
"session_id": "shared_workflow_session"
```

#### 3. Mixed Sessions (Hybrid Approach)
Some agents share context, others work independently:
```json
{
  "instances": [
    {"session_id": "research_phase"},
    {"session_id": "research_phase"},
    {"session_id": "analysis_phase"},
    {"session_id": "final_synthesis"}
  ]
}
```

### Token Allocation Strategies

#### 1. Progressive Allocation
Start with data collection, increase for analysis:
```json
{
  "data_collector": {"max_tokens_per_command": 8000},
  "analyzer": {"max_tokens_per_command": 12000},
  "synthesizer": {"max_tokens_per_command": 16000},
  "reporter": {"max_tokens_per_command": 20000}
}
```

#### 2. Balanced Allocation
Equal distribution for parallel processing:
```json
{
  "all_agents": {"max_tokens_per_command": 12000}
}
```

#### 3. Priority-Based Allocation
More tokens for critical agents:
```json
{
  "critical_agent": {"max_tokens_per_command": 20000},
  "supporting_agents": {"max_tokens_per_command": 8000}
}
```

### Tool Permission Optimization

#### Minimal Permissions
Grant only necessary tools:
```json
{
  "analyzer": {"allowed_tools": ["Read", "Task"]},
  "writer": {"allowed_tools": ["Read", "Write", "Edit"]},
  "system_agent": {"allowed_tools": ["Bash", "Read", "Write"]}
}
```

#### Role-Based Permissions
Tools aligned with agent roles:
```json
{
  "researcher": {"allowed_tools": ["WebSearch", "WebFetch", "Write"]},
  "developer": {"allowed_tools": ["Read", "Write", "Edit", "Bash"]},
  "analyst": {"allowed_tools": ["Read", "Grep", "Glob", "Write"]}
}
```

## Performance Optimization Patterns

### 1. Staged Execution
Break complex workflows into stages:

```bash
# Stage 1: Data Collection
python zen_orchestrator.py --config stage1_collection.json

# Stage 2: Analysis
python zen_orchestrator.py --config stage2_analysis.json

# Stage 3: Reporting
python zen_orchestrator.py --config stage3_reporting.json
```

### 2. Conditional Workflows
Use budget controls for conditional execution:

```bash
# Light analysis (budget-constrained)
python zen_orchestrator.py --config analysis.json --overall-token-budget 25000

# Deep analysis (full budget)
python zen_orchestrator.py --config analysis.json --overall-token-budget 75000
```

### 3. Incremental Processing
Process data in batches:

```json
{
  "instances": [
    {
      "name": "batch-processor-1",
      "command": "/process-batch --batch=1-100",
      "description": "Process records 1-100"
    },
    {
      "name": "batch-processor-2",
      "command": "/process-batch --batch=101-200",
      "description": "Process records 101-200"
    }
  ]
}
```

## Error Handling and Recovery

### 1. Validation Checkpoints
Include validation at each stage:

```json
{
  "name": "validator",
  "command": "/validate-stage; Check completion status of previous stage; Verify data integrity before proceeding",
  "description": "Validates stage completion and data integrity"
}
```

### 2. Fallback Strategies
Define fallback approaches:

```json
{
  "name": "primary-processor",
  "command": "/process-primary; If fails, log error and trigger fallback processing method",
  "description": "Primary processing with fallback strategy"
}
```

### 3. Recovery Procedures
Include recovery in workflows:

```json
{
  "name": "recovery-agent",
  "command": "/recover-state; Analyze failed operations; Implement recovery procedures; Resume from last checkpoint",
  "description": "Handles error recovery and state restoration"
}
```

## Industry-Specific Examples

### Software Development

```bash
# Complete development workflow
python zen_orchestrator.py --config examples/code_review.json
python zen_orchestrator.py --config examples/testing_workflow.json
python zen_orchestrator.py --config examples/debugging_workflow.json
```

### Data Science

```bash
# Research and analysis pipeline
python zen_orchestrator.py --config examples/data_analysis.json
```

### Content Marketing

```bash
# Content creation and optimization
python zen_orchestrator.py --config examples/content_creation.json
```

### System Administration

```bash
# Safe system changes
python zen_orchestrator.py --config examples/migration_workflow.json
```

## Best Practices Summary

### Configuration Design
1. **Start Simple**: Begin with 3-5 agents
2. **Single Responsibility**: Each agent has one clear purpose
3. **Logical Flow**: Design clear execution paths
4. **Validation Gates**: Include quality checks at each stage

### Resource Management
1. **Token Budgets**: Allocate based on expected complexity
2. **Tool Permissions**: Grant minimal necessary access
3. **Session Strategy**: Balance independence vs collaboration
4. **Monitoring**: Use status reports for optimization

### Quality Assurance
1. **Multiple Perspectives**: Use diverse analysis approaches
2. **Iterative Refinement**: Build validation into workflows
3. **Comprehensive Coverage**: Address all aspects of the task
4. **Final Synthesis**: Combine results intelligently

### Operational Excellence
1. **Documentation**: Comment configurations thoroughly
2. **Testing**: Use dry-run mode for validation
3. **Monitoring**: Track token usage and performance
4. **Optimization**: Continuously improve based on results

## Troubleshooting Common Patterns

### Issue: Agents Producing Inconsistent Results
**Solution**: Add detailed context in `pre_commands`

### Issue: High Token Usage
**Solutions**:
- Reduce `max_tokens_per_command`
- Use more focused agent commands
- Implement staged execution

### Issue: Slow Execution
**Solutions**:
- Increase parallelism with isolated sessions
- Optimize tool permissions
- Use conditional workflows

### Issue: Poor Result Quality
**Solutions**:
- Add validation agents
- Improve command specificity
- Include quality checkpoints

This advanced guide provides the patterns and techniques needed to create sophisticated, production-ready Zen Orchestrator workflows.