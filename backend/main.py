import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

from config import Configuration
from middleware.security import (
    RateLimitMiddleware,
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)
from router import (
    auth,
    text
)

config = Configuration()
config.validate()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

api = FastAPI(title="share-text-backend", docs_url="/docs")

api.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)
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


@api.get("/")
def home():
    return {
        "result": "success",
        "message": "Please Go To /Docs"
    }

@api.get("/health-check")
def healthcheck():
    return {
        "result": "success",
        "time": datetime.now()
    }

# api.include_router(auth.router, tags=["Auth"])
api.include_router(text.router, prefix="/text", tags=["Text"])
