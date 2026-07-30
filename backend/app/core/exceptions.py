from __future__ import annotations

from typing import Any, Optional


class DataForgeError(Exception):
    """Base exception for DataForge AI platform."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        status_code: int = 500,
        details: Optional[dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ScrapingError(DataForgeError):
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            message=message,
            error_code="SCRAPING_ERROR",
            status_code=500,
            details=details,
        )


class ProxyError(DataForgeError):
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            message=message,
            error_code="PROXY_ERROR",
            status_code=502,
            details=details,
        )


class BrowserError(DataForgeError):
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            message=message,
            error_code="BROWSER_ERROR",
            status_code=500,
            details=details,
        )


class ExtractionError(DataForgeError):
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            message=message,
            error_code="EXTRACTION_ERROR",
            status_code=500,
            details=details,
        )


class RateLimitError(DataForgeError):
    def __init__(self, message: str = "Rate limit exceeded", details: Optional[dict] = None):
        super().__init__(
            message=message,
            error_code="RATE_LIMIT",
            status_code=429,
            details=details,
        )


class CAPTCHAError(DataForgeError):
    def __init__(self, message: str = "CAPTCHA encountered", details: Optional[dict] = None):
        super().__init__(
            message=message,
            error_code="CAPTCHA_REQUIRED",
            status_code=403,
            details=details,
        )


class NotFoundError(DataForgeError):
    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            message=f"{resource} not found: {resource_id}",
            error_code="NOT_FOUND",
            status_code=404,
            details={"resource": resource, "resource_id": resource_id},
        )


class AuthenticationError(DataForgeError):
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            error_code="AUTH_ERROR",
            status_code=401,
        )


class AuthorizationError(DataForgeError):
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message=message,
            error_code="FORBIDDEN",
            status_code=403,
        )


class ValidationError(DataForgeError):
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=422,
            details=details,
        )
