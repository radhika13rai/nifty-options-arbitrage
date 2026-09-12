"""
API Authentication, Operator Authorization & RBAC Middleware.
Protects trading operations, kill-switch reset, and control plane endpoints.
"""

import os
import hmac
import logging
from typing import Optional, Set
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger("APIAuth")

# Configurable operator API key
SERQ_API_KEY = os.environ.get("SERQ_API_KEY", "")

# Endpoints strictly requiring Operator / Admin Authorization
RESTRICTED_MUTATING_PATHS: Set[str] = {
    "/api/kill-switch",
    "/api/paper/reset",
    "/api/paper/order",
    "/api/auto-trade/toggle",
    "/api/auto-trade/square-off",
    "/api/ml/retrain",
    "/api/scheduler/advance",
    "/api/soak/start",
    "/api/soak/stop",
    "/api/soak/reset",
    "/api/global-macro/scenario",
    "/api/global-macro/train",
    "/api/global-macro/poll",
    "/api/greeks/calibrate"
}


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Validates API key for sensitive mutating operational endpoints.
    Enforces X-API-Key or Authorization: Bearer <key> header.
    Rejects unauthorized requests with 401 Unauthorized or 403 Forbidden.
    """
    def __init__(self, app, api_key: Optional[str] = None):
        super().__init__(app)
        self.api_key = api_key or SERQ_API_KEY

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        # Check if path is in restricted operational list
        if path in RESTRICTED_MUTATING_PATHS or (method == "POST" and path.startswith("/api/")):
            # Allow analytical stateless calculate requests
            if path in ("/api/greeks/calculate", "/api/greeks/iv", "/api/greeks/screener"):
                return await call_next(request)

            # Check authorization header
            provided_key = request.headers.get("X-API-Key")
            auth_header = request.headers.get("Authorization", "")
            if not provided_key and auth_header.startswith("Bearer "):
                provided_key = auth_header[7:].strip()

            # If an API key is configured, enforce strict constant-time matching
            if self.api_key:
                if not provided_key or not hmac.compare_digest(provided_key, self.api_key):
                    logger.warning(f"Unauthorized access attempt to {method} {path} from {request.client.host if request.client else 'unknown'}")
                    return JSONResponse(
                        {"error": "Unauthorized: Valid API key required in X-API-Key or Authorization: Bearer header."},
                        status_code=401
                    )
            else:
                # If SERQ_API_KEY is not configured, reject external internet requests
                client_host = request.client.host if request.client else ""
                is_local = client_host in ("127.0.0.1", "localhost", "::1", "testclient")
                if not is_local:
                    logger.warning(f"Blocked unauthenticated external request to {path} from {client_host}")
                    return JSONResponse(
                        {"error": "Forbidden: Remote access requires SERQ_API_KEY to be configured."},
                        status_code=403
                    )

        return await call_next(request)
