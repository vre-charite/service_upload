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

import httpx
from starlette.concurrency import run_in_threadpool

from app.config import ConfigClass


async def async_lock_resource(resource_key: str, operation: str) -> dict:
    return await run_in_threadpool(lock_resource, resource_key, operation)


async def async_unlock_resource(resource_key: str, operation: str) -> dict:
    return await run_in_threadpool(unlock_resource, resource_key, operation)


def lock_resource(resource_key: str, operation: str) -> dict:
    # operation can be either read or write
    url = ConfigClass.DATA_OPS_UT_V2 + 'resource/lock/'
    post_json = {'resource_key': resource_key, 'operation': operation}
    with httpx.Client() as client:
        response = client.post(url, json=post_json)
    if response.status_code != 200:
        raise Exception('resource %s already in used' % resource_key)

    return response.json()


def unlock_resource(resource_key: str, operation: str) -> dict:
    # operation can be either read or write
    url = ConfigClass.DATA_OPS_UT_V2 + 'resource/lock/'
    post_json = {'resource_key': resource_key, 'operation': operation}

    with httpx.Client() as client:
        """httpx.delete doesn't support request body.

        https://www.python-httpx.org/compatibility/#request-body-on-http-methods
        """
        response = client.request(url=url, method='DELETE', json=post_json)
    if response.status_code != 200:
        raise Exception('Error when unlock resource %s' % resource_key)

    return response.json()
