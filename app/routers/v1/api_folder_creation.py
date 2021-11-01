""" Folder creation API"""
import os
import re
import requests
from fastapi import APIRouter, HTTPException
from fastapi_utils import cbv
from ...commons.logger_services.logger_factory_service import SrvLoggerFactory
from ...config import ConfigClass
from ...models.base_models import APIResponse
from ...models.models_upload import CreateFolderPOST, CreateFolderPOSTResponse, BulkCreateFolderPOST, BulkCreateFolderPOSTV2
from ...resources.error_handler import catch_internal, EAPIResponseCode, \
    ECustomizedError, customized_error_template
from ...resources.helpers import get_geid, bulk_get_geid
import time

router = APIRouter()

_API_TAG = 'V1 Folder creation'
_API_NAMESPACE = "api_folder_creation"

_logger = SrvLoggerFactory('api_folder_creation').get_logger()


@cbv.cbv(router)
class APIBulkFolderCreationV2:
    """ API to create folder"""

    def __init__(self):
        self.__logger = SrvLoggerFactory(
            'api_bulk_folder_creation').get_logger()

    @router.post("/folder/bulk", tags=[_API_TAG],
                 summary="This API is to bulk create a folder in the target destination",
                 response_model=CreateFolderPOSTResponse)
    @catch_internal(_API_NAMESPACE)
    async def bulk_create_folder_v2(self, request_payload: BulkCreateFolderPOSTV2):
        _res = APIResponse()

        zone = request_payload.zone
        folders = request_payload.folders

        self.__logger.info(
            f"Bulk create folder v2 payload: {request_payload}")

        folder_level = 0
        folder_parent_geid = ""
        folder_parent_name = ""
        folder_relative_path = ""

        payload = []

        try:
            geid_list = bulk_get_geid(len(folders))
            index = 0
            for folder in folders:
                folder_name = folder['name'].strip()
                valid = validate_folder_name(folder_name)

                if len(folder_name) < 1 or len(folder_name) > 20 or valid is not None:
                    continue

                display_path = folder_relative_path+'/' + \
                    folder_name if folder_relative_path else folder_name

                global_entity_id = geid_list[index]
                payload.append({
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
                })
                index += 1

            self.__logger.info(
                f"bulk create folder payload of service entityinfo: {payload}")
            create_response = bulk_create_folder_nodes(payload, zone)
            self.__logger.info(
                f"bulk create folder response of service entityinfo: {create_response}")
            return create_response

        except Exception as error:
            self.__logger.error(f"Error while bulk creating folder {error}")
            raise HTTPException(
                status_code=500, detail=f"Error while bulk creating folder {error}")


@cbv.cbv(router)
class APIBulkFolderCreation:
    """ API to create folder"""

    def __init__(self):
        self.__logger = SrvLoggerFactory(
            'api_bulk_folder_creation').get_logger()

    @router.post("/folder/batch", tags=[_API_TAG],
                 summary="This API is to bulk create a folder in the target destination",
                 response_model=CreateFolderPOSTResponse)
    @catch_internal(_API_NAMESPACE)
    async def bulk_create_folder(self, request_payload: BulkCreateFolderPOST):
        _res = APIResponse()

        folder_name = request_payload.folder_name.strip()
        valid = validate_folder_name(folder_name)

        if len(folder_name) < 1 or len(folder_name) > 20 or valid is not None:
            _res.code = EAPIResponseCode.bad_request
            _res.error_msg = customized_error_template(
                ECustomizedError.INVALID_FOLDER_NAME_TYPE)
            _res.result = {
                "failed": "Folder should not contain : (\/:?*<>|”') and must contain 1 to 20 characters"
            }
            return _res.json_response()
        project_code_list = request_payload.project_code_list
        zone = request_payload.zone

        folder_level = 0
        folder_parent_geid = ""
        folder_parent_name = ""
        folder_relative_path = ""

        payload = []

        display_path = folder_relative_path+'/' + \
            folder_name if folder_relative_path else folder_name

        try:
            geid_list = bulk_get_geid(len(project_code_list))
            index = 0
            for project_code in project_code_list:
                global_entity_id = geid_list[index]
                payload.append({
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
                })
                index += 1

            create_response = bulk_create_folder_nodes(payload, zone)
            return create_response

        except Exception as error:
            _logger.error(f"Error while bulk creating folder {error}")
            raise HTTPException(
                status_code=500, detail=f"Error while bulk creating folder {error}")


