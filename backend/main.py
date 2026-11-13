import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from redis.asyncio import Redis

from config import Configuration
from middleware.security import (
    MetricsMiddleware,
    RateLimitMiddleware,
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)
from metrics import render_metrics
from router import text
from services.text import TextService

config = Configuration()
config.validate()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


async def delete_expired_texts():
    service = TextService()
    while True:
        try:
            # Keep deleting batches until there are no expired shares left.
            while await asyncio.to_thread(service.purge_expired):
                pass
        except Exception:
            logger.exception("expiry_cleanup_failed")
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_client = None
    if config.REDIS_URL:
        redis_client = Redis.from_url(
            config.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
        try:
            await redis_client.ping()
        except Exception:
            await redis_client.aclose()
            raise
        app.state.redis = redis_client
    else:
        logging.getLogger(__name__).warning(
            "REDIS_URL is not configured; rate limiting is local to this process"
        )
    cleanup_task = asyncio.create_task(delete_expired_texts())
    try:
        yield
    finally:
        cleanup_task.cancel()
        with suppress(asyncio.CancelledError):
            await cleanup_task
        if redis_client is not None:
            await redis_client.aclose()


api = FastAPI(title="share-text-backend", docs_url="/docs", lifespan=lifespan)

api.add_middleware(SecurityHeadersMiddleware)
api.add_middleware(
    RequestSizeLimitMiddleware,
    max_body_bytes=config.MAX_REQUEST_BODY_BYTES,
)
api.add_middleware(
    RateLimitMiddleware,
    max_requests=config.RATE_LIMIT_MAX_REQUESTS,
    window_seconds=config.RATE_LIMIT_WINDOW_SECONDS,
)
api.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)
api.add_middleware(MetricsMiddleware)


@api.get("/metrics", include_in_schema=False, response_class=PlainTextResponse)
def metrics():
    return PlainTextResponse(
        render_metrics(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@api.get("/")
def home():
    return {
        "result": "success",
        "message": "Please go to /docs.",
    }

@api.get("/health-check")
def healthcheck():
    return {
        "result": "success",
        "time": datetime.now(timezone.utc),
    }

api.include_router(text.router, prefix="/text", tags=["Text"])
