from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

from router import (
    auth,
    text
)

api = FastAPI(title="textie-backend", docs_url="/docs")

api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
