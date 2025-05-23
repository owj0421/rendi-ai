from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi import Request
from fastapi import APIRouter
from fastapi import Depends

from .api.v1 import (
    conversation,
)
from .core import (
    config,
    exceptions
)


app = FastAPI(
    title=config.settings.PROJECT_NAME,
    description=config.settings.PROJECT_DESCRIPTION,
    version=config.settings.PROJECT_VERSION,
)


# Exception handlers
app.add_exception_handler(Exception, exceptions.general_exception_handler)
app.add_exception_handler(exceptions.HTTPException, exceptions.http_exception_handler)


# CORS settings
# origins = [
#     "http://localhost",
#     "http://localhost:3000",
#     "http://127.0.0.1:3000",
# ]
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

@app.get("/")
async def root():
    return {"message": "Hello World"}
    
# Include routers
app.include_router(
    conversation.router, 
    prefix="/api/v1"
)