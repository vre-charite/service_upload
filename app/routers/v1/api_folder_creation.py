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

"""Folder creation API."""
import os
import re

import httpx
from fastapi import APIRouter
from fastapi import HTTPException
from fastapi_utils import cbv

from app.commons.logger_services.logger_factory_service import SrvLoggerFactory
from app.config import ConfigClass
from app.models.base_models import APIResponse
from app.models.models_upload import BulkCreateFolderPOST
from app.models.models_upload import BulkCreateFolderPOSTV2
from app.models.models_upload import CreateFolderPOST
from app.models.models_upload import CreateFolderPOSTResponse
from app.resources.error_handler import EAPIResponseCode
from app.resources.error_handler import ECustomizedError
from app.resources.error_handler import catch_internal
from app.resources.error_handler import customized_error_template
from app.resources.helpers import bulk_get_geid
from app.resources.helpers import get_geid
from app.resources.lock import lock_resource
from app.resources.lock import unlock_resource

router = APIRouter()

_API_TAG = 'V1 Folder creation'
_API_NAMESPACE = 'api_folder_creation'

_logger = SrvLoggerFactory('api_folder_creation').get_logger()

# TODO this might be move out from the upload service <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<


@cbv.cbv(router)
class APIBulkFolderCreationV2:
    """API to create folder."""

    def __init__(self):
        self.__logger = SrvLoggerFactory('api_bulk_folder_creation').get_logger()

    @router.post(
        '/folder/bulk',
        tags=[_API_TAG],
        summary='This API is to bulk create a folder in the target destination',
        response_model=CreateFolderPOSTResponse,
    )
    @catch_internal(_API_NAMESPACE)
    async def bulk_create_folder_v2(self, request_payload: BulkCreateFolderPOSTV2):
        zone = request_payload.zone
        folders = request_payload.folders

        self.__logger.info(f'Bulk create folder v2 payload: {request_payload}')

        folder_level = 0
        folder_parent_geid = ''
        folder_parent_name = ''
        folder_relative_path = ''

        payload = []
        try:
            geid_list = bulk_get_geid(len(folders))
            index = 0
            for folder in folders:
                folder_name = folder['name'].strip()
                valid = validate_folder_name(folder_name)

                if len(folder_name) < 1 or len(folder_name) > 20 or valid is not None:
                    continue

                display_path = folder_relative_path + '/' + folder_name if folder_relative_path else folder_name

                global_entity_id = geid_list[index]
                payload.append(
                    {
                        'global_entity_id': global_entity_id,
                        'folder_name': folder_name,
                        'folder_level': folder_level,
                        'folder_parent_geid': folder_parent_geid,
                        'folder_parent_name': folder_parent_name,
                        'uploader': folder['uploader'],
                        'folder_relative_path': folder_relative_path,
                        'zone': zone,
                        'project_code': folder['project_code'],
                        'folder_tags': folder['tags'],
                        'extra_attrs': {
                            'display_path': display_path,
                        },
                    }
                )
                index += 1

            self.__logger.info(f'bulk create folder payload of service entityinfo: {payload}')
            create_response = bulk_create_folder_nodes(payload, zone)
            self.__logger.info(f'bulk create folder response of service entityinfo: {create_response}')
            return create_response

        except Exception as error:
            self.__logger.error(f'Error while bulk creating folder {error}')
            raise HTTPException(status_code=500, detail=f'Error while bulk creating folder {error}')


