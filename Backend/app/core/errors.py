from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def _correlation_id(request: Request) -> str:
    return getattr(request.state, "correlation_id", _request_id(request))


def _error_body(
    request: Request,
    code: str,
    message: str,
    details: list | None = None,
) -> dict:
    error: dict = {
        "code": code,
        "message": message,
        "request_id": _request_id(request),
        "correlation_id": _correlation_id(request),
    }
    if details is not None:
        error["details"] = details
    return {"error": error}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict) and "error" in detail:
            body = detail
            if isinstance(body["error"], dict):
                body["error"].setdefault("request_id", _request_id(request))
                body["error"].setdefault("correlation_id", _correlation_id(request))
        else:
            body = _error_body(request, "HTTP_ERROR", str(detail))
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = [
            {
                "field": ".".join(str(part) for part in err.get("loc", [])),
                "code": "INVALID_FIELD",
                "message": err.get("msg", "Invalid value"),
            }
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_body(
                request,
                "VALIDATION_FAILED",
                "One or more fields are invalid.",
                details=details,
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body(request, "INTERNAL_ERROR", "An unexpected error occurred."),
        )
