# Netra Unified Testing Environment

## 🎯 Business Value Justification
**Segment**: ALL - Free to Enterprise  
**Goal**: Protect 100% of revenue by ensuring core functionality works  
**Value Impact**: Failed chat = 100% churn rate = $0 revenue  
**Revenue Impact**: Each working user journey = $99-999/month recurring  
**Critical Metric**: Zero tolerance for basic chat failures

## 📋 Overview

The Unified Testing Environment provides a containerized setup that runs **ALL** services together using **REAL** connections and data flow. This eliminates the testing paradox where individual mocked tests pass but the actual system fails.

### Key Principles
- **REAL OVER MOCKED**: Only mock external services (payment, email). Never mock internal services or databases.
- **UNIFIED SYSTEM TESTS**: Every critical flow tests Auth + Backend + Frontend together.
- **LOUD FAILURES**: Failures are immediately visible with actionable error messages.

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   Auth Service  │
│   (Next.js)     │◄───┤   (FastAPI)     │◄───┤   (FastAPI)     │
│   Port: 3000    │    │   Port: 8000    │    │   Port: 8001    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
    ┌────────────────────────────┼────────────────────────────┐
    │                            │                            │
    ▼                            ▼                            ▼
┌─────────────┐         ┌─────────────┐              ┌─────────────┐
│ PostgreSQL  │         │ ClickHouse  │              │    Redis    │
│ Port: 5433  │         │ Port: 8124  │              │ Port: 6380  │
└─────────────┘         └─────────────┘              └─────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Docker Desktop (Windows/Mac) or Docker Engine (Linux)
- Docker Compose v2.0+
- 8GB RAM minimum
- 10GB free disk space

### Option 1: One-Command Start (Recommended)

**Windows (PowerShell):**
```powershell
.\start-unified-tests.ps1
```

**Linux/Mac (Bash):**
```bash
./start-unified-tests.sh
```

### Option 2: Manual Docker Compose

```bash
# Start all services
docker-compose -f docker-compose.test.yml --env-file .env.test up -d

# Check service health
docker-compose -f docker-compose.test.yml ps

# Run tests
docker-compose -f docker-compose.test.yml run --rm test-runner

# Stop everything
docker-compose -f docker-compose.test.yml down --volumes
```

## 📊 Services Configuration

| Service | Container Port | Host Port | Purpose |
|---------|----------------|-----------|---------|
| Frontend | 3000 | 3000 | Next.js UI |
| Backend | 8000 | 8000 | FastAPI + WebSocket |
| Auth Service | 8080 | 8001 | Authentication |
| PostgreSQL | 5432 | 5433 | Main Database |
| ClickHouse | 8123 | 8124 | Analytics DB |
| Redis | 6379 | 6380 | Caching/Sessions |

## 🔧 Environment Configuration

The `.env.test` file contains all necessary configuration:

- **Database URLs**: Containerized database connections
- **Service URLs**: Internal container networking
- **Test Credentials**: Pre-configured test users
- **Feature Flags**: Testing-specific overrides
- **Mock Settings**: External service mocking

## 🧪 Test Categories

### 1. Unified Critical Tests (50+ tests)
Tests that validate the entire system working together:
- First-time user signup → chat interaction
- Returning user login → conversation history
- OAuth flow → dashboard access
- Real-time WebSocket communication

### 2. Service Integration Tests (100+ tests)
Tests between two services:
- Auth ↔ Backend JWT validation
- Backend ↔ Frontend API calls
- Frontend ↔ Auth OAuth flows

### 3. Component Isolation Tests (500+ tests)
Traditional unit tests with minimal mocking:
- Business logic validation
- Data transformation
- Utility functions

## 🔍 Critical User Journeys Tested

### First Time User Flow
1. User visits landing page
2. User clicks sign up
3. User enters email and password
4. Auth service creates user
5. Backend creates user profile
6. Frontend redirects to dashboard
7. User sends first chat message
8. Backend processes via WebSocket
9. Agent responds with meaningful answer
10. Response displayed in Frontend

**Validation:**
- ✅ User exists in Auth database
- ✅ User exists in Backend database
- ✅ WebSocket connection established
- ✅ Message received and processed
- ✅ Response generated and delivered

### OAuth Login Flow
1. User clicks "Login with Google"
2. OAuth redirect initiated
3. Google authentication completes (mocked)
4. Callback processed
5. User created/updated in Auth
6. Profile synced to Backend
7. Dashboard loads

