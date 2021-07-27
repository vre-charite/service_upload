import os
import time
import shutil
from typing import List
from fastapi import APIRouter, BackgroundTasks, Header, File, UploadFile, Form
from fastapi_utils import cbv
from ...models.base_models import APIResponse, EAPIResponseCode
from ...models.models_upload import PreUploadResponse, PreUploadPOST,\
    EUploadJobType, ChunkUploadPOST, ChunkUploadResponse, OnSuccessUploadPOST, \
    GETJobStatusResponse, POSTCombineChunksResponse, SingleFileForm
from ...models.fsm_file_upload import EState, FsmMgrUpload
from ...commons.logger_services.logger_factory_service import SrvLoggerFactory
from ...commons.data_providers import session_job_get_status
from ...commons.service_connection.minio_client import Minio_Client
from ...resources.error_handler import catch_internal, ECustomizedError, customized_error_template
from ...resources.helpers import update_file_operation_logs, get_geid, get_project, send_to_queue, \
    delete_by_session_id
from ...models.folder import FolderMgr, FolderNode
from ...models.file_data import SrvFileDataMgr
from ...models.tag import SrvTagsMgr
from ...config import ConfigClass
import datetime

router = APIRouter()

_API_TAG = 'V2 Upload'
_API_NAMESPACE = "api_data_upload"
_JOB_TYPE = "data_upload"

@cbv.cbv(router)
class APIUploadV2:
    '''
    API Upload Class V2
    '''

    def __init__(self):
        self.__logger = SrvLoggerFactory(_API_NAMESPACE).get_logger()

    @router.get("/upload/{bucket}/object/{object_path}", tags=[_API_TAG],
                 summary="temperary api here, generate presigned upload url")
    @catch_internal(_API_NAMESPACE)
    async def upload_pre(self, bucket:str, object_path:str):

        # init resp
        _res = APIResponse()

        self.__logger.info('[data_pre_upload] {} {}'.format(bucket, object_path))

        mc = Minio_Client()
        presigned_upload_url = mc.client.presigned_put_object(bucket, object_path)

        if ConfigClass.env != 'dev':
            presigned_upload_url = presigned_upload_url.split('//', 2)[-1]
            presigned_upload_url = 'https://' + presigned_upload_url

        _res.code = EAPIResponseCode.success
        _res.result = presigned_upload_url
        return _res.json_response()