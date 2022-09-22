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

import os
import shutil
import time
import unicodedata as ud
from typing import List
from typing import Optional

import httpx
from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import File
from fastapi import Form
from fastapi import Header
from fastapi import UploadFile
from fastapi_utils import cbv
from starlette.concurrency import run_in_threadpool

from app.commons.data_providers import SrvAioRedisSingleton
from app.commons.data_providers import session_job_get_status
from app.commons.logger_services.logger_factory_service import SrvLoggerFactory
from app.commons.service_connection.minio_client import Minio_Client_
from app.config import ConfigClass
from app.models.base_models import APIResponse
from app.models.base_models import EAPIResponseCode
from app.models.file_data import SrvFileDataMgr
from app.models.folder import FolderMgr
from app.models.folder import FolderNode
from app.models.folder import batch_create_4j_foldernodes
from app.models.folder import batch_link_folders
from app.models.fsm_file_upload import EState
from app.models.fsm_file_upload import FsmMgrUpload
from app.models.fsm_file_upload import get_fsm_object
from app.models.models_upload import ChunkUploadResponse
from app.models.models_upload import EUploadJobType
from app.models.models_upload import GETJobStatusResponse
from app.models.models_upload import OnSuccessUploadPOST
from app.models.models_upload import POSTCombineChunksResponse
from app.models.models_upload import PreUploadPOST
from app.models.models_upload import PreUploadResponse
from app.resources.error_handler import ECustomizedError
from app.resources.error_handler import catch_internal
from app.resources.error_handler import customized_error_template
from app.resources.helpers import async_get_geid
from app.resources.helpers import delete_by_session_id
from app.resources.helpers import generate_archive_preview
from app.resources.helpers import get_project
from app.resources.helpers import send_to_queue
from app.resources.helpers import update_file_operation_logs
from app.resources.lock import async_lock_resource
from app.resources.lock import async_unlock_resource
from app.resources.lock import unlock_resource

router = APIRouter()

_API_TAG = 'V1 Upload'
_API_NAMESPACE = 'api_data_upload'
_JOB_TYPE = 'data_upload'


