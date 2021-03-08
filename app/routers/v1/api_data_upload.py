import os
import time
import shutil
from fastapi import APIRouter, BackgroundTasks, Header, File, UploadFile, Form
from fastapi_utils import cbv
from ...models.base_models import APIResponse, EAPIResponseCode
from ...models.models_upload import PreUploadResponse, PreUploadPOST,\
    EDataType, ChunkUploadPOST, ChunkUploadResponse, OnSuccessUploadPOST, \
    GETJobStatusResponse
from ...models.fsm_file_upload import EState, FsmMgrUpload
from ...commons.logger_services.logger_factory_service import SrvLoggerFactory
from ...resources.error_handler import catch_internal, ECustomizedError, customized_error_template
from ...resources.helpers import set_status, get_status, \
    update_file_operation_logs, get_geid, get_project, send_to_queue, \
    delete_by_session_id, get_file_type
from ...models.file_data import SrvFileDataMgr
from ...models.tag import SrvTagsMgr
from ...config import ConfigClass

router = APIRouter()

_API_TAG = 'V1 Upload'
_API_NAMESPACE = "api_data_upload"


@cbv.cbv(router)
class APIUpload:
    '''
    API Upload Class
    '''

    def __init__(self):
        self.__logger = SrvLoggerFactory('api_data_upload').get_logger()

    @router.post("/files/jobs", tags=[_API_TAG], response_model=PreUploadResponse,
                 summary="Always would be called first when upload, \
                 Init an async upload job, returns generated job indentifier.")
    @catch_internal(_API_NAMESPACE)
    async def upload_pre(self, request_payload: PreUploadPOST, session_id=Header(None)):
        '''
        This method allow to create an async upload job
        '''
        # init resp
        _res = APIResponse()
        if not session_id:
            _res.code = EAPIResponseCode.bad_request
            _res.result = {}
            _res.error_msg = "Invalid Session ID: " + str(session_id)
            return _res.json_response()
        # get geid
        resumable_identifier = get_geid("upload")
        temp_dir = get_temp_dir(resumable_identifier)
        if request_payload.resumable_dataType == EDataType.SINGLE_FILE_DATA.name:
            project_info = get_project(request_payload.project_code)
            raw_folder_path = get_raw_folder_path(request_payload.project_code)
            file_full_path = os.path.join(
                raw_folder_path, request_payload.resumable_filename)
            # init status manager
            status_mgr = FsmMgrUpload(
                session_id,
                resumable_identifier,
                file_full_path,
                request_payload.project_code,
                request_payload.operator
            )
            try:
                # check if the file already exists
                if os.path.isfile(file_full_path):
                    error_msg = 'File %s already exists: ' % file_full_path
                    self.__logger.error(error_msg)
                    _res.code = EAPIResponseCode.conflict
                    _res.error_msg = error_msg
                    return _res.json_response()
                status_mgr.go(EState.INIT)
                # create temp dir
                if not os.path.isdir(temp_dir):
                    os.makedirs(temp_dir)
                # set preuploaded status
                job_recorded = status_mgr.go(EState.PRE_UPLOADED)
                _res.code = EAPIResponseCode.success
                _res.result = job_recorded
                return _res.json_response()
            except Exception as exce:
                # catch internal error
                status_mgr.set_payload({"error_msg": str(exce)})
                status_mgr.go(EState.TERMINATED)
                raise exce
        else:
            _res.code = EAPIResponseCode.bad_request
            _res.error_msg = "Invalid data type: {}".format(
                request_payload.resumable_dataType)
            return _res.json_response()

    @router.get("/files/jobs", tags=[_API_TAG], response_model=GETJobStatusResponse,
                summary="get upload job status")
    @catch_internal(_API_NAMESPACE)
    async def get_status(self, project_code,
                         operator, session_id: str = Header(None)):
        '''
        This method allow to check file upload status
        '''
        _res = APIResponse()
        if not session_id:
            _res.code = EAPIResponseCode.bad_request
            _res.result = {}
            _res.error_msg = "Invalid Session ID: " + str(session_id)
            return _res.json_response()
        job_fatched = get_status(
            session_id, "*", project_code, "data_upload", operator)
        found = False
        if len(job_fatched) > 0:
            # find target source
            found = True
        if found:
            _res.code = EAPIResponseCode.success
            _res.result = job_fatched
            return _res.json_response()
        else:
            _res.code = EAPIResponseCode.not_found
            _res.result = job_fatched
            _res.error_msg = customized_error_template(
                ECustomizedError.JOB_NOT_FOUND)
            return _res.json_response()

    @router.delete("/files/jobs", tags=[_API_TAG],
                   summary="Delete the upload job status.")
    @catch_internal(_API_NAMESPACE)
    async def clear_status(self, session_id: str = Header(None)):
        '''
        delete status by session id
        '''
        _res = APIResponse()
        if not session_id:
            _res.code = EAPIResponseCode.bad_request
            _res.result = {}
            _res.error_msg = "Invalid Session ID: " + str(session_id)
            return _res.json_response()
        delete_by_session_id(session_id, action="data_upload")
        _res.code = EAPIResponseCode.success
        _res.result = {
            "message": "Success"
        }
        return _res.json_response()

    @router.post("/files/chunks", tags=[_API_TAG], response_model=ChunkUploadResponse,
                 summary="upload chunks process.")
    @catch_internal(_API_NAMESPACE)
    async def upload_chunks(self,
                            project_code: str = Form(...),
                            operator: str = Form(...),
                            resumable_identifier: str = Form(...),
                            resumable_filename: str = Form(...),
                            resumable_dataType: str = Form(...),
                            resumable_chunk_number: int = Form(...),
                            resumable_total_chunks: int = Form(...),
                            resumable_total_size: int = Form(...),
                            tags: list = Form(...),
                            generate_id: str = Form(...),
                            session_id: str = Header(None),
                            chunk_data: UploadFile = File(...)):
        '''
        This method allow to upload file chunks
        '''
        # init resp
        _res = APIResponse()
        if not session_id:
            _res.code = EAPIResponseCode.bad_request
            _res.result = {}
            _res.error_msg = "Invalid Session ID: " + str(session_id)
            return _res.json_response()
        metadatas = {
            "generate_id": generate_id
        }
        temp_dir = get_temp_dir(resumable_identifier)
        raw_folder_path = get_raw_folder_path(project_code)
        file_full_path = os.path.join(
            raw_folder_path, resumable_filename)
        # init status manager
        status_mgr = FsmMgrUpload(
            session_id,
            resumable_identifier,
            file_full_path,
            project_code,
            operator
        )
        try:
            chunk_name = generate_chunk_name(
                resumable_filename, resumable_chunk_number)
            destination = os.path.join(temp_dir, chunk_name)
            self.__logger.info(
                'Start to save chunk {} to destination {}'.format(chunk_name, destination))
            save_file(destination, chunk_data)
        except Exception as exce:
            # catch internal error
            status_mgr.set_payload({"error_msg": str(exce)})
            status_mgr.go(EState.TERMINATED)
            raise exce
        _res.code = EAPIResponseCode.success
        _res.result = {
            "msg": "Succeed"
        }
        return _res.json_response()

    @router.post("/files", tags=[_API_TAG], response_model=PreUploadResponse,
                 summary="create a background worker to combine chunks, transfer file to the destination namespace")
    @catch_internal(_API_NAMESPACE)
    async def on_success(self, request_payload: OnSuccessUploadPOST,
                         background_tasks: BackgroundTasks,
                         session_id: str = Header(None)):
        '''
        This method allow to create a background worker to combine chunks uploaded
        '''
        # init resp
        _res = APIResponse()
        if not session_id:
            _res.code = EAPIResponseCode.bad_request
            _res.result = {}
            _res.error_msg = "Invalid Session ID: " + str(session_id)
            return _res.json_response()
        temp_dir = get_temp_dir(request_payload.resumable_identifier)
        raw_folder_path = get_raw_folder_path(request_payload.project_code)
        file_full_path = os.path.join(
            raw_folder_path, request_payload.resumable_filename)
        # init status manager
        status_mgr = FsmMgrUpload(
            session_id,
            request_payload.resumable_identifier,
            file_full_path,
            request_payload.project_code,
            request_payload.operator
        )
        self.__logger.info('File will be uploaded to %s' % raw_folder_path)
        chunk_paths = [
            os.path.join(
                temp_dir,
                generate_chunk_name(request_payload.resumable_filename, x)
            )
            for x in range(1, request_payload.resumable_total_chunks + 1)
        ]
        # add backgroud task
        background_tasks.add_task(finalize_worker, self.__logger, request_payload,
                                  status_mgr, chunk_paths, file_full_path, temp_dir)
        # set merging status
        job_recorded = status_mgr.go(EState.CHUNK_UPLOADED)
        _res.code = EAPIResponseCode.success
        _res.result = job_recorded
        return _res.json_response()


