import os
from fastapi import APIRouter
from ..config import ConfigClass

router = APIRouter()

# root api, for debuging


@router.get("/")
async def root():
    '''
    For testing if service's up
    '''
    return {"message": "Service-Upload-%s On, Version: " % os.environ.get('namespace', 'Local') + ConfigClass.version}