@cbv.cbv(router)
class APIUpload:
    """API Upload Class."""

    def __init__(self):
        self.__logger = SrvLoggerFactory('api_data_upload').get_logger()

    @router.post(
        '/files/jobs',
        tags=[_API_TAG],
        response_model=PreUploadResponse,
        summary='Always would be called first when upload, \
                 Init an async upload job, returns job identifier.',
    )
    @catch_internal(_API_NAMESPACE)
    async def upload_pre(self, request_payload: PreUploadPOST, session_id=Header(None)):
        """This method allow to create an async upload job."""
        # init resp
        _res = APIResponse()
        job_list = []
        redis_srv = SrvAioRedisSingleton()
        redis_pipeline = await redis_srv.get_pipeline()
        to_create_folders = []
        folder_relations = []
        conflict_file_paths = []
        conflict_folder_paths = []
        if not session_id:
            _res.code = EAPIResponseCode.bad_request
            _res.result = {}
            # This msg doesnt make sense as session_id is None
            _res.error_msg = 'Invalid Session ID: ' + str(session_id)
            return _res.json_response()
        # check job type
        if (
            request_payload.job_type == EUploadJobType.AS_FILE.name
            or request_payload.job_type == EUploadJobType.AS_FOLDER.name
        ):
            project_info = await get_project(request_payload.project_code)
            if not project_info:
                """this will never happens because project_code is a mandory field."""
                _res.code = EAPIResponseCode.not_found
                _res.result = {}
                _res.error_msg = 'Container or Dataset not found'
                return _res.json_response()
            # raw_folder_path = get_raw_folder_path(request_payload.project_code)
            created_folders_cache: List[FolderNode] = []
            task_id = await async_get_geid()

            # filename converting
            for upload_data in request_payload.data:
                # here I have to update the special character into NFC form
                # since some of the browser will encode them into NFD form
                # for the bug detail. Please check the 2244
                upload_data.resumable_filename = ud.normalize('NFC', upload_data.resumable_filename)
                upload_data.resumable_filename = (
                    upload_data.dcm_id + '_' + upload_data.resumable_filename
                    if upload_data.dcm_id and upload_data.dcm_id != 'undefined'
                    else upload_data.resumable_filename
                )

            # handle filename conflicts
            # if request_payload.do_conflict_check:
            if request_payload.job_type == EUploadJobType.AS_FILE.name:
                conflict_file_paths = await get_conflict_file_paths(request_payload.data, request_payload.project_code)

            # also check the folder confilct. Note we might have the situation
            # that folder is same name but with different files
            if request_payload.job_type == EUploadJobType.AS_FOLDER.name:
                conflict_folder_paths = (
                    (
                        await get_conflict_folder_paths(
                            request_payload.data,
                            request_payload.project_code,
                            request_payload.current_folder_node,
                            request_payload.incremental,
                        )
                    )
                    if request_payload.job_type == EUploadJobType.AS_FOLDER.name
                    else []
                )

            if len(conflict_file_paths) > 0 or len(conflict_folder_paths) > 0:
                return response_conflic_folder_file_names(_res, conflict_file_paths, conflict_folder_paths)

            #######################################################

            namespace = ConfigClass.disk_namespace

            # TODO SOMEHOW REFACTOR HERE
            # this variable will be across the file node AND the folder node
            # to record which node is locked. in case there is a error, we can
            # recover those file
            locked_file_node = []
            for upload_data in request_payload.data:
                # add lock
                bucket = ('gr-' if namespace == 'greenroom' else 'core-') + request_payload.project_code
                lock_key = os.path.join(bucket, upload_data.resumable_relative_path, upload_data.resumable_filename)

                try:
                    await async_lock_resource(lock_key, 'write')
                    locked_file_node.append((lock_key, 'write'))
                    # self.__logger.info("[INFO] lock added for: {}".format(lock_key))
                except Exception as e:
                    _res.code = EAPIResponseCode.conflict
                    _res.error_msg = str(e)
                    return _res

                # create folder and folder nodes
                folder_mgr = FolderMgr(
                    created_folders_cache,
                    project_info['global_entity_id'],
                    request_payload.project_code,
                    # raw_folder_path,
                    upload_data.resumable_relative_path,
                    request_payload.folder_tags,
                    namespace,
                )

                try:
                    await folder_mgr.create(request_payload.operator)
                    to_create_folders += folder_mgr.to_create
                    folder_relations += folder_mgr.relations_data
                except FileExistsError as file_exist_error:
                    # print("here")
                    _res.code = EAPIResponseCode.conflict
                    _res.error_msg = str(file_exist_error)
                    # recover the lock if there is error
                    for resource_key, operation in locked_file_node:
                        await async_unlock_resource(resource_key, operation)
                    return _res.json_response()
                except Exception as other_error:
                    self.__logger.error(str(other_error))
                    # recover the lock if there is error
                    for resource_key, operation in locked_file_node:
                        await async_unlock_resource(resource_key, operation)
                    return _res.json_response()

                last_folder_node_geid = folder_mgr.last_node.global_entity_id if folder_mgr.last_node else None
                self.__logger.info('[INFO] Folders created: {}'.format(lock_key))

                # get job geid
                resumable_identifier = await async_get_geid()
                self.__logger.info('[INFO] Fetched geid for: {}'.format(lock_key))
                temp_dir = await get_temp_dir(resumable_identifier)
                relative_full_path = await run_in_threadpool(
                    os.path.join, upload_data.resumable_relative_path, upload_data.resumable_filename
                )
                self.__logger.info('[INFO] path calculated for: {}'.format(lock_key))

                # init empty status manager
                status_mgr = await get_fsm_object(
                    session_id,
                    request_payload.project_code,
                    _JOB_TYPE,
                    request_payload.operator,
                )
                # first time need to call set_job_id
                await status_mgr.set_job_id(resumable_identifier)
                status_mgr.set_source(relative_full_path)
                status_mgr.add_payload('task_id', task_id)
                status_mgr.add_payload('resumable_identifier', resumable_identifier)
                status_mgr.add_payload('parent_folder_geid', last_folder_node_geid)
                self.__logger.info('[INFO] Job created: {}'.format(lock_key))

                try:
                    # create temp dir
                    is_dir_exist = await run_in_threadpool(os.path.isdir, temp_dir)
                    if not is_dir_exist:
                        await run_in_threadpool(os.makedirs, temp_dir)
                    # set preuploaded status
                    status_mgr.set_status(EState.PRE_UPLOADED.name)
                    job_key, job_value, job_recorded = status_mgr.get_kv_entity()
                    await run_in_threadpool(redis_pipeline.set, job_key, job_value)
                    job_list.append(job_recorded)
                    self.__logger.info('[INFO] Job status changed: {}'.format(lock_key))
                except Exception as exce:
                    # catch internal error
                    status_mgr.add_payload('error_msg', str(exce))
                    status_mgr.set_status(EState.TERMINATED.name)
                    self.__logger.error('[INFO] Job failed: {}'.format(lock_key))
                    raise exce

                self.__logger.info('[SUCCEED] All tasks done for: {}'.format(lock_key))

            # batch create folder nodes
            if len(to_create_folders) > 0:
                # also try to lock the those new folder
                locked_folder_node = []
                try:
                    for nodes in to_create_folders:
                        bucket_prefix = 'gr-' if nodes.get('zone') == 'greenroom' else 'core-'
                        bucket = bucket_prefix + nodes.get('project_code')
                        lock_key = '%s/%s' % (bucket, nodes.get('display_path'))
                        await async_lock_resource(lock_key, 'write')
                        locked_folder_node.append((lock_key, 'write'))

                    first_node = to_create_folders[0]
                    zone = first_node['zone']
                    res = await batch_create_4j_foldernodes(to_create_folders, zone)
                    self.__logger.info('[SUCCEED] Neo4j Folders create result: {}'.format(res.text))
                    relations_saved = await batch_link_folders(folder_relations)
                    self.__logger.info('[SUCCEED] Neo4j Folders relations result: {}'.format(relations_saved.text))
                    self.__logger.info('[SUCCEED] Neo4j Folders saved: {}'.format(len(to_create_folders)))

                except Exception as e:
                    # if we hit the lock then just return 409 already in use
                    _res.code = EAPIResponseCode.conflict
                    _res.result = str(e)
                    # here ONLY the folder has some issue then we unlock the
                    # file node in previous
                    for resource_key, operation in locked_file_node:
                        await async_unlock_resource(resource_key, operation)

                    return _res.json_response()
                finally:
                    # here we unlock the locked nodes ONLY
                    for resource_key, operation in locked_folder_node:
                        await async_unlock_resource(resource_key, operation)
            await redis_pipeline.execute()
            _res.code = EAPIResponseCode.success
            _res.result = job_list
            self.__logger.info('[SUCCEED] Done')

            return _res.json_response()
        else:
            _res.code = EAPIResponseCode.bad_request
            _res.error_msg = 'Invalid job type: {}'.format(request_payload.job_type)
            return _res.json_response()

    @router.get('/files/jobs', tags=[_API_TAG], response_model=GETJobStatusResponse, summary='get upload job status')
    @catch_internal(_API_NAMESPACE)
    async def get_status(self, project_code, operator, session_id: str = Header(None)):
        """This method allow to check file upload status."""
        _res = APIResponse()
        if not session_id:
            _res.code = EAPIResponseCode.bad_request
            _res.result = {}
            _res.error_msg = 'Invalid Session ID: ' + str(session_id)
            return _res.json_response()
        job_fatched = await session_job_get_status(session_id, '*', project_code, _JOB_TYPE, operator)
        _res.code = EAPIResponseCode.success
        _res.result = job_fatched
        return _res.json_response()

    @router.delete('/files/jobs', tags=[_API_TAG], summary='Delete the upload job status.')
    @catch_internal(_API_NAMESPACE)
    async def clear_status(self, session_id: str = Header(None)):
        """delete status by session id."""
        _res = APIResponse()
        if not session_id:
            _res.code = EAPIResponseCode.bad_request
            _res.result = {}
            _res.error_msg = 'Invalid Session ID: ' + str(session_id)
            return _res.json_response()
        await delete_by_session_id(session_id, action=_JOB_TYPE)
        _res.code = EAPIResponseCode.success
        _res.result = {'message': 'Success'}
        return _res.json_response()

    @router.post('/files/chunks', tags=[_API_TAG], response_model=ChunkUploadResponse, summary='upload chunks process.')
    @catch_internal(_API_NAMESPACE)
    async def upload_chunks(
        self,
        project_code: str = Form(...),
        operator: str = Form(...),
        resumable_identifier: str = Form(...),
        resumable_filename: str = Form(...),
        resumable_relative_path: str = Form(''),
        resumable_chunk_number: int = Form(...),
        resumable_total_chunks: int = Form(...),
        resumable_total_size: int = Form(...),
        tags: list = Form([]),
        dcm_id: str = Form('undefined'),
        session_id: str = Header(None),
        chunk_data: UploadFile = File(...),
    ):
        """This method allow to upload file chunks."""
        # init resp
        _res = APIResponse()
        if not session_id:
            _res.code = EAPIResponseCode.bad_request
            _res.result = {}
            _res.error_msg = 'Invalid Session ID: ' + str(session_id)
            return _res.json_response()

        self.__logger.info('resumable_filename: %s' % resumable_filename)
        # here I have to update the special character into NFC form
        # since some of the browser will encode them into NFD form
        # for the bug detail. Please check the ticket 2244
        resumable_filename = ud.normalize('NFC', resumable_filename)

        # check pipeline id
        resumable_filename = (
            dcm_id + '_' + resumable_filename if dcm_id and dcm_id != 'undefined' else resumable_filename
        )
        temp_dir = await get_temp_dir(resumable_identifier)

        # raw_folder_path = get_raw_folder_path(project_code)
        # file_full_path = os.path.join(
        #     raw_folder_path, resumable_relative_path, resumable_filename)
        # relative_full_path = os.path.join(
        #     resumable_relative_path, resumable_filename)

        # init status manager
        status_mgr = await get_fsm_object(
            session_id,
            project_code,
            _JOB_TYPE,
            operator,
            resumable_identifier,
        )
        try:
            chunk_name = generate_chunk_name(resumable_filename, resumable_chunk_number)
            destination = await run_in_threadpool(os.path.join, temp_dir, chunk_name)
            self.__logger.info('Start to save chunk {} to destination {}'.format(chunk_name, destination))
            await run_in_threadpool(save_file, destination, chunk_data)
        except Exception as exce:
            # catch internal error
            status_mgr.add_payload('error_msg', str(exce))
            await status_mgr.go(EState.TERMINATED)
            raise exce
        _res.code = EAPIResponseCode.success
        _res.result = {'msg': 'Succeed'}
        return _res.json_response()

    @router.post(
        '/files',
        tags=[_API_TAG],
        response_model=POSTCombineChunksResponse,
        summary='create a background worker to combine chunks, transfer file to the destination namespace',
    )
    @catch_internal(_API_NAMESPACE)
    async def on_success(
        self,
        request_payload: OnSuccessUploadPOST,
        background_tasks: BackgroundTasks,
        session_id: str = Header(None),
        Authorization: Optional[str] = Header(None),
        refresh_token: Optional[str] = Header(None),
    ):
        """This method allow to create a background worker to combine chunks uploaded."""
        # init resp
        _res = APIResponse()
        access_token = Authorization
        if not session_id:
            _res.code = EAPIResponseCode.bad_request
            _res.result = {}
            _res.error_msg = 'Invalid Session ID: ' + str(session_id)
            return _res.json_response()

        self.__logger.info('resumable_filename: %s' % request_payload.resumable_filename)
        # here I have to update the special character into NFC form
        # since some of the browser will encode them into NFD form
        # for the bug detail. Please check the ticket 2244
        request_payload.resumable_filename = ud.normalize('NFC', request_payload.resumable_filename)

        # check pipeline id
        request_payload.resumable_filename = (
            request_payload.dcm_id + '_' + request_payload.resumable_filename
            if request_payload.dcm_id and request_payload.dcm_id != 'undefined'
            else request_payload.resumable_filename
        )

        temp_dir = await get_temp_dir(request_payload.resumable_identifier)
        project_folder_path = await run_in_threadpool(os.path.join, ConfigClass.ROOT_PATH, request_payload.project_code)
        file_full_path = await run_in_threadpool(
            os.path.join,
            project_folder_path,
            request_payload.resumable_relative_path,
            request_payload.resumable_filename,
        )
        # relative_full_path = os.path.join(
        #     request_payload.resumable_relative_path,
        #     request_payload.resumable_filename)

        # init status manager
        status_mgr = await get_fsm_object(
            session_id,
            request_payload.project_code,
            _JOB_TYPE,
            request_payload.operator,
            request_payload.resumable_identifier,
        )
        self.__logger.info('File will be uploaded to %s' % project_folder_path)
        chunk_paths = [
            await run_in_threadpool(os.path.join, temp_dir, generate_chunk_name(request_payload.resumable_filename, x))
            for x in range(1, request_payload.resumable_total_chunks + 1)
        ]

        self.__logger.info('resumable_filename: %s' % request_payload.resumable_filename)
        # self.__logger.info(chunk_paths)

        # add background task to combine all received chunks
        background_tasks.add_task(
            finalize_worker,
            self.__logger,
            request_payload,
            status_mgr,
            chunk_paths,
            file_full_path,
            temp_dir,
            access_token,
            refresh_token,
        )

        self.__logger.info('finalize_worker started')
        # set merging status
        job_recorded = await status_mgr.go(EState.CHUNK_UPLOADED)
        _res.code = EAPIResponseCode.success
        _res.result = job_recorded
        self.__logger.info('wait for response')
        return _res.json_response()


