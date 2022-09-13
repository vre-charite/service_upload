# Copyright 2022 Indoc Research
# 
# Licensed under the EUPL, Version 1.2 or – as soon they
# will be approved by the European Commission - subsequent
# versions of the EUPL (the "Licence");
# You may not use this work except in compliance with the
# Licence.
# You may obtain a copy of the Licence at:
# 
# https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12
# 
# Unless required by applicable law or agreed to in
# writing, software distributed under the Licence is
# distributed on an "AS IS" basis,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied.
# See the Licence for the specific language governing
# permissions and limitations under the Licence.
# 

from enum import Enum
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field

from .base_models import APIResponse


class EUploadJobType(Enum):
    AS_FOLDER = 'AS_FOLDER'
    AS_FILE = 'AS_FILE'


class SingleFileForm(BaseModel):
    resumable_filename: str
    resumable_relative_path: str = ''
    dcm_id: str = 'undefined'


class PreUploadPOST(BaseModel):
    """Pre upload payload model."""

    project_code: str
    operator: str
    job_type: str = 'AS_FOLDER | AS_FILE'
    folder_tags: List[str] = []
    data: List[SingleFileForm]
    upload_message = ''
    current_folder_node = ''
    incremental = False
    # do_conflict_check = True


class PreUploadResponse(APIResponse):
    """Pre upload response class."""

    result: dict = Field(
        {},
        example=[
            {
                'session_id': 'unique_session_2021',
                'job_id': '1bfe8fd8-8b41-11eb-a8bd-eaff9e667817-1616439732',
                'source': 'file1.png',
                'action': 'data_upload',
                'status': 'PRE_UPLOADED',
                'project_code': 'gregtest',
                'operator': 'zhengyang',
                'progress': 0,
                'payload': {
                    'resumable_identifier': '1bfe8fd8-8b41-11eb-a8bd-eaff9e667817-1616439732',
                    'parent_folder_geid': '1bcbe182-8b41-11eb-bf7a-eaff9e667817-1616439732',
                },
                'update_timestamp': '1616439731',
            },
            {
                'session_id': 'unique_session_2021',
                'job_id': '1c90ceac-8b41-11eb-bf7a-eaff9e667817-1616439733',
                'source': 'a/b/file1.png',
                'action': 'data_upload',
                'status': 'PRE_UPLOADED',
                'project_code': 'gregtest',
                'operator': 'zhengyang',
                'progress': 0,
                'payload': {
                    'resumable_identifier': '1c90ceac-8b41-11eb-bf7a-eaff9e667817-1616439733',
                    'parent_folder_geid': '1c67ba8a-8b41-11eb-845f-eaff9e667817-1616439733',
                },
                'update_timestamp': '1616439732',
            },
            {
                'session_id': 'unique_session_2021',
                'job_id': '1cfd235e-8b41-11eb-a8bd-eaff9e667817-1616439734',
                'source': 'a/b/c/file2.png',
                'action': 'data_upload',
                'status': 'PRE_UPLOADED',
                'project_code': 'gregtest',
                'operator': 'zhengyang',
                'progress': 0,
                'payload': {
                    'resumable_identifier': '1cfd235e-8b41-11eb-a8bd-eaff9e667817-1616439734',
                    'parent_folder_geid': '1cd44d62-8b41-11eb-8a88-eaff9e667817-1616439733',
                },
                'update_timestamp': '1616439733',
            },
            {
                'session_id': 'unique_session_2021',
                'job_id': '1d4696f6-8b41-11eb-8a88-eaff9e667817-1616439734',
                'source': 'a/b/c/file3.png',
                'action': 'data_upload',
                'status': 'PRE_UPLOADED',
                'project_code': 'gregtest',
                'operator': 'zhengyang',
                'progress': 0,
                'payload': {
                    'resumable_identifier': '1d4696f6-8b41-11eb-8a88-eaff9e667817-1616439734',
                    'parent_folder_geid': '1cd44d62-8b41-11eb-8a88-eaff9e667817-1616439733',
                },
                'update_timestamp': '1616439733',
            },
            {
                'session_id': 'unique_session_2021',
                'job_id': '1daf9192-8b41-11eb-8a88-eaff9e667817-1616439735',
                'source': 'a/b/c/d/file4.png',
                'action': 'data_upload',
                'status': 'PRE_UPLOADED',
                'project_code': 'gregtest',
                'operator': 'zhengyang',
                'progress': 0,
                'payload': {
                    'resumable_identifier': '1daf9192-8b41-11eb-8a88-eaff9e667817-1616439735',
                    'parent_folder_geid': '1d8a22cc-8b41-11eb-a8bd-eaff9e667817-1616439734',
                },
                'update_timestamp': '1616439734',
            },
            {
                'session_id': 'unique_session_2021',
                'job_id': '1e662e20-8b41-11eb-8a88-eaff9e667817-1616439736',
                'source': 'a/e/c/d/file4.png',
                'action': 'data_upload',
                'status': 'PRE_UPLOADED',
                'project_code': 'gregtest',
                'operator': 'zhengyang',
                'progress': 0,
                'payload': {
                    'resumable_identifier': '1e662e20-8b41-11eb-8a88-eaff9e667817-1616439736',
                    'parent_folder_geid': '1e3fa930-8b41-11eb-845f-eaff9e667817-1616439736',
                },
                'update_timestamp': '1616439735',
            },
        ],
    )


