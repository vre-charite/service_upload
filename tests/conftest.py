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

import asyncio
import json
import os
import shutil
from io import BytesIO

import pytest
from aioredis import StrictRedis
from async_asgi_testclient import TestClient as TestAsyncClient
from fastapi.testclient import TestClient
from httpx import Response
from starlette.config import environ
from urllib3 import HTTPResponse

environ['CONFIG_CENTER_ENABLED'] = 'false'
environ['CORE_ZONE_LABEL'] = 'Core'
environ['GREEN_ZONE_LABEL'] = 'Greenroom'

environ['ENTITYINFO_SERVICE'] = 'http://ENTITYINFO_SERVICE'
environ['NEO4J_SERVICE'] = 'http://NEO4J_SERVICE'
environ['QUEUE_SERVICE'] = 'http://QUEUE_SERVICE'
environ['PROVENANCE_SERVICE'] = 'http://PROVENANCE_SERVICE'
environ['UTILITY_SERVICE'] = 'http://UTILITY_SERVICE'
environ['DATA_OPS_UTIL'] = 'http://DATA_OPS_UTIL_SERVICE'

environ['MINIO_OPENID_CLIENT'] = 'MINIO_OPENID_CLIENT'
environ['MINIO_ENDPOINT'] = 'MINIO_ENDPOINT'
environ['MINIO_HTTPS'] = 'true'
environ['KEYCLOAK_URL'] = 'KEYCLOAK_URL'
environ['MINIO_ACCESS_KEY'] = 'MINIO_ACCESS_KEY'
environ['MINIO_SECRET_KEY'] = 'MINIO_SECRET_KEY'
environ['KEYCLOAK_MINIO_SECRET'] = 'KEYCLOAK_MINIO_SECRET'

environ['REDIS_PORT'] = '6379'
environ['REDIS_DB'] = '0'
environ['REDIS_PASSWORD'] = ''
environ['ROOT_PATH'] = './tests/'


@pytest.fixture(scope='session')
def event_loop(request):
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
    asyncio.set_event_loop_policy(None)


@pytest.fixture(autouse=True)
async def clean_up_redis():
    cache = StrictRedis(host=environ.get('REDIS_HOST'))
    await cache.flushall()


@pytest.fixture(autouse=True)
def mock_settings(monkeypatch):
    from app.config import ConfigClass

    monkeypatch.setattr(ConfigClass, 'TEMP_BASE', './tests/')


@pytest.fixture
def test_client():
    from run import app

    return TestClient(app)


@pytest.fixture
def test_async_client():
    from run import app

    return TestAsyncClient(app)


@pytest.fixture
def mock_get_geid_request(httpx_mock):
    # configService
    httpx_mock.add_response(
        method='GET',
        url='http://utility_service/v1/utility/id',
        json={
            'result': 'fake_global_entity_id',
        },
        status_code=200,
    )


@pytest.fixture()
def create_job_folder():
    folder_path = 'tests/fake_global_entity_id'
    os.mkdir(folder_path)
    with open(f'{folder_path}/any_part_001', 'x') as f:
        f.write('Create a new text file!')
    yield
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)


@pytest.fixture
async def create_fake_job(monkeypatch):
    from app.commons.data_providers.redis import SrvAioRedisSingleton

    fake_job = {
        'session_id': '1234',
        'job_id': 'fake_global_entity_id',
        'source': 'any',
        'action': 'data_upload',
        'status': 'PRE_UPLOADED',
        'project_code': 'any',
        'operator': 'me',
        'progress': 0,
        'payload': {
            'task_id': 'fake_global_entity_id',
            'resumable_identifier': 'fake_global_entity_id',
            'parent_folder_geid': None,
        },
        'update_timestamp': '1643041439',
    }

    async def fake_return(x, y):
        return [bytes(json.dumps(fake_job), 'utf-8')]

    monkeypatch.setattr(SrvAioRedisSingleton, 'mget_by_prefix', fake_return)


@pytest.fixture
def mock_minio(monkeypatch):
    from app.commons.service_connection.minio_client import Minio

    class FakeObject:
        size = b'a'

    http_response = HTTPResponse()
    response = Response(status_code=200)
    response.raw = http_response
    response.raw._fp = BytesIO(b'File like object')

    monkeypatch.setattr(Minio, 'stat_object', lambda x, y, z: FakeObject())
    monkeypatch.setattr(Minio, 'get_object', lambda x, y, z: http_response)
    monkeypatch.setattr(Minio, 'list_buckets', lambda x: [])
    monkeypatch.setattr(Minio, 'fget_object', lambda *x: [])