def generate_chunk_name(uploaded_filename, chunk_number):
    """generate chunk file name."""
    return uploaded_filename + '_part_%03d' % chunk_number


async def async_get_temp_dir(resumable_identifier):
    return await run_in_threadpool(get_temp_dir, resumable_identifier)


async def get_temp_dir(resumable_identifier):
    """get temp directory."""
    return await run_in_threadpool(os.path.join, ConfigClass.TEMP_BASE, resumable_identifier)


def save_file(dest: str, my_file: UploadFile):
    """save file on the disk."""
    with open(dest, 'wb') as buffer:
        shutil.copyfileobj(my_file.file, buffer)


async def finalize_worker(
    logger,
    request_payload: OnSuccessUploadPOST,
    status_mgr: FsmMgrUpload,
    chunk_paths: list,
    target_file_full_path,
    temp_dir,
    access_token,
    refresh_token,
):
    """async zip worker."""
    lock_key = 'default'
    try:
        # Upload task to combine file chunks and upload to nfs
        namespace = os.environ.get('namespace')
        target_head, target_tail = os.path.split(target_file_full_path)
        temp_merged_file_full_path = os.path.join(temp_dir, request_payload.resumable_filename)
        with open(temp_merged_file_full_path, 'ab') as temp_file:
            for p in chunk_paths:
                # since some browser has different encoding so
                # we normalize the name with linux standard NFC
                stored_chunk_file_name = p
                logger.info('processing chunck %s' % stored_chunk_file_name)
                # TODO since we using python 3.7 unicode data does not
                # HAVE is_normalized form.
                # if ud.normalize('NFC', p) != p:
                #     stored_chunk_file_name = ud.normalize('NFC', p)

                stored_chunk_file = open(stored_chunk_file_name, 'rb')
                temp_file.write(stored_chunk_file.read())
                stored_chunk_file.close()
                os.unlink(stored_chunk_file_name)
        logger.info('done with combinging chunks')

        # # here now we dont deprecate the nfs completely
        # # so we need to do some overwrite if the file exist
        # target_path = os.path.join(target_head, request_payload.resumable_filename)
        # logger.info(temp_merged_file_full_path)
        # logger.info(target_path)
        # dest = shutil.move(temp_merged_file_full_path, target_path)
        # logger.info("Destination path is: %s" % dest)

        # for backup also sync to minio
        logger.info('Minio Connection Test')
        # format the bucket name and minio path
        bucket = ('gr-' if namespace == 'greenroom' else 'core-') + request_payload.project_code
        relative_path = target_file_full_path.replace(ConfigClass.ROOT_PATH, '')
        _, obj_path = tuple(relative_path[1:].split('/', 1))
        # file_path = target_head + "/" + target_tail

        # since now we have the user node, remove this join
        # obj_path = os.path.join(request_payload.operator, obj_path)

        version_id = ''
        # after use the minio the pipeline will also use the minio location
        minio_http = ('https://' if ConfigClass.MINIO_HTTPS else 'http://') + ConfigClass.MINIO_ENDPOINT
        minio_location = 'minio://%s/%s/%s' % (minio_http, bucket, obj_path)
        # get lock key
        lock_key = os.path.join(bucket, obj_path)
        # minio_location = minio_location.encode('utf-8')
        try:
            mc = Minio_Client_(access_token, refresh_token)
            logger.info('Minio Connection Success')

            result = mc.client.fput_object(
                bucket,
                obj_path,
                temp_merged_file_full_path,
            )
            version_id = result.version_id
            logger.info('Minio Upload Success')
        except Exception as e:
            logger.error('error when uploading: ' + str(e))
            # async_unlock_resource(lock_key)

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
            request_payload.dcm_id,
            bucket,  # minio attribute
            obj_path,  # minio attribute
            version_id,  # minio attribute
            operator=request_payload.operator,
            process_pipeline=request_payload.process_pipeline,
            from_parents=request_payload.from_parents,
            parent_folder_geid=status_mgr.payload['parent_folder_geid'],
        )
        if res_create_meta.get('error'):
            logger.error('res_create_meta error: ' + str(res_create_meta))
            raise Exception('res_create_meta error: ' + str(res_create_meta))
        else:
            logger.info('done with creating atlas record v2')
        # get created entity
        created_entity = res_create_meta['result']

        # Store zip file preview in postgres
        try:
            file_type = os.path.splitext(temp_merged_file_full_path)[1]
            if file_type == '.zip':
                archive_preview = generate_archive_preview(temp_merged_file_full_path)
                payload = {
                    'archive_preview': archive_preview,
                    'file_geid': created_entity['global_entity_id'],
                }
                httpx.post(ConfigClass.DATA_OPS_UTIL + 'archive', json=payload)
        except Exception as e:
            geid = created_entity['global_entity_id']
            logger.error(f'Error adding file preview for {geid}: {str(e)}')
            # async_unlock_resource(lock_key)

        # update full path to Greenroom/<display_path>
        obj_path = (
            (ConfigClass.GREEN_ZONE_LABEL if namespace == 'greenroom' else ConfigClass.CORE_ZONE_LABEL) + '/' + obj_path
        )
        # add upload logs
        update_file_operation_logs(
            request_payload.operator,
            obj_path,
            request_payload.project_code,
            extra={'upload_message': request_payload.upload_message},
        )

        # # update tag frequence in redis
        # project_id = (await get_project(request_payload.project_code))['id']
        # for tag in request_payload.tags:
        #     SrvTagsMgr().add_freq(project_id, tag)

        # send to queue
        payload = {
            'event_type': 'data_uploaded',
            'payload': {
                'input_path': minio_location,  # update to minio
                'project': request_payload.project_code,
                'dcm_id': request_payload.dcm_id,
                'uploader': request_payload.operator,
                'source_geid': created_entity['global_entity_id'],
                # new here the token for following pipeline
                'auth_token': {'at': access_token, 'rt': refresh_token},
            },
            'create_timestamp': time.time(),
        }
        send_to_queue(payload, logger)
        logger.info('sent to queue.')
        # clean up tmp folder
        await status_mgr.go(EState.FINALIZED)
        try:
            shutil.rmtree(temp_dir)
        except Exception as exce:
            logger.info('Upload on succeed rmtree error: ' + str(exce))
            # async_unlock_resource(lock_key)
        try:
            status_mgr.add_payload('source_geid', created_entity['global_entity_id'])
            await status_mgr.go(EState.SUCCEED)
        except Exception as exce:
            logger.info('Upload on succeed set status as succeed error: ' + str(exce))
            # async_unlock_resource(lock_key)
        logger.info('Upload Job Done.')
        # async_unlock_resource(lock_key)

    except FileNotFoundError as e:
        error_msg = 'folder {} is already empty'.format(temp_dir)
        logger.warning(error_msg)
        logger.warning(str(e))
        # async_unlock_resource(lock_key)

    except Exception as exce:
        # catch internal error
        logger.error(str(exce))
        status_mgr.add_payload('error_msg', str(exce))
        await status_mgr.go(EState.TERMINATED)
        # async_unlock_resource(lock_key)
        raise exce

    finally:
        unlock_resource(lock_key, 'write')