@cbv.cbv(router)
class APIFolderCreation:
    """ API to create folder"""

    def __init__(self):
        self.__logger = SrvLoggerFactory('api_folder_creation').get_logger()

    @router.post("/folder", tags=[_API_TAG],
                 summary="This API is to create a folder in the target destination",
                 response_model=CreateFolderPOSTResponse)
    @catch_internal(_API_NAMESPACE)
    async def create_folder(self, request_payload: CreateFolderPOST):
        """
        create folder / sub folder
        """
        _res = APIResponse()

        folder_name = request_payload.folder_name.strip()

        # check if folder name is valid

        valid = validate_folder_name(folder_name)
        if len(folder_name) < 1 or len(folder_name) > 20 or valid is not None:
            _res.code = EAPIResponseCode.bad_request
            _res.error_msg = customized_error_template(
                ECustomizedError.INVALID_FOLDER_NAME_TYPE)
            _res.result = {
                "failed": "Folder should not contain : (\/:?*<>|”') and must contain 1 to 20 characters"
            }
            return _res.json_response()
        project_code = request_payload.project_code
        zone = request_payload.zone
        raw_folder_path = "get_raw_folder_path(project_code, zone)"

        destination_geid = request_payload.destination_geid
        global_entity_id = get_geid()
        folder_level = 0
        folder_full_path = os.path.join(raw_folder_path, folder_name)
        folder_parent_geid = ""
        folder_parent_name = ""
        folder_relative_path = ""

        try:
            # create folder node
            if destination_geid is not None:
                destination_geid = request_payload.destination_geid
                respon_query = get_from_db(destination_geid)
                if respon_query.status_code != 200:
                    _logger.error(
                        f"Error while fetching details from db : {respon_query.text}")
                    raise HTTPException(
                        status_code=500, detail=f"Error while creating folder")
                if respon_query.status_code == 200 and len(respon_query.json()) != 0:
                    respon_query = respon_query.json()
                    folder_parent_geid = respon_query[0]['global_entity_id']
                    folder_parent_name = respon_query[0]['name']
                    folder_relative_path = os.path.join(
                        respon_query[0]['folder_relative_path'], folder_parent_name)
                    folder_full_path = os.path.join(
                        raw_folder_path, folder_relative_path, folder_name)
                    folder_level = len(folder_relative_path.split("/"))

            # check if the project exist
            project_query_url = ConfigClass.NEO4J_SERVICE+"nodes/Container/query"
            payload = {
                'code': project_code
            }
            response = requests.post(project_query_url, json=payload)
            if len(response.json()) == 0:
                _logger.error(f"project {project_code} does not exist")
                return project_does_not_exist(_res, project_code)

            # now we have to use the neo4j to check duplicate
            display_path = folder_relative_path+'/' + \
                folder_name if folder_relative_path else folder_name
            payload = {
                'display_path': display_path,
                'project_code': project_code,
                'archived': False,
            }
            # also check if it is in greeroom or core
            neo4j_zone_label = "VRECore" if zone == "vrecore" else "Greenroom"
            node_query_url = ConfigClass.NEO4J_SERVICE + "nodes/%s/query" % neo4j_zone_label
            response = requests.post(node_query_url, json=payload)
            # print(response.json())
            if len(response.json()) > 0:
                _logger.error(
                    f"Folder with name {folder_name} already exists in the destination {display_path}")
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
                'zone': zone,
                'project_code': project_code,
                'folder_tags': request_payload.tags,
                'extra_attrs': {
                    'display_path': display_path,
                },
            }

            ########################################################
            # Since we move to minio so deprecate the nfs folder
            # there is no folder concept in minio so we just use
            # the neo4j for display purpose
            ########################################################
            # try:
            #     os.makedirs(folder_full_path)
            #     query_response = create_folder_node(query_params=query)

            #     return query_response

            # except FileExistsError as error:
            #     _logger.error(f"Folder with name {folder_name} already exists in the destination {folder_full_path}")
            #     return folder_name_conflict(_res, folder_name, folder_full_path)

            query_response = create_folder_node(query_params=query)
            return query_response

        except Exception as error:
            _logger.error(f"Error while creating folder {error}")
            raise HTTPException(
                status_code=500, detail=f"Error while creating folder {error}")


