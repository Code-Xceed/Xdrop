from fastapi import APIRouter
from .routes_analyze import router as analyze_router
from .routes_download import router as download_router
from .routes_library import router as library_router
from .routes_settings import router as settings_router
from .routes_resolve import router as resolve_router
from .routes_premiere import router as premiere_router
from .routes_aftereffects import router as aftereffects_router
from .routes_editors import router as editors_router
from .websocket import router as ws_router

api_router = APIRouter()
api_router.include_router(analyze_router)
api_router.include_router(download_router)
api_router.include_router(library_router)
api_router.include_router(settings_router)
api_router.include_router(resolve_router)
api_router.include_router(premiere_router)
api_router.include_router(aftereffects_router)
api_router.include_router(editors_router)
api_router.include_router(ws_router)

__all__ = ["api_router"]
