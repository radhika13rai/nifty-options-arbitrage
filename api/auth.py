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
from starlette.websockets import WebSocket

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
    "/api/greeks/calibrate",
    "/api/intelligence/headline",
    "/api/learning/evaluate-challenger"
}

# Public unauthenticated endpoints
PUBLIC_PATHS: Set[str] = {
    "/health",
    "/"
}


def is_websocket_authenticated(websocket: WebSocket) -> bool:
    """
    Validates WebSocket authentication before accept() is called.
    Accepts:
      - Query parameter: ?api_key=<key> or ?token=<key>
      - Headers: X-API-Key or Authorization: Bearer <key>
    """
    configured_key = os.environ.get("SERQ_API_KEY", "")

    # Extract candidate key
    provided_key = websocket.query_params.get("api_key") or websocket.query_params.get("token")
    if not provided_key:
        provided_key = websocket.headers.get("x-api-key")
    if not provided_key:
        auth_header = websocket.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            provided_key = auth_header[7:].strip()

    client_host = websocket.client.host if websocket.client else ""
    is_local = client_host in ("127.0.0.1", "localhost", "::1", "testclient")

    if configured_key:
        if provided_key and hmac.compare_digest(provided_key, configured_key):
            return True
        if is_local:
            return True
        logger.warning(
            f"WebSocket auth failed from {client_host}: invalid or missing API key"
        )
        return False

    # If no SERQ_API_KEY is configured, allow only local development loopback
    if not is_local:
        logger.warning(f"Blocked unauthenticated remote WebSocket connection from {client_host}")
        return False
    return True


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Validates API key for sensitive mutating operational endpoints and telemetry.
    Enforces X-API-Key or Authorization: Bearer <key> header.
    Rejects unauthorized requests with 401 Unauthorized or 403 Forbidden.
    """
    def __init__(self, app, api_key: Optional[str] = None):
        super().__init__(app)
        self.api_key = api_key or os.environ.get("SERQ_API_KEY", "")

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        # /health and root dashboard are public
        if path in PUBLIC_PATHS:
            return await call_next(request)

        # Allow stateless analytical calculate endpoints
        if path in ("/api/greeks/calculate", "/api/greeks/iv", "/api/greeks/screener"):
            return await call_next(request)

        # Check authorization header
        provided_key = request.headers.get("X-API-Key")
        auth_header = request.headers.get("Authorization", "")
        if not provided_key and auth_header.startswith("Bearer "):
            provided_key = auth_header[7:].strip()

        client_host = request.client.host if request.client else ""
        is_local = client_host in ("127.0.0.1", "localhost", "::1", "testclient")

        # Mutating endpoints strictly require authentication regardless of origin if SERQ_API_KEY is configured
        is_mutating = path in RESTRICTED_MUTATING_PATHS or (method == "POST" and path.startswith("/api/"))

        if is_mutating:
            if self.api_key:
                if not provided_key or not hmac.compare_digest(provided_key, self.api_key):
                    logger.warning(f"Unauthorized access attempt to {method} {path} from {client_host}")
                    return JSONResponse(
                        {"error": "Unauthorized: Valid API key required in X-API-Key or Authorization: Bearer header."},
                        status_code=401
                    )
            elif not is_local:
                logger.warning(f"Blocked unauthenticated external mutating request to {path} from {client_host}")
                return JSONResponse(
                    {"error": "Forbidden: Remote access requires SERQ_API_KEY to be configured."},
                    status_code=403
                )
        else:
            # Sensitive GET endpoints: require auth if remote; if local, allow without key unless key is passed
            if not is_local:
                if not self.api_key:
                    return JSONResponse(
                        {"error": "Forbidden: Remote telemetry access requires SERQ_API_KEY configuration."},
                        status_code=403
                    )
                if not provided_key or not hmac.compare_digest(provided_key, self.api_key):
                    return JSONResponse(
                        {"error": "Unauthorized: Remote access requires valid API key."},
                        status_code=401
                    )

        return await call_next(request)
