from fastapi import FastAPI
from .routers import api_root
from .routers.v1 import api_data_upload

def api_registry(app: FastAPI):
    app.include_router(api_root.router)
    app.include_router(api_data_upload.router, prefix="/v1")