def get_root_folder(folder_path):
    """recursively get rootfolder."""
    if not os.path.dirname(folder_path):
        return folder_path
    else:
        parent_folder = os.path.dirname(folder_path)
        return get_root_folder(parent_folder)


async def get_conflict_folder_paths(data, project_code, current_folder_node, incremental):
    """return conflict folder paths."""
    namespace = os.environ.get('namespace')

    # to speed up the loop -> change the array to set
    # to remove the duplicate folder name check
    folder_set = set()
    for upload_data in data:
        # check folder name
        dp = current_folder_node if current_folder_node else get_root_folder(upload_data.resumable_relative_path)
        folder_set.add(dp)

    conflict_folder_paths = []
    for display_path in folder_set:
        payload = {'display_path': display_path, 'project_code': project_code, 'archived': False}
        # also check if it is in greeroom or core
        neo4j_zone_label = ConfigClass.GREEN_ZONE_LABEL if namespace == 'greenroom' else ConfigClass.CORE_ZONE_LABEL
        node_query_url = ConfigClass.NEO4J_SERVICE + 'nodes/%s/query' % neo4j_zone_label
        with httpx.Client() as client:
            response = client.post(node_query_url, json=payload)
        if len(response.json()) > 0:
            conflict_folder_paths.append(
                {'display_path': display_path, 'relative_path': upload_data.resumable_relative_path, 'type': 'Folder'}
            )

            break
    return conflict_folder_paths