class ChunkUploadPOST(BaseModel):
    """chunk upload payload model."""

    project_code: str
    operator: str
    resumable_identifier: str
    resumable_filename: str
    resumable_chunk_number: int
    resumable_total_chunks: int
    resumable_total_size: float
    tags: List[str] = []
    dcm_id: str = 'undefined'
    metadatas: dict = None


class ChunkUploadResponse(APIResponse):
    """Pre upload response class."""

    result: dict = Field({}, example={'msg': 'Succeed'})


class OnSuccessUploadPOST(BaseModel):
    """merge chunks payload model."""

    project_code: str
    operator: str
    resumable_identifier: str
    resumable_filename: str
    resumable_relative_path: str
    resumable_total_chunks: int
    resumable_total_size: float
    tags: List[str] = []
    dcm_id: str = 'undefined'
    metadatas: dict = None
    process_pipeline: str = None
    from_parents: list = None
    upload_message = ''


class GETJobStatusResponse(APIResponse):
    """get Job status response class."""

    result: dict = Field(
        {},
        example=[
            {
                'session_id': 'unique_session',
                'job_id': 'upload-0a572418-7c2b-11eb-8428-be498ca98c54-1614780986',
                'source': '<path>',
                'action': 'data_upload',
                'status': 'PRE_UPLOADED | SUCCEED',
                'project_code': 'em0301',
                'operator': 'zhengyang',
                'progress': 0,
                'payload': {
                    'resumable_identifier': 'upload-0a572418-7c2b-11eb-8428-be498ca98c54-1614780986',
                    'parent_folder_geid': '1e3fa930-8b41-11eb-845f-eaff9e667817-1616439736',
                },
                'update_timestamp': '1614780986',
            }
        ],
    )


class POSTCombineChunksResponse(APIResponse):
    """get Job status response class."""

    result: dict = Field(
        {},
        example={
            'session_id': 'unique_session',
            'job_id': 'upload-0a572418-7c2b-11eb-8428-be498ca98c54-1614780986',
            'source': '<path>',
            'action': 'data_upload',
            'status': 'PRE_UPLOADED | SUCCEED',
            'project_code': 'em0301',
            'operator': 'zhengyang',
            'progress': 0,
            'payload': {
                'resumable_identifier': 'upload-0a572418-7c2b-11eb-8428-be498ca98c54-1614780986',
                'parent_folder_geid': '1e3fa930-8b41-11eb-845f-eaff9e667817-1616439736',
            },
            'update_timestamp': '1614780986',
        },
    )


class CreateFolderPOST(BaseModel):
    """create folder request payload model."""

    folder_name: str
    destination_geid: str
    zone: str = 'greenroom'
    project_code: str
    uploader: str
    tags: List[str] = []


class BulkCreateFolderPOST(BaseModel):
    """create folder request payload model."""

    folder_name: str
    destination_geid: Optional[str] = None
    zone: str
    project_code_list: List[str] = []
    uploader: str
    tags: List[str] = []


class BulkCreateFolderPOSTV2(BaseModel):
    """create folder request payload model."""

    zone: str
    folders: List[dict] = []


class CreateFolderPOSTResponse(APIResponse):
    """Response model for folder creation POST request."""

    result: dict = Field(
        {},
        example={
            'code': 200,
            'error_msg': '',
            'page': 0,
            'total': 1,
            'num_of_pages': 1,
            'result': {
                'id': 10170,
                'labels': ['Folder', 'Greenroom'],
                'name': 'test1',
                'time_created': '2021-05-05T22:33:49',
                'time_lastmodified': '2021-05-05T22:33:49',
                'global_entity_id': '9491b055-4c63-4987-9e1a-778dcec699ec-1620254029',
                'folder_level': 1,
                'folder_relative_path': '',
                'project_code': '04142',
                'tags': [],
                'list_priority': 10,
                'uploader': 'varsha',
            },
        },
    )
