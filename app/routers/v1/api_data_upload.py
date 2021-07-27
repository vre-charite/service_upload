import os
import time
import shutil
import requests

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
    delete_by_session_id, generate_archive_preview
from ...models.folder import FolderMgr, FolderNode
from ...models.file_data import SrvFileDataMgr
from ...models.tag import SrvTagsMgr
from ...config import ConfigClass

router = APIRouter()

_API_TAG = 'V1 Upload'
_API_NAMESPACE = "api_data_upload"
_JOB_TYPE = "data_upload"


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
        job_list = []
        if not session_id:
            _res.code = EAPIResponseCode.bad_request
            _res.result = {}
            _res.error_msg = "Invalid Session ID: " + str(session_id)
            return _res.json_response()

        # check job type
        if request_payload.job_type == EUploadJobType.AS_FILE.name \
                or request_payload.job_type == EUploadJobType.AS_FOLDER.name:
            project_info = get_project(request_payload.project_code)
            if not project_info:
                _res.code = EAPIResponseCode.not_found
                _res.result = {}
                _res.error_msg = "Dataset not found"
                return _res.json_response()
            raw_folder_path = get_raw_folder_path(request_payload.project_code)
            created_folders_cache: List[FolderNode] = []
            task_id = get_geid()

            # filename converting
            for upload_data in request_payload.data:
                upload_data.resumable_filename = upload_data.generate_id + "_" + upload_data.resumable_filename \
                    if upload_data.generate_id and upload_data.generate_id != "undefined" \
                    else upload_data.resumable_filename

            # handle filename conflicts
            conflict_file_paths = get_conflict_file_paths(
                request_payload.data, request_payload.project_code)
            # also check the folder confilct. Note we might have the situation
            # that folder is same name but with different files
            conflict_folder_paths = get_conflict_folder_paths(
                request_payload.data, request_payload.project_code, request_payload.current_folder_node,
                request_payload.incremental) if request_payload.job_type == EUploadJobType.AS_FOLDER.name \
                else []

            if len(conflict_file_paths) > 0 or len(conflict_folder_paths) > 0:
                return response_conflic_folder_file_names(
                    _res, conflict_file_paths, conflict_folder_paths
                )

            for upload_data in request_payload.data:
                # create folder and folder nodes
                folder_mgr = FolderMgr(
                    created_folders_cache,
                    project_info["global_entity_id"],
                    request_payload.project_code,
                    raw_folder_path,
                    upload_data.resumable_relative_path,
                    request_payload.folder_tags)
                try:
                    folder_mgr.create(request_payload.operator)
                except FileExistsError as file_exist_error:
                    _res.code = EAPIResponseCode.conflict
                    _res.error_msg = str(file_exist_error)
                    return _res.json_response()
                last_folder_node_geid = folder_mgr.last_node.global_entity_id \
                    if folder_mgr.last_node else None
                # get job geid
                resumable_identifier = get_geid()
                temp_dir = get_temp_dir(resumable_identifier)
                file_full_path = os.path.join(
                    raw_folder_path, upload_data.resumable_relative_path,
                    upload_data.resumable_filename)
                relative_full_path = os.path.join(
                    upload_data.resumable_relative_path,
                    upload_data.resumable_filename)
                # init empty status manager
                status_mgr = FsmMgrUpload(
                    session_id,
                    request_payload.project_code,
                    _JOB_TYPE,
                    request_payload.operator,
                )
                # first time need to call set_job_id
                status_mgr.set_job_id(resumable_identifier)
                status_mgr.set_source(relative_full_path)
                status_mgr.add_payload(
                    "task_id", task_id)
                status_mgr.add_payload(
                    "resumable_identifier", resumable_identifier)
                status_mgr.add_payload(
                    "parent_folder_geid", last_folder_node_geid)
                try:
                    status_mgr.go(EState.INIT)
                    # create temp dir
                    if not os.path.isdir(temp_dir):
                        os.makedirs(temp_dir)
                    # set preuploaded status
                    job_recorded = status_mgr.go(EState.PRE_UPLOADED)
                    job_list.append(job_recorded)
                except Exception as exce:
                    # catch internal error
                    status_mgr.add_payload("error_msg", str(exce))
                    status_mgr.go(EState.TERMINATED)
                    raise exce
            _res.code = EAPIResponseCode.success
            _res.result = job_list
            return _res.json_response()
        else:
            _res.code = EAPIResponseCode.bad_request
            _res.error_msg = "Invalid job type: {}".format(
                request_payload.job_type)
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
        job_fatched = session_job_get_status(
            session_id, "*", project_code, _JOB_TYPE, operator)
        _res.code = EAPIResponseCode.success
        _res.result = job_fatched
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
        delete_by_session_id(session_id, action=_JOB_TYPE)
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
                            resumable_relative_path: str = Form(""),
                            resumable_chunk_number: int = Form(...),
                            resumable_total_chunks: int = Form(...),
                            resumable_total_size: int = Form(...),
                            tags: list = Form([]),
                            generate_id: str = Form("undefined"),
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
        # check generate id
        resumable_filename = generate_id + "_" + resumable_filename \
            if generate_id and generate_id != "undefined" else resumable_filename
        temp_dir = get_temp_dir(resumable_identifier)
        raw_folder_path = get_raw_folder_path(project_code)
        file_full_path = os.path.join(
            raw_folder_path, resumable_relative_path, resumable_filename)
        relative_full_path = os.path.join(
            resumable_relative_path, resumable_filename)
        # init status manager
        status_mgr = FsmMgrUpload(
            session_id,
            project_code,
            _JOB_TYPE,
            operator,
            resumable_identifier,
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
            status_mgr.add_payload("error_msg", str(exce))
            status_mgr.go(EState.TERMINATED)
            raise exce
        _res.code = EAPIResponseCode.success
        _res.result = {
            "msg": "Succeed"
        }
        return _res.json_response()

    @router.post("/files", tags=[_API_TAG], response_model=POSTCombineChunksResponse,
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

        # check generate id
        request_payload.resumable_filename = request_payload.generate_id + "_" + request_payload.resumable_filename \
            if request_payload.generate_id and request_payload.generate_id != "undefined" \
            else request_payload.resumable_filename

        temp_dir = get_temp_dir(request_payload.resumable_identifier)
        raw_folder_path = get_raw_folder_path(request_payload.project_code)
        file_full_path = os.path.join(
            raw_folder_path, request_payload.resumable_relative_path,
            request_payload.resumable_filename)
        relative_full_path = os.path.join(
            request_payload.resumable_relative_path,
            request_payload.resumable_filename)

        # init status manager
        status_mgr = FsmMgrUpload(
            session_id,
            request_payload.project_code,
            _JOB_TYPE,
            request_payload.operator,
            request_payload.resumable_identifier,
        )
        self.__logger.info('File will be uploaded to %s' % raw_folder_path)
        chunk_paths = [
            os.path.join(
                temp_dir,
                generate_chunk_name(request_payload.resumable_filename, x)
            )
            for x in range(1, request_payload.resumable_total_chunks + 1)
        ]

        # add backgroud task to combine all recieved chunks
        background_tasks.add_task(finalize_worker, self.__logger, request_payload,
                                  status_mgr, chunk_paths, file_full_path, temp_dir)
        # set merging status
        job_recorded = status_mgr.go(EState.CHUNK_UPLOADED)
        _res.code = EAPIResponseCode.success
        _res.result = job_recorded
        return _res.json_response()


def get_raw_folder_path(project_code):
    namespace = os.environ.get('namespace')
    # (optional) check if the folder is not existed
    raw_folder_path = os.path.join(
        ConfigClass.ROOT_PATH, project_code)
    if namespace == "vre" or namespace == "vrecore":
        raw_folder_path = os.path.join(raw_folder_path)
    elif namespace == "greenroom":
        # we decide to remove the raw folder for now it will upload 
        # to the /project_code/
        # raw_folder_path = os.path.join(raw_folder_path, "raw")
        raw_folder_path = os.path.join(raw_folder_path)

        # os.makedirs(raw_folder_path)
    # check raw folder path valid
    if not os.path.isdir(raw_folder_path):
        raise(Exception('Folder raw does not existed: %s' %
                        raw_folder_path))
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

        # here now we dont deprecate the nfs completely
        # so we need to do some overwrite if the file exist
        target_path = os.path.join(target_head, request_payload.resumable_filename)
        shutil.move(temp_merged_file_full_path, target_path)

        # for backup also sync to minio
        logger.info("Minio Connection Test")
        # format the bucket name and minio path
        bucket = ("core-" if namespace == "vrecore" else "gr-") + request_payload.project_code
        relative_path = target_file_full_path.replace(ConfigClass.ROOT_PATH, '')
        _, obj_path = tuple(relative_path[1:].split('/', 1))
        file_path = target_head + "/" + target_tail 

        # since now we have the user node, remove this join
        # obj_path = os.path.join(request_payload.operator, obj_path)
        
        version_id = ""
        # after use the minio the generate pipeline will also use the minio location
        minio_http = ("https://" if ConfigClass.MINIO_HTTPS else "http://") + ConfigClass.MINIO_ENDPOINT
        minio_location = "minio://%s/%s/%s"%(minio_http, bucket, obj_path)
        # minio_location = minio_location.encode('utf-8')
        try:
            mc = Minio_Client()
            logger.info("Minio Connection Success")

            result = mc.client.fput_object(
                bucket, obj_path, os.path.join(target_head, request_payload.resumable_filename), 
            )
            version_id = result.version_id
            logger.info("Minio Upload Success")
        except Exception as e:
            logger.error("error when uploading: "+str(e))

        # create entity file data
        file_meta_mgr = SrvFileDataMgr(logger)
        res_create_meta = file_meta_mgr.create(
            request_payload.operator,
            target_tail,
            target_head,
            request_payload.resumable_total_size,
            'Raw file in {}'.format(namespace),
            namespace,
            request_payload.project_code,
            request_payload.tags,
            request_payload.generate_id,
            bucket,             # minio attribute
            obj_path,           # minio attribute
            version_id,  # minio attribute
            operator=request_payload.operator,
            process_pipeline=request_payload.process_pipeline,
            from_parents=request_payload.from_parents,
            parent_folder_geid=status_mgr.payload['parent_folder_geid'])
        if res_create_meta.get('error'):
            logger.error("res_create_meta error: " + str(res_create_meta))
            raise Exception("res_create_meta error: " +
                            str(res_create_meta))
        else:
            logger.info('done with creating atlas record v2')
        # get created entity
        created_entity = res_create_meta["result"]

        # Store zip file preview in postgres
        try:
            file_type = os.path.splitext(file_path)[1]
            if file_type == ".zip":
                archive_preview = generate_archive_preview(file_path)
                payload = {
                    "archive_preview": archive_preview,
                    "file_geid": created_entity["global_entity_id"],
                }
                response = requests.post(ConfigClass.DATA_OPS_GR + "archive", json=payload)
        except Exception as e:
            geid = created_entity["global_entity_id"]
            logger.info(f'Error adding file preview for {geid}: {str(e)}')

        
        # update full path to Greenroom/<display_path>
        obj_path = ("VRECore/" if namespace == "vrecore" else "Greenroom/") + obj_path
        # add upload logs
        update_file_operation_logs(
            request_payload.operator,
            request_payload.operator,
            obj_path, 
            request_payload.resumable_total_size,
            request_payload.project_code,
            request_payload.generate_id,
            extra={
                "upload_message": request_payload.upload_message
            }
        )
        # update tag frequence in redis
        project_id = get_project(request_payload.project_code)['id']
        for tag in request_payload.tags:
            SrvTagsMgr().add_freq(project_id, tag)
        # send to queue
        payload = {
            "event_type": "data_uploaded",
            "payload": {
                "input_path": minio_location, # update to minio
                "project": request_payload.project_code,
                "generate_id": request_payload.generate_id,
                "uploader": request_payload.operator,
                "source_geid": created_entity["global_entity_id"]
            },
            "create_timestamp": time.time()
        }
        send_to_queue(payload, logger)
        logger.info('sent to queue.')
        # clean up tmp folder
        status_mgr.go(EState.FINALIZED)
        try:
            shutil.rmtree(temp_dir)
        except Exception as exce:
            logger.info("Upload on succeed rmtree error: " + str(exce))
        try:
            status_mgr.add_payload(
                "source_geid",  created_entity["global_entity_id"])
            status_mgr.go(EState.SUCCEED)
        except Exception as exce:
            logger.info("Upload on succeed set status as succeed error: " + str(exce))
        logger.info('Upload Job Done.')

    except FileNotFoundError:
        error_msg = 'folder {} is already empty'.format(temp_dir)
        logger.warning(error_msg)

    except Exception as exce:
        # catch internal error
        logger.error(str(exce))
        status_mgr.set_payload({"error_msg": str(exce)})
        status_mgr.go(EState.TERMINATED)
        raise exce


def get_root_folder(folder_path):
    '''
    recursively get rootfolder
    '''
    if not os.path.dirname(folder_path):
        return folder_path
    else:
        parent_folder = os.path.dirname(folder_path)
        return get_root_folder(parent_folder)


def get_conflict_folder_paths(data, project_code, current_folder_node, incremental):
    '''
    return conflict folder paths
    '''
    namespace = os.environ.get('namespace')

    # to speed up the loop -> change the array to set
    # to remove the duplicate folder name check
    folder_set = set()
    for upload_data in data:
        # check folder name
        dp = current_folder_node if current_folder_node \
            else get_root_folder(upload_data.resumable_relative_path)
        folder_set.add(dp)

    conflict_folder_paths = []
    for display_path in folder_set:
        payload = {
            'display_path': display_path,
            'project_code': project_code,
            'archived': False
        }
        # also check if it is in greeroom or core
        neo4j_zone_label = "VRECore" if namespace == "vre" else "Greenroom"
        node_query_url = ConfigClass.NEO4J_SERVICE + "nodes/%s/query"%neo4j_zone_label
        response = requests.post(node_query_url, json=payload)
        if len(response.json()) > 0:
            conflict_folder_paths.append({
                "name": display_path,
                "relative_path": upload_data.resumable_relative_path,
                "type": "Folder"
            })

            break
    return conflict_folder_paths


def get_conflict_file_paths(data, project_code):
    '''
    return conflict file path
    '''
    namespace = os.environ.get('namespace')
    conflict_file_paths = []
    for upload_data in data:
        # file_full_path = os.path.join(
        #     file_path, upload_data.resumable_relative_path,
        #     upload_data.resumable_filename)
        # if os.path.exists(file_full_path):
        #     conflict_file_paths.append({
        #         "name": upload_data.resumable_filename,
        #         "relative_path": upload_data.resumable_relative_path,
        #         "type": "File"
        #     })

        # now we have to use the neo4j to check duplicate
        display_path = upload_data.resumable_relative_path+'/'+upload_data.resumable_filename
        payload = {
            'display_path': display_path,
            'project_code': project_code,
            'archived': False
        }
        # also check if it is in greeroom or core
        neo4j_zone_label = "VRECore" if namespace == "vre" else "Greenroom"
        node_query_url = ConfigClass.NEO4J_SERVICE + "nodes/%s/query"%neo4j_zone_label
        response = requests.post(node_query_url, json=payload)
        
        if len(response.json()) > 0:
            conflict_file_paths.append({
                "name": upload_data.resumable_filename,
                "relative_path": upload_data.resumable_relative_path,
                "type": "File"
            })


    return conflict_file_paths





def response_conflic_folder_file_names(_res, conflict_file_paths, conflict_folder_paths):
    '''
    set conflict response when filename or folder name conflics
    '''
    # conflict file names
    if len(conflict_file_paths) > 0:
        _res.code = EAPIResponseCode.conflict
        _res.error_msg = customized_error_template(
            ECustomizedError.INVALID_FILENAME)
        _res.result = {
            "failed": conflict_file_paths
        }
        return _res.json_response()
    # conflict folder names
    if len(conflict_folder_paths) > 0:
        _res.code = EAPIResponseCode.conflict
        _res.error_msg = customized_error_template(
            ECustomizedError.INVALID_FOLDERNAME)
        _res.result = {
            "failed": conflict_folder_paths
        }
        return _res.json_response()
