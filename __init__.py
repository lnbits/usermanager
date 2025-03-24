from fastapi import APIRouter
from loguru import logger

from .crud import db
from .views import usermanager_generic_router
from .views_api import usermanager_api_router

logger.debug("usermanager ext running.")

usermanager_ext: APIRouter = APIRouter(prefix="/usermanager", tags=["usermanager"])
usermanager_ext.include_router(usermanager_generic_router)
usermanager_ext.include_router(usermanager_api_router)

usermanager_static_files = [
    {
        "path": "/usermanager/static",
        "name": "usermanager_static",
    }
]

__all__ = [
    "db",
    "usermanager_ext",
    "usermanager_static_files",
]
