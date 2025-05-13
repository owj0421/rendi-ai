from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi import Request
from fastapi import APIRouter
from fastapi import Depends

from .api.v1 import (
    # advice,
    conversation,
    # predecessor
)
from .core.config import (
    settings
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.PROJECT_VERSION,
)

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
app.include_router(conversation.router, prefix="/api/v1")
# app.include_router(advice.router, prefix="/api/v1")
# app.include_router(predecessor.router, prefix="/api/v1")