""" Folder creation API"""
import os
import re
import requests
from fastapi import APIRouter, HTTPException
from fastapi_utils import cbv
from ...commons.logger_services.logger_factory_service import SrvLoggerFactory
from ...config import ConfigClass
from ...models.base_models import APIResponse
from ...models.models_upload import CreateFolderPOST, CreateFolderPOSTResponse
from ...resources.error_handler import catch_internal, EAPIResponseCode, \
    ECustomizedError, customized_error_template
from ...resources.helpers import get_geid

router = APIRouter()

_API_TAG = 'V1 Folder creation'
_API_NAMESPACE = "api_folder_creation"

_logger = SrvLoggerFactory('api_folder_creation').get_logger()


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
        raw_folder_path = get_raw_folder_path(project_code, zone)

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
                    _logger.error(f"Error while fetching details from db : {respon_query.text}")
                    raise HTTPException(status_code=500, detail=f"Error while creating folder")
                if respon_query.status_code == 200 and len(respon_query.json()) != 0:
                    respon_query = respon_query.json()
                    folder_parent_geid = respon_query[0]['global_entity_id']
                    folder_parent_name = respon_query[0]['name']
                    folder_relative_path = os.path.join(respon_query[0]['folder_relative_path'], folder_parent_name)
                    folder_full_path = os.path.join(raw_folder_path, folder_relative_path, folder_name)
                    folder_level = len(folder_relative_path.split("/"))
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
            }

            try:
                os.makedirs(folder_full_path)
                query_response = create_folder_node(query_params=query)

                return query_response

            except FileExistsError as error:
                _logger.error(f"Folder with name {folder_name} already exists in the destination {folder_full_path}")
                return folder_name_conflict(_res, folder_name, folder_full_path)
        except Exception as error:
            _logger.error(f"Error while creating folder {error}")
            raise HTTPException(status_code=500, detail=f"Error while creating folder {error}")


def create_folder_node(query_params) -> object:
    """ create folder node using entity_info_service"""
    payload = {
        **query_params
    }
    create_url = ConfigClass.ENTITYINFO_SERVICE + "folders"
    respon = requests.post(create_url, json=payload)
    if respon.status_code == 200:
        return respon.json()
    else:
        _logger.error(f"Error while creating folder node : {respon.text}")
        raise HTTPException(status_code=500, detail=f"Error while creating folder")


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


def get_raw_folder_path(project_code, zone):
    # (optional) check if the folder is not existed
    raw_folder_path = os.path.join(
        ConfigClass.ROOT_PATH, project_code)
    if zone == "vrecore":
        raw_folder_path = os.path.join(raw_folder_path)
    elif zone == "greenroom":
        raw_folder_path = os.path.join(raw_folder_path, "raw")
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
