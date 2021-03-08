import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import ConfigClass
from .api_registry import api_registry


def create_app():
    '''
    create app function
    '''
    app = FastAPI(
        title="Service Data Upload %s" % (os.environ.get('namespace', 'local')),
        description="Service for data upload usage",
        docs_url="/v1/api-doc",
        version=ConfigClass.version
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins="*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API registry
    # v1
    api_registry(app)

    return app