@cbv.cbv(router)
class APIBulkFolderCreation:
    """API to create folder."""

    def __init__(self):
        self.__logger = SrvLoggerFactory('api_bulk_folder_creation').get_logger()

    @router.post(
        '/folder/batch',
        tags=[_API_TAG],
        summary='This API is to bulk create a folder in the target destination',
        response_model=CreateFolderPOSTResponse,
    )
    @catch_internal(_API_NAMESPACE)
    async def bulk_create_folder(self, request_payload: BulkCreateFolderPOST):
        _res = APIResponse()
        folder_name = request_payload.folder_name.strip()
        valid = validate_folder_name(folder_name)

        if len(folder_name) < 1 or len(folder_name) > 20 or valid is not None:
            _res.code = EAPIResponseCode.bad_request
            _res.error_msg = customized_error_template(ECustomizedError.INVALID_FOLDER_NAME_TYPE)
            _res.result = {'failed': "Folder should not contain : (\\/:?*<>|”') and must contain 1 to 20 characters"}
            return _res.json_response()
        project_code_list = request_payload.project_code_list
        zone = ConfigClass.GREEN_ZONE_LABEL if request_payload.zone == 'greenroom' else ConfigClass.CORE_ZONE_LABEL

        folder_level = 0
        folder_parent_geid = ''
        folder_parent_name = ''
        folder_relative_path = ''

        payload = []

        display_path = folder_relative_path + '/' + folder_name if folder_relative_path else folder_name

        try:
            geid_list = bulk_get_geid(len(project_code_list))
            index = 0
            for project_code in project_code_list:
                global_entity_id = geid_list[index]
                payload.append(
                    {
                        'global_entity_id': global_entity_id,
                        'folder_name': folder_name,
                        'folder_level': folder_level,
                        'folder_parent_geid': folder_parent_geid,
                        'folder_parent_name': folder_parent_name,
                        'uploader': request_payload.uploader,
                        'folder_relative_path': folder_relative_path,
                        'zone': zone,
                        'project_code': project_code,
                        'folder_tags': request_payload.tags,
                        'extra_attrs': {
                            'display_path': display_path,
                        },
                    }
                )
                index += 1

            create_response = bulk_create_folder_nodes(payload, zone)
            return create_response

        except Exception as error:
            _logger.error(f'Error while bulk creating folder {error}')
            raise HTTPException(status_code=500, detail=f'Error while bulk creating folder {error}')


@cbv.cbv(router)
class APIFolderCreation:
    """API to create folder."""

    def __init__(self):
        self.__logger = SrvLoggerFactory('api_folder_creation').get_logger()

    @router.post(
        '/folder',
        tags=[_API_TAG],
        summary='This API is to create a folder in the target destination',
        response_model=CreateFolderPOSTResponse,
    )
    @catch_internal(_API_NAMESPACE)
    async def create_folder(self, request_payload: CreateFolderPOST):
        """create folder / sub folder."""
        _res = APIResponse()
        folder_name = request_payload.folder_name.strip()

        # check if folder name is valid
        valid = validate_folder_name(folder_name)
        if len(folder_name) < 1 or len(folder_name) > 20 or valid is not None:
            _res.code = EAPIResponseCode.bad_request
            _res.error_msg = customized_error_template(ECustomizedError.INVALID_FOLDER_NAME_TYPE)
            _res.result = {'failed': "Folder should not contain : (\\/:?*<>|”') and must contain 1 to 20 characters"}
            return _res.json_response()
        project_code = request_payload.project_code
        zone = request_payload.zone
        # raw_folder_path = "get_raw_folder_path(project_code, zone)"

        destination_geid = request_payload.destination_geid
        global_entity_id = get_geid()
        folder_level = 0
        # folder_full_path = os.path.join(raw_folder_path, folder_name)
        folder_parent_geid = ''
        folder_parent_name = ''
        folder_relative_path = ''
        neo4j_zone_label = ''
        display_path = None

        try:
            # create folder node
            if destination_geid is not None:
                destination_geid = request_payload.destination_geid
                respon_query = get_from_db(destination_geid)
                if respon_query.status_code != 200:
                    _logger.error(f'Error while fetching details from db : {respon_query.text}')
                    raise HTTPException(status_code=500, detail='Error while creating folder')
                if respon_query.status_code == 200 and len(respon_query.json()) != 0:
                    respon_query = respon_query.json()
                    folder_parent_geid = respon_query[0]['global_entity_id']
                    folder_parent_name = respon_query[0]['name']
                    folder_relative_path = os.path.join(respon_query[0]['folder_relative_path'], folder_parent_name)
                    folder_level = respon_query[0].get('folder_level') + 1
            else:
                return

            # check if the project exist
            project_query_url = ConfigClass.NEO4J_SERVICE + 'nodes/Container/query'
            payload = {'code': project_code}
            with httpx.Client() as client:
                response = client.post(project_query_url, json=payload)
            if len(response.json()) == 0:
                _logger.error(f'project {project_code} does not exist')
                return project_does_not_exist(_res, project_code)

            # now we have to use the neo4j to check duplicate
            display_path = folder_relative_path + '/' + folder_name if folder_relative_path else folder_name
            payload = {
                'display_path': display_path,
                'project_code': project_code,
                'archived': False,
            }
            # also check if it is in greeroom or core
            neo4j_zone_label = ConfigClass.GREEN_ZONE_LABEL if zone == 'greenroom' else ConfigClass.CORE_ZONE_LABEL
            node_query_url = ConfigClass.NEO4J_SERVICE + 'nodes/%s/query' % neo4j_zone_label
            with httpx.Client() as client:
                response = client.post(node_query_url, json=payload)
            # print(response.json())
            if len(response.json()) > 0:
                _logger.error(f'Folder with name {folder_name} already exists in the destination {display_path}')
                return folder_name_conflict(_res, folder_name, display_path)

            # formulate the folder metadata
            query = {
                'global_entity_id': global_entity_id,
                'folder_name': folder_name,
                'folder_level': folder_level,
                'folder_parent_geid': folder_parent_geid,
                'folder_parent_name': folder_parent_name,
                'uploader': request_payload.uploader,
                'folder_relative_path': folder_relative_path,
                'zone': neo4j_zone_label,
                'project_code': project_code,
                'folder_tags': request_payload.tags,
                'extra_attrs': {
                    'display_path': display_path,
                },
            }

            # TODO decorator here?
            # before the creation check if folder is on locked
            # this purpose is to avoid racing in the two client
            bucket_prefix = 'gr-' if neo4j_zone_label == ConfigClass.GREEN_ZONE_LABEL else 'core-'
            folder_key = '%s/%s' % (bucket_prefix + project_code, display_path)
            lock_resource(folder_key, 'write')

            query_response = None
            try:
                query_response = create_folder_node(query_params=query)
                # print(query_response)
            except Exception as e:
                raise e
            finally:
                # at the end unlock the folder
                unlock_resource(folder_key, 'write')

            return query_response

        except Exception as error:
            _logger.error(f'Error while creating folder {error}')
            raise HTTPException(status_code=500, detail=f'Error while creating folder {error}')


