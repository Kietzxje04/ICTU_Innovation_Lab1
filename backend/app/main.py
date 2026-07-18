from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api import router
from .config import get_settings
from .database import SessionLocal, create_schema
from .exceptions import DomainError
from .seed import seed_cases
from .schemas import ApiError, ApiResponse


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_schema()
    session = SessionLocal()
    try:
        seed_cases(session)
    finally:
        session.close()
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, version="2.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request.state.request_id = request.headers.get("X-Request-Id", f"req-{uuid4().hex}")
    response = await call_next(request)
    response.headers["X-Request-Id"] = request.state.request_id
    return response


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError):
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiResponse(
            data=None,
            meta={"request_id": request.state.request_id, "api": "single-backend"},
            error=ApiError(code=exc.code, message=exc.message, details=exc.details),
        ).model_dump(mode="json"),
    )


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiResponse(
            data=None,
            meta={"request_id": request.state.request_id, "api": "single-backend"},
            error=ApiError(
                code=str(detail.get("code", "HTTP_ERROR")),
                message=str(detail.get("message", "Request failed")),
                details=detail,
            ),
        ).model_dump(mode="json"),
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=ApiResponse(
            data=None,
            meta={"request_id": request.state.request_id, "api": "single-backend"},
            error=ApiError(code="VALIDATION_ERROR", message="Request validation failed", details=exc.errors()),
        ).model_dump(mode="json"),
    )


app.include_router(router)
