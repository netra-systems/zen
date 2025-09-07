# Netra Auth Service

**IMPORTANT**: This is a completely independent standalone authentication microservice for the Netra platform.
It has NO dependencies on the main Netra app and must remain fully self-contained.

## Architecture

### Independence Principle
The auth service is designed to be 100% independent from the main Netra application:
- All code is contained within the `auth_service/` directory
- Uses its own `auth_core/` module (NOT the main app's `app/` module)
- Has its own models, services, and routes
- No imports from the main Netra app are allowed

### Core Responsibilities
The auth service handles:
- User authentication (login/logout)
- Token management (JWT creation/validation)
- Session management (Redis-backed)
- Service-to-service authentication
- OAuth integration

## Local Development

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Redis (via Docker)
- PostgreSQL (via Docker)

### Quick Start

1. Start the auth service with dependencies:
```bash
python scripts/start_auth_service.py
```

This will:
- Start Redis and PostgreSQL containers
- Run database migrations
- Start the auth service on port 8081

2. Alternatively, use Docker Compose:
```bash
docker-compose -f docker-compose.auth.yml up
```

### Manual Setup

1. Start dependencies:
```bash
docker-compose -f docker-compose.auth.yml up redis postgres
```

2. Run the auth service:
```bash
cd auth_service
python -m uvicorn main:app --host 0.0.0.0 --port 8081 --reload
```

## API Documentation

When running locally, API documentation is available at:
- Swagger UI: http://localhost:8081/docs
- ReDoc: http://localhost:8081/redoc

## Endpoints

### Health Check
- `GET /health` - Service health status
- `GET /auth/health` - Auth module health with Redis status

### Authentication
- `POST /auth/login` - User login
- `POST /auth/logout` - User logout
- `POST /auth/validate` - Validate access token
- `POST /auth/refresh` - Refresh tokens
- `GET /auth/verify` - Quick token verification

### Service Authentication
- `POST /auth/service-token` - Generate service-to-service token

## Configuration

## Deployment


### Deploy to GCP Cloud Run

1. Using GitHub Actions (automatic on push to main/staging):
   - Pushes to `main` deploy to production
   - Pushes to `staging` deploy to staging

2. Manual deployment:
```bash
python scripts/deploy_auth_service.py --env staging
```

3. Using Terraform:
```bash
cd terraform-gcp
terraform apply -target=google_cloud_run_service.auth_service
```

## Integration

### Backend Integration

The main Netra backend service integrates with this auth service using the auth client located in the main app at `app/clients/auth_client.py`:

```python
# In the main Netra app (not in auth service)
# Import the auth client from main app's client module
from netra_backend.app.clients.auth_client import auth_client

# Validate token
result = await auth_client.validate_token(token)

# Login
result = await auth_client.login(email, password)

# Logout
success = await auth_client.logout(token)
```

### Frontend Integration

The frontend uses the auth service configuration at `frontend/lib/auth-service-config.ts`:

```typescript
import { authService } from '@/lib/auth-service-config';

// Login
authService.initiateLogin('google');

// Get session
const session = await authService.getSession();

// Validate token
const isValid = await authService.validateToken(token);
```

## Testing

### Run Integration Tests

```bash
python scripts/test_auth_integration.py
```

This tests:
- Auth service health
- API endpoints
- Backend integration
- Token validation flow
- CORS configuration

### Unit Tests

```bash
cd auth_service
pytest tests/
```

## Monitoring

### Health Checks
- Service health: `/health`
- Detailed health: `/auth/health`

### Metrics
- Request latency
- Token validation rate
- Login success/failure rate
- Redis connection status

## Security

- JWT tokens with configurable expiry
- Refresh token rotation
- Rate limiting on auth endpoints
- CORS configuration
- Service-to-service authentication
- Secret management via GCP Secret Manager

## Troubleshooting

### Common Issues

1. **Port already in use**
   - Check if another service is using port 8081
   - Use `lsof -i :8081` to find the process

2. **Redis connection failed**
   - Ensure Redis container is running
   - Check REDIS_URL environment variable

3. **Database connection failed**
   - Ensure PostgreSQL container is running

4. **CORS errors**
   - Verify CORS_ORIGINS environment variable
   - Check frontend URL configuration

## Support

For issues or questions, contact the platform team or check the documentation.