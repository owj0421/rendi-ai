from . import logger
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from starlite import Response, status_codes
from starlette.requests import Request


async def http_exception_handler(request: Request, exc: HTTPException):
    # logger.logger.warning(f"HTTPException: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )
    
    
async def general_exception_handler(request: Request, exc: Exception):
    # logger.logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Failed to initialize conversation due to server error."},
    )