### Basic Chat Interaction
1. User types message
2. Frontend sends via WebSocket
3. Backend authenticates user
4. Message routed to agent
5. Agent processes request (mocked)
6. Response generated
7. Response sent via WebSocket
8. Frontend displays response

## 📈 Success Metrics

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Test Execution Rate | 10% | 100% | 🔄 In Progress |
| Real vs Mocked Ratio | 5% real | 80% real | 🔄 In Progress |
| Unified Test Coverage | 0% | 100% | 🔄 In Progress |
| Deployment Confidence | 20% | 95% | 🔄 In Progress |

## 🛠️ Usage Commands

### Basic Commands
```bash
# Start everything and run tests
./start-unified-tests.sh

# Force rebuild and clean start
./start-unified-tests.sh --build --cleanup

# Check service health
./start-unified-tests.sh --status

# View live logs
./start-unified-tests.sh --logs

# Stop all services
./start-unified-tests.sh --stop
```

### Development Commands
```bash
# Run only specific test categories
docker-compose -f docker-compose.test.yml run --rm test-runner \
  python test_runner.py --level unified --category auth

# Access service logs
docker-compose -f docker-compose.test.yml logs frontend-service
docker-compose -f docker-compose.test.yml logs backend-service
docker-compose -f docker-compose.test.yml logs auth-service

# Connect to databases for debugging
docker-compose -f docker-compose.test.yml exec test-postgres psql -U test_user -d netra_test
docker-compose -f docker-compose.test.yml exec test-redis redis-cli -a test_password
```

## 🐛 Troubleshooting

### Common Issues

**Services Not Starting:**
```bash
# Check Docker is running
docker info

# Check for port conflicts
netstat -an | grep -E ":(3000|8000|8001|5433|6380|8124)"

# Clean everything and restart
docker-compose -f docker-compose.test.yml down --volumes --remove-orphans
docker system prune -f
```

**Database Connection Errors:**
```bash
# Check database health
docker-compose -f docker-compose.test.yml exec test-postgres pg_isready -U test_user

# View database logs
docker-compose -f docker-compose.test.yml logs test-postgres

# Reset database
docker-compose -f docker-compose.test.yml down --volumes
docker-compose -f docker-compose.test.yml up -d test-postgres
```

**Test Failures:**
```bash
# Run tests with verbose output
docker-compose -f docker-compose.test.yml run --rm test-runner \
  python test_runner.py --level unified --verbose --no-coverage

# Access test results
docker-compose -f docker-compose.test.yml run --rm test-runner ls -la /app/test_results/
```

### Service URLs for Manual Testing

Once services are running, you can manually test:

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000/docs (Swagger UI)
- **Auth Service**: http://localhost:8001/docs (Swagger UI)
- **Backend Health**: http://localhost:8000/health
- **Auth Health**: http://localhost:8001/health

## 📝 Test Data

The environment creates pre-configured test users:

**Regular User:**
- Email: test@netra.ai
- Password: test_password_123

**Admin User:**
- Email: admin@netra.ai
- Password: admin_password_123

## 🔒 Security Notes

- All credentials in `.env.test` are for testing only
- Real API keys should never be used in test environment
- Test databases are isolated and temporary
- OAuth providers use mock implementations

## 🚀 CI/CD Integration

To integrate with your CI/CD pipeline:

```yaml
# GitHub Actions example
- name: Run Unified Tests
  run: |
    ./start-unified-tests.sh --build --cleanup
    
- name: Upload Test Results
  uses: actions/upload-artifact@v3
  with:
    name: test-results
    path: test_results_unified/
```

## 📊 Monitoring

The test environment includes built-in monitoring:

- **Health Checks**: All services have automated health checks
- **Test Results**: Comprehensive HTML and JSON reports
- **Performance Metrics**: Response time tracking
- **Error Reporting**: Detailed failure diagnostics

## 🎯 Next Steps

1. **Run the setup**: `./start-unified-tests.sh --build --cleanup`
2. **Verify all services are healthy**: `./start-unified-tests.sh --status`
3. **Review test results**: Check `./test_results_unified/` directory
4. **Integrate with CI/CD**: Add to your deployment pipeline
5. **Expand test coverage**: Add more unified test scenarios

## 📞 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review service logs: `./start-unified-tests.sh --logs`
3. Verify Docker resources are sufficient (8GB RAM minimum)
4. Ensure no port conflicts with local development environment

---

**Remember**: This is REAL integration testing. Every test exercises actual service communication, database operations, and user workflows. This gives us true confidence that the system works as users expect.