def get_raw_folder_path(project_code):
    # (optional) check if the folder is not existed
    raw_folder_path = os.path.join(
        ConfigClass.ROOT_PATH, project_code)
    raw_folder_path = os.path.join(raw_folder_path, "raw")
    # check raw folder path valid
    if not os.path.isdir(raw_folder_path):
        raise(Exception('Folder raw does not existed: %s' %
                        (raw_folder_path)))
    return raw_folder_path


def generate_chunk_name(uploaded_filename, chunk_number):
    '''
    generate chunk file name
    '''
    return uploaded_filename + '_part_%03d' % chunk_number


def get_temp_dir(resumable_identifier):
    '''
    get temp directory
    '''
    return os.path.join(ConfigClass.TEMP_BASE, resumable_identifier)


def save_file(dest: str, my_file: UploadFile):
    '''
    save file on the disk
    '''
    with open(dest, "wb") as buffer:
        shutil.copyfileobj(my_file.file, buffer)


def finalize_worker(logger,
                    request_payload: OnSuccessUploadPOST,
                    status_mgr: FsmMgrUpload,
                    chunk_paths: list,
                    target_file_full_path,
                    temp_dir):
    '''
    async zip worker
    '''
    try:
        # Upload task to combine file chunks and upload to nfs
        namespace = {
            "vre": "vrecore",
            "greenroom": "greenroom"
        }.get(
            os.environ.get('namespace')
        )
        target_head, target_tail = os.path.split(target_file_full_path)
        temp_merged_file_full_path = os.path.join(
            temp_dir, request_payload.resumable_filename)
        with open(temp_merged_file_full_path, 'ab') as temp_file:
            for p in chunk_paths:
                stored_chunk_file_name = p
                stored_chunk_file = open(stored_chunk_file_name, 'rb')
                temp_file.write(stored_chunk_file.read())
                stored_chunk_file.close()
                os.unlink(stored_chunk_file_name)
        logger.info('done with combinging chunks')
        # transfer to nfs
        shutil.move(temp_merged_file_full_path, target_head)
        # create entity file data
        file_meta_mgr = SrvFileDataMgr(logger)
        file_type = get_file_type()
        res_create_meta = file_meta_mgr.create(
            request_payload.operator,
            target_tail,
            target_head,
            request_payload.resumable_total_size,
            'Raw file in {}'.format(namespace),
            namespace,
            file_type,
            request_payload.project_code,
            request_payload.tags,
            request_payload.generate_id,
            operator=request_payload.operator,
            process_pipeline=request_payload.process_pipeline,
            from_parents=request_payload.from_parents)
        if res_create_meta.get('error'):
            logger.error("res_create_meta error: " + str(res_create_meta))
            raise Exception("res_create_meta error: " +
                            str(res_create_meta))
        else:
            logger.info('done with creating atlas record v2')
        # update tag frequence in redis
        project_id = get_project(request_payload.project_code)['result']['id']
        for tag in request_payload.tags:
            SrvTagsMgr().add_freq(project_id, tag)
        # send to queue
        payload = {
            "event_type": "data_uploaded",
            "payload": {
                "input_path": target_file_full_path,
                "project": request_payload.project_code,
                "generate_id": request_payload.generate_id,
                "uploader": request_payload.operator
            },
            "create_timestamp": time.time()
        }
        send_to_queue(payload, logger)
        # clean up tmp folder
        status_mgr.go(EState.FINALIZED)
        shutil.rmtree(temp_dir)
        status_mgr.go(EState.SUCCEED)
        # add upload logs
        update_file_operation_logs(
            request_payload.operator,
            request_payload.operator,
            target_file_full_path,
            request_payload.resumable_total_size,
            request_payload.project_code,
            request_payload.generate_id,
            extra={
                "upload_message": request_payload.upload_message
            }
        )

    except FileNotFoundError:
        error_msg = 'folder {} is already empty'.format(temp_dir)
        logger.warning(error_msg)

    except Exception as exce:
        # catch internal error
        logger.error(str(exce))
        status_mgr.set_payload({"error_msg": str(exce)})
        status_mgr.go(EState.TERMINATED)
        raise exce
