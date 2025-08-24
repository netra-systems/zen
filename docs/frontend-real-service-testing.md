# Frontend Real Service Testing

## Overview

The frontend test infrastructure now supports running tests against real backend services instead of mocks. This enables true end-to-end integration testing with actual API calls, WebSocket connections, and database interactions.

## Quick Start

### 1. Start Backend Services

```bash
# Option A: Use Docker services (recommended)
python scripts/start_test_services.py --docker

# Option B: Use local services
python scripts/start_test_services.py
```

### 2. Run Frontend Tests with Real Services

```bash
# Using unified test runner (recommended)
python unified_test_runner.py --category frontend --real-services

# With real LLM
python unified_test_runner.py --category frontend --real-services --real-llm

# Using npm scripts directly
npm run test:real          # Real services with local backend
npm run test:real:docker   # Real services with Docker
npm run test:real:llm      # Real services with real LLM
npm run test:real:all      # Everything real
```

## Configuration

### Environment Variables

- `USE_REAL_SERVICES`: Enable real service testing (default: false)
- `USE_DOCKER_SERVICES`: Use Docker containers (default: false)  
- `USE_REAL_LLM`: Use real LLM APIs (default: false)
- `BACKEND_URL`: Backend service URL (default: http://localhost:8000)
- `AUTH_SERVICE_URL`: Auth service URL (default: http://localhost:8081)
- `WEBSOCKET_URL`: WebSocket URL (default: ws://localhost:8000)

### Jest Configuration Files

- `jest.config.cjs`: Default configuration with mocks (unit tests)
- `jest.config.real.cjs`: Configuration for real service testing
- `jest.setup.js`: Default setup with all mocks
- `jest.setup.real.js`: Setup for real service testing

## Test Modes

### 1. Mocked Mode (Default)
- All external services are mocked
- Fast execution
- No external dependencies
- Good for unit tests and CI

```bash
npm test
```

### 2. Real Services Mode
- Uses actual backend services
- Real HTTP/WebSocket connections
- Real database operations
- Good for integration testing

```bash
npm run test:real
```

### 3. Docker Services Mode
- Uses Docker containers for all services
- Isolated test environment
- Consistent across machines
- Good for E2E testing

```bash
npm run test:real:docker
```

### 4. Real LLM Mode
- Uses actual LLM APIs (OpenAI, Anthropic, etc.)
- Requires API keys
- Has cost implications
- Good for AI feature testing

```bash
npm run test:real:llm
```

## Writing Tests for Real Services

### Example Test

```javascript
describe('Chat Integration (Real Services)', () => {
  beforeAll(async () => {
    // Wait for services to be ready
    await global.waitForBackend();
    await global.waitForAuthService();
    
    // Authenticate test user
    await global.authenticateTestUser();
  });
  
  it('should send and receive messages through real WebSocket', async () => {
    // This will use real WebSocket connection
    const ws = new WebSocket(process.env.WEBSOCKET_URL);
    
    await new Promise(resolve => {
      ws.onopen = resolve;
    });
    
    ws.send(JSON.stringify({
      type: 'message',
      content: 'Hello from test'
    }));
    
    const response = await new Promise(resolve => {
      ws.onmessage = (event) => {
        resolve(JSON.parse(event.data));
      };
    });
    
    expect(response).toHaveProperty('type');
    expect(response).toHaveProperty('content');
  });
});
```

### Helper Functions

- `global.waitForBackend()`: Wait for backend to be ready
- `global.waitForAuthService()`: Wait for auth service to be ready
- `global.authenticateTestUser()`: Authenticate a test user

## CI/CD Integration

### GitHub Actions

```yaml
- name: Start test services
  run: |
    docker-compose -f docker-compose.test.yml up -d
    python scripts/wait_for_services.py

- name: Run frontend tests with real services
  env:
    USE_REAL_SERVICES: true
    USE_DOCKER_SERVICES: true
  run: |
    npm run test:real:docker
```

## Benefits

1. **True Integration Testing**: Test actual service interactions
2. **Catch Real Issues**: Find problems mocks might hide
3. **Confidence**: Know your frontend works with real backend
4. **Flexibility**: Choose appropriate test level for your needs

## Troubleshooting

### Services Not Starting
```bash
# Check Docker is running
docker info

# Check port availability
netstat -an | grep 8000
netstat -an | grep 8081
```

### Tests Timing Out
```bash
# Increase timeout
JEST_TIMEOUT=60000 npm run test:real
```

### Authentication Issues
```bash
# Check auth service is running
curl http://localhost:8081/health

# Try manual authentication
curl -X POST http://localhost:8081/auth/dev/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com"}'
```

## Best Practices

1. **Use Mocked Tests for CI**: Keep CI fast with mocked tests
2. **Real Services for Pre-Deploy**: Run real service tests before deployment
3. **Isolate Test Data**: Use separate test database/redis
4. **Clean Up**: Ensure tests clean up after themselves
5. **Monitor Costs**: Be careful with real LLM usage

## Migration Guide

### From Mocked to Real Tests

1. Identify tests that would benefit from real services
2. Move integration tests to use real services
3. Keep unit tests mocked for speed
4. Add cleanup in afterEach/afterAll hooks
5. Handle async operations properly

### Example Migration

```javascript
// Before (Mocked)
jest.mock('@/services/apiClient');

it('should fetch data', async () => {
  apiClient.get.mockResolvedValue({ data: mockData });
  const result = await fetchData();
  expect(result).toEqual(mockData);
});

// After (Real Services)
it('should fetch data from real API', async () => {
  await global.waitForBackend();
  const result = await fetchData();
  expect(result).toHaveProperty('id');
  expect(result).toHaveProperty('created_at');
});
```

## Performance Considerations

- Real service tests are slower than mocked tests
- Use parallel execution where possible
- Cache test data when appropriate
- Use Docker for consistent performance
- Monitor test execution times

## Security Notes

- Never commit real API keys
- Use TEST_* prefixed environment variables
- Isolate test environments from production
- Use separate test databases
- Clean sensitive data after tests