# Netra Apex Folder Structure Rules

## Critical Principle: Directory Integrity

Every file has a designated location based on its purpose and scope. Violating these conventions breaks system coherence and creates maintenance debt.

## 1. Service Boundaries (NEVER VIOLATE)

### Microservice Isolation
Each microservice owns its directory and ALL files within must be specific to that service:

```
/netra_backend/     # Main backend service (80% of codebase)
  /app/            # Application code
  /tests/          # Backend-specific tests ONLY
  /alembic/        # Database migrations for backend

/auth_service/      # Authentication microservice  
  /auth_core/      # Core auth logic
  /tests/          # Auth-specific tests ONLY
  /services_init.py # Service initialization

/frontend/          # React/Next.js frontend
  /components/     # React components
  /hooks/          # React hooks
  /lib/            # Frontend utilities
  /__tests__/      # Frontend unit tests
  /cypress/        # E2E UI tests
```

**CRITICAL RULES:**
- NEVER place auth_service tests in /netra_backend/tests/
- NEVER place backend tests in /auth_service/tests/
- NEVER mix service-specific code across boundaries
- Each service must be independently deployable

## 2. Test Organization Hierarchy

### Test Categories by Location

```
/tests/                     # Root-level cross-service tests
  /e2e/                    # End-to-end tests spanning multiple services
    /fixtures/             # Shared E2E test fixtures
    /performance/          # Performance and load tests
    /rapid_message/        # Message handling tests
    /websocket_resilience/ # WebSocket stability tests
    /test_helpers/         # E2E test utilities
    
/netra_backend/tests/       # Backend-specific tests
  /agents/                 # Agent system tests
  /integration/            # Backend integration tests
  /unit/                   # Backend unit tests
  
/auth_service/tests/        # Auth-specific tests
  /integration/            # Auth integration tests
  /unit/                   # Auth unit tests
  /factories/              # Test data factories
  
/frontend/                  # Frontend tests
  /__tests__/              # Component unit tests
  /cypress/e2e/            # UI E2E tests

/test_framework/            # Shared test infrastructure
  /decorators.py           # Test decorators
  /mock_utils.py           # Mock utilities
  /runner.py               # Test runner utilities
```

### Test Placement Rules

1. **Unit Tests**: Place next to the code they test or in service's `/tests/unit/`
2. **Integration Tests**: In service's `/tests/integration/`
3. **E2E Tests**: In `/tests/e2e/` if they span services
4. **Performance Tests**: In `/tests/e2e/performance/`
5. **Service-Specific E2E**: Can be in service's `/tests/e2e/` subdirectory

## 3. Configuration Management

### Configuration Hierarchy

```
/                           # Root configuration
  config.yaml              # Main application config
  pytest.ini               # Global pytest config
  requirements.txt         # Python dependencies
  package.json            # Node.js dependencies (if applicable)
  
/config/                   # Configuration directory
  /staging.env            # Staging environment
  /docker-compose.*.yml   # Docker configurations
  /cloudbuild-*.yaml      # GCP Cloud Build configs
  
/auth_service/            
  requirements.txt        # Auth-specific dependencies
  pytest.ini              # Auth-specific test config
  
/frontend/
  package.json            # Frontend dependencies
  next.config.ts          # Next.js configuration
  tsconfig.json           # TypeScript configuration
```

### Environment Files
- Development: `.env.development` (gitignored)
- Staging: `/config/staging.env`
- Production: Managed via secret management
- Test: `.env.test` (gitignored)

## 4. Documentation Structure

```
/docs/                     # User-facing documentation
  /architecture/          # Architecture documentation
  /auth/                  # Authentication guides
  /business/              # Business context
  /development/           # Development guides
  /operations/            # Operations guides
  /reports/               # Analysis reports
  /testing/               # Testing documentation
  
/SPEC/                    # Technical specifications
  *.xml                   # XML specifications
  *.md                    # Markdown specifications
  /learnings/             # Learnings and insights
  /generated/             # Generated artifacts
  
/documentation/           # Implementation documentation
  /implementation_reports/ # Implementation summaries
  /planning/              # Planning documents
  /status/                # Status reports
```

## 5. Scripts and Automation

```
/scripts/                  # Utility and automation scripts
  dev_launcher.py         # Development environment launcher
  check_*.py              # Validation scripts
  fix_*.py                # Automated fix scripts
  generate_*.py           # Generation scripts
  validate_*.py           # Validation utilities
  test_*.py               # Script tests
  
/database_scripts/        # Database-specific scripts
  *.sql                   # SQL scripts
  create_*.py             # Database creation scripts
  
/.github/                 # GitHub-specific
  /workflows/             # GitHub Actions workflows
  /scripts/               # CI/CD scripts
```

## 6. Shared Resources

