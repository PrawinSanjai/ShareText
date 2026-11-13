import hashlib
import time
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
        if content_length:
            try:
                too_large = int(content_length) > self.max_body_bytes
            except ValueError:
                return JSONResponse(
                    status_code=400,
                    content={"detail": "Invalid Content-Length header."},
                )

            if too_large:
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Request body is too large."},
                )

        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    EXEMPT_PATHS = {"/", "/health-check", "/docs", "/openapi.json", "/metrics"}

    def __init__(self, app, max_requests: int, window_seconds: int):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.local_requests = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        client_host = request.client.host if request.client else "unknown"
        client_id = hashlib.sha256(client_host.encode("utf-8")).hexdigest()
        redis_client = getattr(request.app.state, "redis", None)

        try:
            if redis_client is not None:
                count, retry_after = await self._count_with_redis(redis_client, client_id)
            else:
                count, retry_after = self._count_locally(client_id)
        except Exception:
            return JSONResponse(
                status_code=503,
                content={"detail": "Request limiting is temporarily unavailable."},
                headers={"Retry-After": "1"},
            )

        if count > self.max_requests:
            return self._too_many_requests(retry_after)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(self.max_requests - count)
        return response

    async def _count_with_redis(self, redis_client, client_id: str):
        # Use Redis time so every app instance agrees on the same time window.
        seconds, microseconds = await redis_client.time()
        now = seconds + microseconds / 1_000_000
        window_id = int(now // self.window_seconds)
        retry_after = self.window_seconds - int(now % self.window_seconds)
        key = f"sharetext:ratelimit:{client_id}:{window_id}"

        # INCR is atomic. The transaction also refreshes the key's cleanup TTL.
        async with redis_client.pipeline(transaction=True) as pipeline:
            pipeline.incr(key)
            pipeline.expire(key, self.window_seconds * 2)
            count, _ = await pipeline.execute()
        return count, retry_after

    def _count_locally(self, client_id: str):
        now = time.monotonic()
        window_start = now - self.window_seconds
        requests = self.local_requests[client_id]

        while requests and requests[0] <= window_start:
            requests.popleft()

        if len(requests) >= self.max_requests:
            retry_after = max(1, int(requests[0] + self.window_seconds - now + 0.999))
            return len(requests) + 1, retry_after

        requests.append(now)
        return len(requests), 0

    def _too_many_requests(self, retry_after: int):
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please try again later."},
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(self.max_requests),
                "X-RateLimit-Remaining": "0",
            },
        )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=()",
        )
        response.headers.setdefault("Cache-Control", "no-store")
        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/metrics":
            return await call_next(request)

        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            record_request(
                request.method,
                status_code,
                time.perf_counter() - started,
            )
