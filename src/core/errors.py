from __future__ import annotations

import logging
from typing import Any

from fastapi import Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.exc import DBAPIError
from starlette.exceptions import HTTPException as StarletteHTTPException


logger = logging.getLogger(__name__)


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


DEFAULT_ERROR_RESPONSES = {
    status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
    status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
    status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
    status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    status.HTTP_409_CONFLICT: {"model": ErrorResponse},
    status.HTTP_429_TOO_MANY_REQUESTS: {"model": ErrorResponse},
    status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse},
}


class BusinessError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int,
        *,
        details: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        self.headers = headers
        super().__init__(message)


def business_error(
    code: str,
    message: str,
    status_code: int,
    *,
    details: Any | None = None,
    headers: dict[str, str] | None = None,
) -> BusinessError:
    return BusinessError(
        code,
        message,
        status_code,
        details=details,
        headers=headers,
    )


def not_found(code: str, message: str) -> BusinessError:
    return business_error(code, message, status.HTTP_404_NOT_FOUND)


def conflict(code: str, message: str) -> BusinessError:
    return business_error(code, message, status.HTTP_409_CONFLICT)


def bad_request(code: str, message: str) -> BusinessError:
    return business_error(code, message, status.HTTP_400_BAD_REQUEST)


def unauthorized(code: str, message: str) -> BusinessError:
    return business_error(
        code,
        message,
        status.HTTP_401_UNAUTHORIZED,
        headers={"WWW-Authenticate": "Bearer"},
    )


def forbidden(code: str, message: str) -> BusinessError:
    return business_error(code, message, status.HTTP_403_FORBIDDEN)


def too_many_requests(
    code: str,
    message: str,
    *,
    retry_after: int,
) -> BusinessError:
    return business_error(
        code,
        message,
        status.HTTP_429_TOO_MANY_REQUESTS,
        headers={"Retry-After": str(retry_after)},
    )


def _response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: Any | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    content = ErrorResponse(
        error=ErrorDetail(code=code, message=message, details=details)
    ).model_dump(exclude_none=True)
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(content),
        headers=headers,
    )


async def business_error_handler(
    request: Request,
    exc: BusinessError,
) -> JSONResponse:
    return _response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
        headers=exc.headers,
    )


async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return _response(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="VALIDATION_ERROR",
        message="Request validation failed",
        details=exc.errors(),
    )


async def http_error_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    if exc.status_code == status.HTTP_404_NOT_FOUND:
        code = "ROUTE_NOT_FOUND"
        message = "Route not found"
    elif exc.status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
        code = "METHOD_NOT_ALLOWED"
        message = "Method not allowed"
    else:
        code = f"HTTP_{exc.status_code}"
        message = str(exc.detail)
    return _response(
        status_code=exc.status_code,
        code=code,
        message=message,
        headers=exc.headers,
    )


async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "Unhandled request error request_id=%s method=%s path=%s",
        getattr(request.state, "request_id", "unknown"),
        request.method,
        request.url.path,
        exc_info=exc,
    )
    return _response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred",
    )


async def database_error_handler(request: Request, exc: DBAPIError) -> JSONResponse:
    logger.exception(
        "Database request error request_id=%s method=%s path=%s",
        getattr(request.state, "request_id", "unknown"),
        request.method,
        request.url.path,
        exc_info=exc,
    )
    mysql_error_code = None
    if exc.orig is not None and getattr(exc.orig, "args", None):
        mysql_error_code = exc.orig.args[0]

    if mysql_error_code in {1062, 1451, 1452, 3819}:
        return _response(
            status_code=status.HTTP_409_CONFLICT,
            code="DATABASE_CONSTRAINT_VIOLATION",
            message="The request conflicts with a database constraint",
        )
    return _response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="DATABASE_ERROR",
        message="A database error occurred",
    )


def install_error_handlers(app) -> None:
    app.add_exception_handler(BusinessError, business_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(DBAPIError, database_error_handler)
    app.add_exception_handler(Exception, internal_error_handler)