async def get_conflict_file_paths(data, project_code):
    """return conflict file path."""
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
        display_path = upload_data.resumable_relative_path + '/' + upload_data.resumable_filename
        payload = {'display_path': display_path, 'project_code': project_code, 'archived': False}
        # also check if it is in greeroom or core
        neo4j_zone_label = ConfigClass.GREEN_ZONE_LABEL if namespace == 'greenroom' else ConfigClass.CORE_ZONE_LABEL
        node_query_url = ConfigClass.NEO4J_SERVICE + 'nodes/%s/query' % neo4j_zone_label
        async with httpx.AsyncClient() as client:
            response = await client.post(node_query_url, json=payload)

        if len(response.json()) > 0:
            conflict_file_paths.append(
                {
                    'name': upload_data.resumable_filename,
                    'relative_path': upload_data.resumable_relative_path,
                    'type': 'File',
                }
            )

    return conflict_file_paths


def response_conflic_folder_file_names(_res, conflict_file_paths, conflict_folder_paths):
    """set conflict response when filename or folder name conflics."""
    # conflict file names
    if len(conflict_file_paths) > 0:
        _res.code = EAPIResponseCode.conflict
        _res.error_msg = customized_error_template(ECustomizedError.INVALID_FILENAME)
        _res.result = {'failed': conflict_file_paths}
        return _res.json_response()
    # conflict folder names
    if len(conflict_folder_paths) > 0:
        _res.code = EAPIResponseCode.conflict
        _res.error_msg = customized_error_template(ECustomizedError.INVALID_FOLDERNAME)
        _res.result = {'failed': conflict_folder_paths}
        return _res.json_response()
