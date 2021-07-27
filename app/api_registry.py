from fastapi import FastAPI
from .routers import api_root
from .routers.v1 import api_data_upload, api_folder_creation
from .routers.v2 import api_data_upload_v2


def api_registry(app: FastAPI):
    app.include_router(api_root.router)
    app.include_router(api_data_upload.router, prefix="/v1")
    app.include_router(api_folder_creation.router, prefix="/v1")
    app.include_router(api_data_upload_v2.router, prefix="/v2")