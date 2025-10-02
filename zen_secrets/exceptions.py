"""
Secret Management Exceptions

Custom exception classes for the Zen Secret Management System.
Provides detailed error information for debugging and monitoring.
"""

from typing import Optional, Dict, Any


class SecretManagerError(Exception):
    """Base exception for all secret management errors."""

    def __init__(self, message: str, error_code: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.error_code = error_code
        self.context = context or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging."""
        return {
            "error_type": self.__class__.__name__,
            "message": str(self),
            "error_code": self.error_code,
            "context": self.context
        }


class SecretNotFoundError(SecretManagerError):
    """Raised when a requested secret is not found."""

    def __init__(self, secret_name: str, environment: Optional[str] = None):
        message = f"Secret '{secret_name}' not found"
        if environment:
            message += f" in environment '{environment}'"

        super().__init__(
            message=message,
            error_code="SECRET_NOT_FOUND",
            context={"secret_name": secret_name, "environment": environment}
        )


class SecretAccessDeniedError(SecretManagerError):
    """Raised when access to a secret is denied due to insufficient permissions."""

    def __init__(self, secret_name: str, required_permission: str,
                 service_account: Optional[str] = None):
        message = f"Access denied to secret '{secret_name}'. Required permission: {required_permission}"
        if service_account:
            message += f". Service account: {service_account}"

        super().__init__(
            message=message,
            error_code="SECRET_ACCESS_DENIED",
            context={
                "secret_name": secret_name,
                "required_permission": required_permission,
                "service_account": service_account
            }
        )


class SecretValidationError(SecretManagerError):
    """Raised when secret validation fails."""

    def __init__(self, secret_name: str, validation_errors: list):
        message = f"Validation failed for secret '{secret_name}': {', '.join(validation_errors)}"

        super().__init__(
            message=message,
            error_code="SECRET_VALIDATION_FAILED",
            context={
                "secret_name": secret_name,
                "validation_errors": validation_errors
            }
        )


class SecretRotationError(SecretManagerError):
    """Raised when secret rotation fails."""

    def __init__(self, secret_name: str, rotation_step: str,
                 original_error: Optional[Exception] = None):
        message = f"Secret rotation failed for '{secret_name}' at step '{rotation_step}'"
        if original_error:
            message += f": {str(original_error)}"

        super().__init__(
            message=message,
            error_code="SECRET_ROTATION_FAILED",
            context={
                "secret_name": secret_name,
                "rotation_step": rotation_step,
                "original_error": str(original_error) if original_error else None
            }
        )


class SecretConfigurationError(SecretManagerError):
    """Raised when secret configuration is invalid."""

    def __init__(self, config_issue: str, config_path: Optional[str] = None):
        message = f"Secret configuration error: {config_issue}"
        if config_path:
            message += f" in {config_path}"

        super().__init__(
            message=message,
            error_code="SECRET_CONFIG_ERROR",
            context={
                "config_issue": config_issue,
                "config_path": config_path
            }
        )


class SecretEncryptionError(SecretManagerError):
    """Raised when secret encryption/decryption fails."""

    def __init__(self, operation: str, secret_name: str,
                 encryption_key_id: Optional[str] = None):
        message = f"Secret {operation} failed for '{secret_name}'"
        if encryption_key_id:
            message += f" using key '{encryption_key_id}'"

        super().__init__(
            message=message,
            error_code="SECRET_ENCRYPTION_ERROR",
            context={
                "operation": operation,
                "secret_name": secret_name,
                "encryption_key_id": encryption_key_id
            }
        )


class SecretBackupError(SecretManagerError):
    """Raised when secret backup operations fail."""

    def __init__(self, operation: str, backup_location: str,
                 secret_count: Optional[int] = None):
        message = f"Secret backup {operation} failed for location '{backup_location}'"
        if secret_count:
            message += f" ({secret_count} secrets affected)"

        super().__init__(
            message=message,
            error_code="SECRET_BACKUP_ERROR",
            context={
                "operation": operation,
                "backup_location": backup_location,
                "secret_count": secret_count
            }
        )


class SecretAuditError(SecretManagerError):
    """Raised when secret audit logging fails."""

    def __init__(self, audit_operation: str, secret_name: str,
                 user_id: Optional[str] = None):
        message = f"Audit logging failed for {audit_operation} on secret '{secret_name}'"
        if user_id:
            message += f" by user '{user_id}'"

        super().__init__(
            message=message,
            error_code="SECRET_AUDIT_ERROR",
            context={
                "audit_operation": audit_operation,
                "secret_name": secret_name,
                "user_id": user_id
            }
        )


class SecretIntegrityError(SecretManagerError):
    """Raised when secret integrity checks fail."""

    def __init__(self, secret_name: str, integrity_check: str,
                 expected_hash: Optional[str] = None, actual_hash: Optional[str] = None):
        message = f"Integrity check '{integrity_check}' failed for secret '{secret_name}'"
        if expected_hash and actual_hash:
            message += f" (expected: {expected_hash[:8]}..., actual: {actual_hash[:8]}...)"

        super().__init__(
            message=message,
            error_code="SECRET_INTEGRITY_ERROR",
            context={
                "secret_name": secret_name,
                "integrity_check": integrity_check,
                "expected_hash": expected_hash,
                "actual_hash": actual_hash
            }
        )