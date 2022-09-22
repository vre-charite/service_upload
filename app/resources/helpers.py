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

import json
import os
from zipfile import ZipFile

import httpx
from starlette.concurrency import run_in_threadpool

from app.commons.data_providers.redis import SrvAioRedisSingleton
from app.config import ConfigClass

from .error_handler import internal_jsonrespon_handler


def generate_archive_preview(file_path, file_type='zip'):
    results = {}
    if file_type == 'zip':
        ArchiveFile = ZipFile

    with ArchiveFile(file_path, 'r') as archive:
        for file in archive.infolist():
            # get filename for file
            filename = file.filename.split('/')[-1]
            if not filename:
                # get filename for folder
                filename = file.filename.split('/')[-2]
            current_path = results
            for path in file.filename.split('/')[:-1]:
                if path:
                    if not current_path.get(path):
                        current_path[path] = {'is_dir': True}
                    current_path = current_path[path]

            if not file.is_dir():
                current_path[filename] = {
                    'filename': filename,
                    'size': file.file_size,
                    'is_dir': False,
                }
    return results


async def async_get_geid():
    """this function exists as proof of concept.

    as soon the service is full async this should be deleted.
    """
    return await run_in_threadpool(get_geid)


def get_geid():
    """get geid http://10.3.7.222:5062/v1/utility/id?entity_type=data_upload."""
    url = ConfigClass.UTILITY_SERVICE + 'utility/id'
    with httpx.Client() as client:
        response = client.get(url)
    if response.status_code == 200:
        return response.json()['result']
    else:
        raise Exception('{}: {}'.format(response.status_code, url))


def bulk_get_geid(number):
    url = ConfigClass.UTILITY_SERVICE + 'utility/id/batch'
    with httpx.Client() as client:
        response = client.get(url, params={'number': number})
    if response.status_code == 200:
        return response.json()['result']
    else:
        raise Exception('{}: {}'.format(response.status_code, url))


async def delete_by_session_id(session_id: str, job_id: str = '*', action: str = '*'):
    srv_redis = SrvAioRedisSingleton()
    prefix = 'dataaction:' + session_id + ':' + job_id + ':' + action
    await srv_redis.mdelete_by_prefix(prefix)
    return True


def update_file_operation_logs(operator, download_path, project_code, operation_type='data_upload', extra=None):
    """Endpoint."""

    # new audit log api
    url_audit_log = ConfigClass.PROVENANCE_SERVICE + 'audit-logs'
    payload_audit_log = {
        'action': operation_type,
        'operator': operator,
        'target': download_path,
        'outcome': download_path,
        'resource': 'file',
        'display_name': os.path.basename(download_path),
        'project_code': project_code,
        'extra': extra if extra else {},
    }
    with httpx.Client() as client:
        res_audit_logs = client.post(url_audit_log, json=payload_audit_log)
    return internal_jsonrespon_handler(url_audit_log, res_audit_logs)


async def get_project(project_code):
    """get project if exists(which is valid)"""
    data = {
        'code': project_code,
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(ConfigClass.NEO4J_SERVICE + 'nodes/Container/query', json=data)
    result = response.json()
    if not result:
        return result
    return result[0]


def send_to_queue(payload, logger):
    """send message to queue."""
    url = ConfigClass.QUEUE_SERVICE + 'send_message'
    logger.info('Sending Message To Queue: ' + str(payload))
    with httpx.Client() as client:
        res = client.post(url=url, json=payload, headers={'Content-type': 'application/json; charset=utf-8'})
    logger.info(res.text)
    return json.loads(res.text)
