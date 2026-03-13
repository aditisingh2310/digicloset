from __future__ import annotations

import logging
import traceback
from typing import Any, Dict

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ErrorResponse(BaseModel):
    """Canonical API error payload used across all routes."""

    error: str
    code: int
    request_id: str | None = None
    details: Dict[str, Any] | None = None


def _request_context(request: Request) -> tuple[str | None, str | None]:
    request_id = getattr(request.state, "request_id", None)
    tenant = getattr(request.state, "tenant", None)
    shop_domain = getattr(tenant, "shop_domain", None) if tenant else None
    return request_id, shop_domain


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Normalize HTTPException output while preserving status code."""

    request_id, shop_domain = _request_context(request)
    logger.info(
        "HTTP exception: %s",
        exc.detail,
        extra={"request_id": request_id, "shop_domain": shop_domain, "status_code": exc.status_code},
    )

    payload = ErrorResponse(
        error="http_error",
        code=exc.status_code,
        request_id=request_id,
        details={"detail": exc.detail},
    )
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump())


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Normalize FastAPI request validation failures."""

    request_id, shop_domain = _request_context(request)
    logger.warning(
        "Validation error",
        extra={"request_id": request_id, "shop_domain": shop_domain, "errors": exc.errors()},
    )

    payload = ErrorResponse(
        error="validation_error",
        code=422,
        request_id=request_id,
        details={"errors": exc.errors()},
    )
    return JSONResponse(status_code=422, content=payload.model_dump())


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unhandled exceptions."""

    request_id, shop_domain = _request_context(request)
    logger.error(
        "Unhandled exception: %s",
        exc,
        extra={"request_id": request_id, "shop_domain": shop_domain},
    )
    logger.debug(traceback.format_exc())

    payload = ErrorResponse(error="internal_server_error", code=500, request_id=request_id)
    return JSONResponse(status_code=500, content=payload.model_dump())
