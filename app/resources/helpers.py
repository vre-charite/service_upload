import os
import zipfile
import time
import json
import requests
from .error_handler import internal_jsonrespon_handler
from ..config import ConfigClass
from ..commons.data_providers.redis import SrvRedisSingleton


def get_geid(entity_type: str):
    '''
    get geid
    http://10.3.7.222:5062/v1/utility/id?entity_type=data_upload
    '''
    url = ConfigClass.UTILITY_SERVICE + \
        "/v1/utility/id?entity_type={}".format(entity_type)
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()['result']
    else:
        raise Exception('{}: {}'.format(response.status_code, url))


def set_status(session_id, job_id, source, action, target_status,
               project_code, operator, payload=None, progress=0):
    '''
    set session job status
    '''
    srv_redis = SrvRedisSingleton()
    my_key = "dataaction:{}:{}:{}:{}:{}:{}".format(
        session_id, job_id, action, project_code, operator, source)
    record = {
        "session_id": session_id,
        "job_id": job_id,
        "source": source,
        "action": action,
        "status": target_status,
        "project_code": project_code,
        "operator": operator,
        "progress": progress,
        "payload": payload,
        'update_timestamp': str(round(time.time()))
    }
    my_value = json.dumps(record)
    srv_redis.set_by_key(my_key, my_value)
    return record


def get_status(session_id, job_id, project_code, action, operator=None):
    '''
    get session job status from datastore
    '''
    srv_redis = SrvRedisSingleton()
    my_key = "dataaction:{}:{}:{}:{}".format(
        session_id, job_id, action, project_code)
    if operator:
        my_key = "dataaction:{}:{}:{}:{}:{}".format(
            session_id, job_id, action, project_code, operator)
    res_binary = srv_redis.mget_by_prefix(my_key)
    return [json.loads(record.decode('utf-8')) for record in res_binary] if res_binary else []


def delete_by_session_id(session_id: str, job_id: str = "*", action: str = "*"):
    '''
    delete status by session id
    '''
    srv_redis = SrvRedisSingleton()
    prefix = "dataaction:" + session_id + ":" + job_id + ":" + action
    srv_redis.mdelete_by_prefix(prefix)
    return True


def update_file_operation_logs(owner, operator, download_path, file_size, project_code,
                               generate_id, operation_type="data_upload", extra=None):
    '''
    Endpoint
    /v1/file/actions/logs
    '''
    url = ConfigClass.DATA_OPS_GR + '/v1/file/actions/logs'
    payload = {
        "operation_type": operation_type,
        "owner": owner,
        "operator": operator,
        "input_file_path": download_path,
        "output_file_path": download_path,
        "file_size": file_size,
        "project_code": project_code,
        "generate_id": generate_id
    }
    res_update_file_operation_logs = requests.post(
        url,
        json=payload
    )
    # new audit log api
    url_audit_log = ConfigClass.PROVENANCE_SERVICE + '/v1/audit-logs'
    payload_audit_log = {
        "action": operation_type,
        "operator": operator,
        "target": download_path,
        "outcome": download_path,
        "resource": "file",
        "display_name": os.path.basename(download_path),
        "project_code": project_code,
        "extra": extra if extra else {}
    }
    res_audit_logs = requests.post(
        url_audit_log,
        json=payload_audit_log
    )
    return internal_jsonrespon_handler(url_audit_log, res_audit_logs)


def get_project(project_code):
    '''
    get project if exists(which is valid)
    '''
    url = ConfigClass.BFF_PORTAL + "/v1/project/code/{}".format(project_code)
    res_project = requests.get(url)
    return internal_jsonrespon_handler(url, res_project)


def check_valid_full_path(full_path):
    '''
    check if file already exists(which is invalid)
    '''
    return True


def send_to_queue(payload, logger):
    '''
    send message to queue
    '''
    url = ConfigClass.SEND_MESSAGE_URL
    logger.info("Sending Message To Queue: " + str(payload))
    res = requests.post(
        url=url,
        json=payload,
        headers={"Content-type": "application/json; charset=utf-8"}
    )
    logger.info(res.text)
    return json.loads(res.text)


def get_file_type():
    '''
    change file type based on service namespace
    '''
    return {
        "vre": "processed",
        "greenroom": "raw"
    }.get(os.environ.get('namespace'), "raw")
