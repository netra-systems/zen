# Claude Code Instance Orchestrator (SDK Enhanced)

Advanced orchestrator for running multiple Claude Code instances in headless mode with full SDK slash command support, session management, and command discovery.

## Quick Start

```bash
# Run with default configuration (3 instances)
./scripts/claude-orchestrator.sh

# See what would be executed without running
./scripts/claude-orchestrator.sh --dry-run

# List all available slash commands
./scripts/claude-orchestrator.sh --list-commands

# Inspect a specific command (shows YAML frontmatter)
./scripts/claude-orchestrator.sh --inspect /test-real

# Use custom configuration
./scripts/claude-orchestrator.sh -c my-config.json
```

## New SDK Features (2025)

✅ **Direct Slash Command Execution**: Commands are executed directly in prompts
✅ **YAML Frontmatter Support**: Full configuration from command files
✅ **Session Management**: Built-in `/clear` and `/compact` commands
✅ **Command Discovery**: Automatic detection of available commands
✅ **Pre-command Sequences**: Chain commands together
✅ **Command Validation**: Verify commands exist before execution

## Default Instance Configuration

The orchestrator runs 3 specialized instances by default:

1. **test_runner** - Executes `/test-real unit`
   - Session management: Clear history + help command first
   - Runs comprehensive unit tests with real services
   - Tools: Bash, Read, Write, Glob, Grep
   - Auto-accepts edits

2. **compliance_checker** - Executes `/compliance`
   - Session management: Clear and compact history
   - Checks SSOT compliance and architecture violations
   - Tools: Bash, Read, Write, Glob, Grep
   - Auto-accepts edits

3. **deployer** - Executes `/deploy-gcp staging`
   - Session management: Compact history, persistent session ID
   - Deploys to GCP staging environment
   - Tools: Bash, Read, Write, WebFetch
   - Asks for permission (interactive prompts)

## Files Created

- `scripts/claude-instance-orchestrator.py` - Main Python orchestrator
- `scripts/claude-orchestrator.sh` - Shell wrapper script
- `claude-instances-config.json` - Instance configuration
- `README-claude-orchestrator.md` - This documentation

## Usage Examples

### Basic Usage
```bash
# Run all 3 default instances
./scripts/claude-orchestrator.sh

# Dry run to see commands
./scripts/claude-orchestrator.sh --dry-run
```

### SDK Enhanced Usage
```bash
# List all available slash commands with descriptions
./scripts/claude-orchestrator.sh --list-commands

# Inspect command YAML frontmatter and configuration
./scripts/claude-orchestrator.sh --inspect /test-real

# Show exact command sequences that would run
./scripts/claude-orchestrator.sh --dry-run
```

### Custom Configuration
```bash
# Use custom config file
./scripts/claude-orchestrator.sh -c custom-config.json

# Save results to specific file
./scripts/claude-orchestrator.sh -o my-results.json

# Run from different workspace
./scripts/claude-orchestrator.sh -w /path/to/project
```

### Direct Python Usage
```bash
# Run orchestrator directly
python3 scripts/claude-instance-orchestrator.py

# With custom options
python3 scripts/claude-instance-orchestrator.py \
  --config claude-instances-config.json \
  --output results.json \
  --workspace .
```

## Configuration Format (SDK Enhanced)

Create custom configurations with full SDK features:

```json
{
  "description": "Enhanced instance configuration with SDK features",
  "instances": [
    {
      "name": "my_tester",
      "command": "/test-real integration",
      "description": "Run integration tests with fresh session",
      "allowed_tools": ["Bash", "Read", "Write"],
      "permission_mode": "acceptEdits",
      "output_format": "json",
      "clear_history": true,
      "compact_history": false,
      "pre_commands": ["/help", "/compact"],
      "session_id": "test_session_001"
    },
    {
      "name": "my_deployer",
      "command": "/deploy-gcp production",
      "description": "Production deployment with session continuity",
      "allowed_tools": ["Bash", "Read", "Write", "WebFetch"],
      "permission_mode": "ask",
      "output_format": "json",
      "clear_history": false,
      "compact_history": true,
      "pre_commands": [],
      "session_id": "deploy_prod_session"
    }
  ]
}
```

### New Configuration Options:
- `clear_history`: Start with fresh conversation (`/clear`)
- `compact_history`: Reduce history size (`/compact`)
- `pre_commands`: Commands to run before main command
- `session_id`: Persistent session for continuity

## Available Slash Commands

Based on your `.claude/commands/` directory, you can use any of these commands:

- `/test-real [category]` - Run tests with real services
- `/deploy-gcp [env]` - Deploy to GCP environment
- `/compliance` - Check architecture compliance
- `/tdd [feature] [module]` - Test-driven development workflow
- `/docker-rebuild` - Rebuild Docker containers
- `/ultimate-test-deploy-loop` - Complete test and deploy cycle
- `/pre-commit` - Pre-commit validation
- `/websocket-test` - WebSocket functionality testing
- And 30+ more commands...

## Output and Results

Results are saved in JSON format with detailed status for each instance:

```json
{
  "total_instances": 3,
  "completed": 2,
  "failed": 1,
  "instances": {
    "test_runner": {
      "status": "completed",
      "duration": "45.2s",
      "output": "...",
      "error": ""
    },
    "deployer": {
      "status": "failed",
      "duration": "12.1s",
      "error": "Authentication failed"
    }
  }
}
```

## Key Features

- **Concurrent Execution**: All instances run in parallel
- **Headless Mode**: Uses Claude Code's `--print` flag for non-interactive operation
- **Tool Permissions**: Configurable tool access per instance
- **Session Management**: Optional session ID support for continuity
- **Error Handling**: Comprehensive error capture and reporting
- **JSON Output**: Structured results for programmatic processing
- **Dry Run Mode**: Preview commands without execution

## Requirements

- Claude Code CLI installed (`npm install -g @anthropics/claude-code`)
- Python 3.8+
- Valid Anthropic API key configured
- Access to the project's `.claude/commands/` directory

## Rate Limit Considerations

- All instances share your Claude usage limits
- 3 concurrent instances will consume rate limits 3x faster
- Consider staggered execution for large workloads
- Monitor usage with `bunx CC usage`

## Troubleshooting

### Claude Command Not Found
```bash
npm install -g @anthropics/claude-code
```

### Authentication Issues
```bash
export ANTHROPIC_API_KEY="your-key-here"
# or configure via Claude Code setup
```

### Permission Denied
```bash
chmod +x scripts/claude-orchestrator.sh
```

### Rate Limit Exceeded
- Reduce concurrent instances
- Use staggered execution
- Monitor usage between runs