def create_folder_node(query_params) -> object:
    """ create folder node using entity_info_service"""
    payload = {
        **query_params
    }
    create_url = ConfigClass.ENTITYINFO_SERVICE + "folders"
    _logger.info("create folder request payload: {}".format(payload))
    respon = requests.post(create_url, json=payload)
    if respon.status_code == 200:
        return respon.json()
    else:
        _logger.error(f"Error while creating folder node : {respon.text}")
        raise HTTPException(
            status_code=500, detail=f"Error while creating folder")


def bulk_create_folder_nodes(payload, zone):
    data = {
        "payload": payload,
        "zone": zone
    }
    create_url = ConfigClass.ENTITYINFO_SERVICE + "folders/batch"
    _logger.info("create folder request payload: {}".format(payload))
    respon = requests.post(create_url, json=data)
    if respon.status_code == 200:
        return respon.json()
    else:
        _logger.error(f"Error while bulk creating folder node : {respon.text}")
        raise HTTPException(
            status_code=500, detail=f"Error while creating folder")


# if FE passes relative_path
def get_from_db(geid):
    """ Get parent folder details from db using global_entity_id"""
    payload = {
        "global_entity_id": geid
    }
    node_query_url = ConfigClass.NEO4J_SERVICE + "nodes/Folder/query"
    response = requests.post(node_query_url, json=payload)
    if response.status_code == 200:
        return response


def folder_name_conflict(_res, folder_name, folder_full_path):
    '''
    return conflict file path
    '''

    _res.code = EAPIResponseCode.conflict
    _res.error_msg = customized_error_template(
        ECustomizedError.INVALID_FILENAME)
    _res.result = {
        "failed": f"Folder with name {folder_name} already exists at the destiantion {folder_full_path}"
    }
    return _res.json_response()


def project_does_not_exist(_res, code):
    '''
    return conflict file path
    '''

    _res.code = EAPIResponseCode.bad_request
    _res.error_msg = f"project {code} does not exist"
    _res.result = {
        "failed": f"project {code} does not exist"
    }
    return _res.json_response()


def get_raw_folder_path(project_code, zone):
    # (optional) check if the folder is not existed
    raw_folder_path = os.path.join(
        ConfigClass.ROOT_PATH, project_code)
    if zone == "vrecore":
        raw_folder_path = os.path.join(raw_folder_path)
    elif zone == "greenroom":
        # we decide to remove the raw folder for now it will upload
        # to the /project_code/
        # raw_folder_path = os.path.join(raw_folder_path, "raw")
        raw_folder_path = os.path.join(raw_folder_path)
        # os.makedirs(raw_folder_path)

    # check raw folder path valid
    if not os.path.isdir(raw_folder_path):
        raise (Exception('Folder raw does not existed: %s' %
                         raw_folder_path))
    return raw_folder_path


def validate_folder_name(folder_name):
    _res = APIResponse()
    regex = re.compile('[/:?.\\*<>|”\']')
    valid = regex.search(folder_name)
    return valid