```
/shared/                  # Cross-service shared resources
  *.json                  # Shared JSON schemas
  schemas.json            # Type definitions
  
/business-context/        # Business documentation
  /reports/               # Business reports
  
/terraform-dev-postgres/  # Infrastructure as code
  *.tf                    # Terraform files
  manage.ps1              # PowerShell management
  manage.sh               # Bash management
```

## 7. Build and Deployment

```
/organized_root/          # Deployment organization
  /deployment_configs/    # Deployment configurations
  
/deployments/             # Deployment artifacts
  /issues/                # Deployment issues log
  
/alembic/                 # Database migrations (backend)
  /versions/              # Migration versions
  
# Note: auth-proxy directory removed - functionality moved to auth_service
```

## 8. Development Support

```
/dev_launcher/            # Development launcher module
  *.py                    # Launcher components
  /tests/                 # Launcher tests
  /logs/                  # Development logs
  
/ccusage/                 # Claude usage tracking tool
  /src/                   # Source code
  /docs/                  # Documentation
  
/cypress/                 # Frontend E2E tests
  /e2e/                   # Test specifications
  
/archive/                 # Archived code
  /legacy_tests_*/        # Archived test suites
```

## 9. Temporary and Generated Files

```
/temp/                    # Temporary files (gitignored)
/uploads/                 # Upload directory (gitignored)
/logs/                    # Application logs (gitignored)
/.venv/                   # Virtual environment (gitignored)
/venv/                    # Alternative venv (gitignored)
/work_in_progress/        # WIP files (evaluate for cleanup)
```

## 10. File Naming Conventions

### Test Files
- Unit tests: `test_<module_name>.py`
- Integration tests: `test_<feature>_integration.py`
- E2E tests: `test_<workflow>_e2e.py`
- Performance tests: `test_<scenario>_performance.py`

### Configuration Files
- Environment: `.env.<environment>`
- Docker: `docker-compose.<environment>.yml`
- CI/CD: `<platform>-<environment>.yaml`

### Documentation
- Guides: `<TOPIC>_GUIDE.md`
- Reports: `<TOPIC>_REPORT.md`
- Specifications: `<feature>.xml` or `<feature>_spec.md`

## 11. Import Path Requirements

### Correct Import Patterns
```python
# Within netra_backend
from netra_backend.app.models import User
from netra_backend.app.services import AgentService

# Within auth_service
from auth_service.auth_core import AuthManager
from auth_service.services_init import initialize

# Cross-service (only via APIs)
# NEVER import directly across service boundaries
```

### Forbidden Patterns
```python
# NEVER DO THIS:
# In auth_service file:
from netra_backend.app.models import User  # VIOLATION!

# In netra_backend file:
from auth_service.auth_core import validate  # VIOLATION!
```

## 12. Migration Rules

When moving files:
1. Update ALL imports in affected files
2. Update relevant test imports
3. Update documentation references
4. Run validation: `python scripts/validate_service_independence.py`
5. Ensure CI/CD passes

## 13. Archive Strategy

### When to Archive
- Legacy code replaced by new implementation
- Deprecated features removed from production
- Old test suites superseded by new ones

### Archive Structure
```
/archive/
  /legacy_<feature>_<date>/
    MANIFEST.txt          # Description of archived content
    <archived_files>      # Original file structure preserved
```

## 14. Special Directories

### Do Not Modify Without Review
- `/SPEC/` - Specifications are the source of truth
- `/shared/` - Changes affect multiple services
- `/.github/workflows/` - CI/CD critical path
- `/terraform-dev-postgres/` - Infrastructure definitions

### Frequently Updated
- `/docs/reports/` - Analysis and status reports
- `/test_reports/` - Test execution results
- `/documentation/status/` - System status tracking

## Validation Commands

Always validate directory structure compliance:

```bash
# Check service independence
python scripts/validate_service_independence.py

# Check import patterns
python scripts/check_imports.py

# Validate test organization
python scripts/validate_test_organization.py

# Check for misplaced files
python scripts/check_file_placement.py
```

## Common Violations and Fixes

### Violation: Auth tests in backend directory
**Fix**: Move to `/auth_service/tests/`

### Violation: Shared utility in service directory
**Fix**: Move to `/shared/` or `/test_framework/`

### Violation: Cross-service imports
**Fix**: Use API calls or message passing

### Violation: Config in wrong location
**Fix**: Root for global, service dir for specific

## Enforcement

The boundary enforcer (`scripts/boundary_enforcer.py`) automatically detects violations. Run before commits:

```bash
python scripts/boundary_enforcer.py --check
```

---

**Remember**: Directory organization is not just about tidiness—it's about maintaining clear boundaries, enabling independent deployment, and preserving system coherence. Every file placement decision impacts the entire system's maintainability.