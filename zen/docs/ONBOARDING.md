# Zen Orchestrator - Onboarding Guide

Welcome to Zen Orchestrator! This guide will get you up and running with multi-agent AI workflows in minutes.

## What is Zen Orchestrator?

Zen Orchestrator is a powerful tool for coordinating multiple AI agents to complete complex tasks. Instead of struggling with a single AI conversation, you can create specialized agents that work together efficiently.

**Key Benefits:**
- **Parallel Processing**: Multiple agents work simultaneously
- **Specialized Expertise**: Each agent focuses on specific tasks
- **Token Efficiency**: Smart token allocation across agents
- **Quality Results**: Multi-stage validation and synthesis
- **Real-time Monitoring**: Live progress tracking and cost management

## Quick Start (5 Minutes)

### 1. Install and Setup

```bash
# Install Zen Orchestrator
pip install zen-orchestrator

# Verify installation
python zen_orchestrator.py --help
```

### 2. Explore Built-in Examples

```bash
# See what's available
python zen_orchestrator.py --list-examples

# Output:
# Available Example Configurations:
# code_review        - Code Review
# content_creation   - Content Creation
# data_analysis      - Data Analysis
# debugging_workflow - Debugging Workflow
# migration_workflow - Migration Workflow
# testing_workflow   - Testing Workflow
```

### 3. Try Your First Workflow

Let's start with a simple code review:

```bash
# Generate the configuration to see what it looks like
python zen_orchestrator.py --generate-example code_review

# Use it directly on your project
python zen_orchestrator.py --config examples/code_review.json --workspace ~/my-project

# Or create a custom version
python zen_orchestrator.py --generate-example code_review > my_code_review.json
# Edit my_code_review.json as needed
python zen_orchestrator.py --config my_code_review.json --workspace ~/my-project
```

### 4. Monitor Progress

Watch as your agents work:

```
╔═══ STATUS REPORT [14:25:10] ═══╗
║ Total: 5 instances
║ Running: 3, Completed: 2, Failed: 0
║ Tokens: 32.1K total | Tools: 15
║ 💰 Cost: $0.0642 total
║
║ TOKEN BUDGET STATUS
║ Overall: [████████████----] 75% 32.1K/43.0K
║
║  Status   Name              Duration  Tokens
║  ──────── ─────────────────  ──────── ──────
║  ✅        security-reviewer  2m15s    8.5K
║  ✅        performance-analyzer 1m42s  7.2K
║  🏃        architecture-reviewer 1m18s 6.5K
║  🏃        test-coverage-analyst 0m45s 4.8K
║  ⏳        quality-synthesizer  queued  0K
╚════════════════════════════════════════════╝
```

## Creating Your First Custom Configuration

### Step 1: Get the LLM Template

```bash
python zen_orchestrator.py --show-prompt-template > prompt_template.txt
```

### Step 2: Customize the Template

Edit the template with your specific needs:

```
I need help creating a Zen Orchestrator configuration for analyzing customer feedback data.

Context:
- CSV files with 10,000+ customer reviews
- Need sentiment analysis and trend identification
- Want actionable business insights
- Must complete analysis in under 20 minutes

Goals:
- Process all feedback files
- Identify sentiment patterns
- Extract key themes and issues
- Generate executive summary with recommendations

Please create a JSON configuration with 4-5 specialized agents...
```

### Step 3: Generate with AI

1. Copy your customized prompt
2. Paste it into ChatGPT, Claude, or your preferred LLM
3. Save the generated JSON as `customer_feedback.json`
4. Run: `python zen_orchestrator.py --config customer_feedback.json`

## Understanding Configuration Structure

Every Zen configuration has the same basic structure:

```json
{
  "// Description": "What this workflow accomplishes",
  "// Use Case": "When to use this configuration",

  "instances": [
    {
      "name": "agent-role-name",
      "command": "Detailed task description with specific instructions",
      "description": "Brief summary of what this agent does",
      "permission_mode": "bypassPermissions",
      "output_format": "stream-json",
      "max_tokens_per_command": 12000,
      "allowed_tools": ["Read", "Write", "Edit", "Task"],
      "session_id": "unique_session_name",
      "clear_history": false,
      "compact_history": true,
      "pre_commands": [
        "Set context for this specific agent",
        "Define focus areas and expectations"
      ]
    }
  ]
}
```

### Key Configuration Elements

| Element | Purpose | Best Practice |
|---------|---------|---------------|
| `name` | Agent identifier | Use descriptive, role-based names |
| `command` | Task specification | Be specific and detailed |
| `max_tokens_per_command` | Token budget | Allocate based on complexity |
| `allowed_tools` | Tool permissions | Grant minimal necessary tools |
| `session_id` | Context management | Use separate sessions for different domains |
| `pre_commands` | Context setting | Always set clear context before main task |

## Common Patterns and Best Practices

### 1. Sequential Workflows

For tasks that build on each other:

```json
{
  "instances": [
    {
      "name": "researcher",
      "command": "Gather information...",
      "session_id": "research_session"
    },
    {
      "name": "analyzer",
      "command": "Analyze the research findings...",
      "session_id": "analysis_session"
    },
    {
      "name": "reporter",
      "command": "Create comprehensive report...",
      "session_id": "reporting_session"
    }
  ]
}
```

### 2. Parallel Analysis

For independent analysis tasks:

```json
{
  "instances": [
    {
      "name": "security-analyst",
      "command": "Analyze security aspects...",
      "session_id": "security_session"
    },
    {
      "name": "performance-analyst",
      "command": "Analyze performance aspects...",
      "session_id": "performance_session"
    },
    {
      "name": "synthesizer",
      "command": "Combine all analysis results...",
      "session_id": "synthesis_session"
    }
  ]
}
```

### 3. Token Allocation Strategy

Distribute tokens based on expected output complexity:

- **Data Collection**: 5,000-8,000 tokens
- **Analysis**: 10,000-15,000 tokens
- **Synthesis/Reporting**: 15,000-20,000 tokens
- **Simple Tasks**: 5,000-8,000 tokens

### 4. Tool Permission Guidelines

Grant minimal necessary tools:

- **Read, Glob, Grep**: For analysis tasks
- **Write, Edit**: For content creation
- **Bash**: For system operations
- **WebSearch, WebFetch**: For research tasks
- **Task**: For complex orchestration

## Advanced Features

### Budget Management

Set overall and per-command budgets:

```bash
# Set overall budget
python zen_orchestrator.py --config my_config.json --overall-token-budget 50000

# Set per-command budgets
python zen_orchestrator.py --config my_config.json \
  --command-budget "/analyze=15000" \
  --command-budget "/generate-report=20000"

# Budget enforcement
python zen_orchestrator.py --config my_config.json \
  --budget-enforcement-mode block  # or "warn"
```

### Scheduling

Schedule workflows to run later:

```bash
# Start in 2 hours
python zen_orchestrator.py --config my_config.json --start-at "2h"

# Start at specific time
python zen_orchestrator.py --config my_config.json --start-at "14:30"

# Start in 30 minutes
python zen_orchestrator.py --config my_config.json --start-at "30m"
```

### Dry Run Testing

Test configurations without execution:

```bash
python zen_orchestrator.py --config my_config.json --dry-run
```

## Troubleshooting

### Common Issues

**Issue**: Agents not producing expected results
**Solution**: Add more specific context in `pre_commands`

**Issue**: Token budget exceeded
**Solution**: Increase `max_tokens_per_command` or use `--overall-token-budget`

**Issue**: Tool permission errors
**Solution**: Add required tools to `allowed_tools` array

**Issue**: Agents repeating work
**Solution**: Use separate `session_id` for each agent

### Getting Help

1. **Check examples**: `python zen_orchestrator.py --list-examples`
2. **Inspect commands**: `python zen_orchestrator.py --inspect-command "/command"`
3. **Use dry run**: `python zen_orchestrator.py --config file.json --dry-run`
4. **Get LLM help**: `python zen_orchestrator.py --show-prompt-template`

## Example Workflows by Use Case

### Content Creation

Perfect for:
- Blog post writing
- Technical documentation
- Marketing content
- SEO optimization

```bash
python zen_orchestrator.py --config examples/content_creation.json
```

### Data Analysis

Ideal for:
- Research data processing
- Statistical analysis
- Report generation
- Visualization creation

```bash
python zen_orchestrator.py --config examples/data_analysis.json
```

### Software Testing

Great for:
- Test suite execution
- Coverage analysis
- Performance monitoring
- Improvement planning

```bash
python zen_orchestrator.py --config examples/testing_workflow.json
```

### System Migration

Essential for:
- Database migrations
- Code refactoring
- System upgrades
- Rollback planning

```bash
python zen_orchestrator.py --config examples/migration_workflow.json
```

## Next Steps

1. **Try the examples**: Start with built-in configurations
2. **Create custom workflows**: Use the LLM template for your specific needs
3. **Optimize performance**: Adjust token allocation and tool permissions
4. **Scale up**: Create complex multi-stage workflows
5. **Monitor costs**: Use budget controls for cost management

**Pro Tip**: Start simple and gradually increase complexity. The built-in examples are production-ready and demonstrate best practices.

## FAQ

**Q: How many agents can I run simultaneously?**
A: No hard limit, but 3-7 agents typically provide the best balance of parallelism and coordination.

**Q: Can agents share information?**
A: Yes, through shared files and session management. Agents in the same session can build on each other's work.

**Q: How do I control costs?**
A: Use `--overall-token-budget`, `--command-budget`, and `--budget-enforcement-mode` for precise cost control.

**Q: Can I modify examples?**
A: Absolutely! Generate an example, save it to a file, modify as needed, and run your custom version.

**Q: What's the difference between sequential and parallel execution?**
A: Sequential agents wait for previous agents to complete. Parallel agents run simultaneously for faster execution.

Welcome to the world of multi-agent AI orchestration! 🚀