# TODO somehow merge the following two function
def create_folder_node(query_params) -> object:
    """create folder node using entity_info_service."""

    # if folder is idle then we go on to create the folder
    payload = {**query_params}
    create_url = ConfigClass.ENTITYINFO_SERVICE + 'folders'
    _logger.info('create folder request payload: {}'.format(payload))
    with httpx.Client() as client:
        respon = client.post(create_url, json=payload)
    if respon.status_code == 200:
        return respon.json()
    else:
        _logger.error(f'Error while creating folder node : {respon.text}')
        raise HTTPException(status_code=500, detail='Error while creating folder')


def bulk_create_folder_nodes(payload, zone):
    data = {
        'payload': payload,
        # TODO update here later
        'zone': ConfigClass.GREEN_ZONE_LABEL if zone == 'greenroom' else ConfigClass.CORE_ZONE_LABEL,
    }
    create_url = ConfigClass.ENTITYINFO_SERVICE + 'folders/batch'
    _logger.info('create folder request payload: {}'.format(payload))
    with httpx.Client() as client:
        respon = client.post(create_url, json=data)
    if respon.status_code == 200:
        return respon.json()
    else:
        _logger.error(f'Error while bulk creating folder node : {respon.text}')
        raise HTTPException(status_code=500, detail='Error while creating folder')


# if FE passes relative_path
def get_from_db(geid):
    """Get parent folder details from db using global_entity_id."""
    payload = {'global_entity_id': geid}
    node_query_url = ConfigClass.NEO4J_SERVICE + 'nodes/Folder/query'
    with httpx.Client() as client:
        response = client.post(node_query_url, json=payload)
    if response.status_code == 200:
        return response


def folder_name_conflict(_res, folder_name, folder_full_path):
    """return conflict file path."""

    _res.code = EAPIResponseCode.conflict
    _res.error_msg = customized_error_template(ECustomizedError.INVALID_FILENAME)
    _res.result = {'failed': f'Folder with name {folder_name} already exists at the destiantion {folder_full_path}'}
    return _res.json_response()


def project_does_not_exist(_res, code):
    """return conflict file path."""

    _res.code = EAPIResponseCode.bad_request
    _res.error_msg = f'project {code} does not exist'
    _res.result = {'failed': f'project {code} does not exist'}
    return _res.json_response()


def validate_folder_name(folder_name):
    regex = re.compile('[/:?.\\*<>|”\']')
    valid = regex.search(folder_name)
    return valid
