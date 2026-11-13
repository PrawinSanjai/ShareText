import time
import hashlib
import uuid
from collections import defaultdict, deque

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response
from metrics import record_request


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_body_bytes: int):
        super().__init__(app)
        self.max_body_bytes = max_body_bytes

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        try:
            is_too_large = content_length and int(content_length) > self.max_body_bytes
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid Content-Length header."},
            )

        if is_too_large:
            return JSONResponse(
                status_code=413,
                content={"detail": "Request body is too large."},
            )

        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    REDIS_SCRIPT = """
    local now_parts = redis.call('TIME')
    local now = (tonumber(now_parts[1]) * 1000) + math.floor(tonumber(now_parts[2]) / 1000)
    local window = tonumber(ARGV[1])
    local max_requests = tonumber(ARGV[2])
    redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now - window)
    local count = redis.call('ZCARD', KEYS[1])
    if count >= max_requests then
        local oldest = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
        local retry_ms = math.max(1, tonumber(oldest[2]) + window - now)
        redis.call('PEXPIRE', KEYS[1], window)
        return {0, 0, retry_ms}
    end
    redis.call('ZADD', KEYS[1], now, ARGV[3])
    redis.call('PEXPIRE', KEYS[1], window)
    return {1, max_requests - count - 1, 0}
    """

    def __init__(self, app, max_requests: int, window_seconds: int):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        if request.url.path in {"/", "/health-check", "/docs", "/openapi.json", "/metrics"}:
            return await call_next(request)

        client_host = request.client.host if request.client else "unknown"
        client_hash = hashlib.sha256(client_host.encode("utf-8")).hexdigest()
        redis_client = getattr(request.app.state, "redis", None)

        if redis_client is not None:
            try:
                allowed, remaining, retry_ms = await redis_client.eval(
                    self.REDIS_SCRIPT,
                    1,
                    f"sharetext:ratelimit:v1:{client_hash}",
                    self.window_seconds * 1000,
                    self.max_requests,
                    uuid.uuid4().hex,
                )
            except Exception:
                return JSONResponse(
                    status_code=503,
                    content={"detail": "Request limiting is temporarily unavailable."},
                    headers={"Retry-After": "1"},
                )
            if not allowed:
                retry_seconds = max(1, (int(retry_ms) + 999) // 1000)
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Please try again later."},
                    headers={"Retry-After": str(retry_seconds), "X-RateLimit-Limit": str(self.max_requests), "X-RateLimit-Remaining": "0"},
                )
            remaining = int(remaining)
        else:
            # Process-local fallback is intended for development only.
            now = time.monotonic()
            window_start = now - self.window_seconds
            timestamps = self.requests[client_hash]
            while timestamps and timestamps[0] <= window_start:
                timestamps.popleft()
            if len(timestamps) >= self.max_requests:
                retry_seconds = max(1, int(timestamps[0] + self.window_seconds - now + 0.999))
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Please try again later."},
                    headers={"Retry-After": str(retry_seconds), "X-RateLimit-Limit": str(self.max_requests), "X-RateLimit-Remaining": "0"},
                )
            timestamps.append(now)
            remaining = self.max_requests - len(timestamps)
            if len(self.requests) > 50000:
                for old_key in list(self.requests)[:10000]:
                    self.requests.pop(old_key, None)

        response = await call_next(request)
        response.headers.setdefault("X-RateLimit-Limit", str(self.max_requests))
        response.headers.setdefault("X-RateLimit-Remaining", str(remaining))
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault("Cache-Control", "no-store")
        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/metrics":
            return await call_next(request)

        started = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            route = request.scope.get("route")
            route_name = getattr(route, "path", "unmatched")
            record_request(
                request.method,
                route_name,
                status,
                time.perf_counter() - started,
            )
