from enum import Enum
from pydantic import BaseModel, Field
from .base_models import APIResponse


class EDataType(Enum):
    SINGLE_FILE_DATA = 1
    BITS_FILE_DATA = 5


class PreUploadPOST(BaseModel):
    '''
    Pre upload payload model
    '''
    project_code: str
    operator: str
    resumable_filename: str
    resumable_dataType: str = EDataType.SINGLE_FILE_DATA.name
    upload_message = ""


class PreUploadResponse(APIResponse):
    '''
    Pre upload response class
    '''
    result: dict = Field({}, example={
        "session_id": "unique_session",
        "job_id": "upload-0a572418-7c2b-11eb-8428-be498ca98c54-1614780986",
        "source": "/data/vre-storage/em0301/raw/test_file_01",
        "action": "data_upload",
        "status": "PRE_UPLOADED | SUCCEED",
        "project_code": "em0301",
        "operator": "zhengyang",
        "progress": 0,
        "payload": {
            "resumable_identifier": "upload-0a572418-7c2b-11eb-8428-be498ca98c54-1614780986"
        },
        "update_timestamp": "1614780986"
    }
    )


class ChunkUploadPOST(BaseModel):
    '''
    chunk upload payload model
    '''
    project_code: str
    operator: str
    resumable_identifier: str
    resumable_filename: str
    resumable_dataType: str = EDataType.SINGLE_FILE_DATA.name
    resumable_chunk_number: int
    resumable_total_chunks: int
    resumable_total_size: float
    tags: list = []
    generate_id: str = "undefined"
    metadatas: dict = None


class ChunkUploadResponse(APIResponse):
    '''
    Pre upload response class
    '''
    result: dict = Field({}, example={
        "msg": "Succeed"
    }
    )


class OnSuccessUploadPOST(BaseModel):
    '''
    merge chunks payload model
    '''
    project_code: str
    operator: str
    resumable_identifier: str
    resumable_filename: str
    resumable_dataType: str = EDataType.SINGLE_FILE_DATA.name
    resumable_total_chunks: int
    resumable_total_size: float
    tags: list = []
    generate_id: str = "undefined"
    metadatas: dict = None
    process_pipeline: str = None
    from_parents: list = None
    upload_message = ""


class GETJobStatusResponse(APIResponse):
    '''
    get Job status response class
    '''
    result: dict = Field({}, example=[
        {
            "session_id": "unique_session",
            "job_id": "upload-0a572418-7c2b-11eb-8428-be498ca98c54-1614780986",
            "source": "/data/vre-storage/em0301/raw/test_file_01",
            "action": "data_upload",
            "status": "PRE_UPLOADED | SUCCEED",
            "project_code": "em0301",
            "operator": "zhengyang",
            "progress": 0,
            "payload": {
                "resumable_identifier": "upload-0a572418-7c2b-11eb-8428-be498ca98c54-1614780986"
            },
            "update_timestamp": "1614780986"
        }
    ]
    )
