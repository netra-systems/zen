# Shim module for backward compatibility
# User auth consolidated into auth_failover_service
from netra_backend.app.services.auth_failover_service import *
from netra_backend.app.core.user_service import UserService

# Legacy aliases
UserAuthService = UserService
authenticate_user = UserService.authenticate
validate_token = UserService.validate_token
