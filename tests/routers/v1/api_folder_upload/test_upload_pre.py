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

from unittest import mock

import pytest

from app.routers.v1.api_data_upload import FolderMgr
from app.routers.v1.api_data_upload import FsmMgrUpload

pytestmark = pytest.mark.asyncio  # set the mark to all tests in this file.


async def test_files_jobs_return_400_when_session_id_header_is_missing(test_async_client, httpx_mock):
    response = await test_async_client.post(
        '/v1/files/jobs', json={'project_code': 'any', 'operator': 'me', 'data': [{'resumable_filename': 'any'}]}
    )
    assert response.status_code == 400
    assert response.json() == {
        'code': 400,
        'error_msg': 'Invalid Session ID: None',
        'page': 0,
        'total': 1,
        'num_of_pages': 1,
        'result': {},
    }


async def test_files_jobs_return_400_when_session_job_type_is_wrong(test_async_client, httpx_mock):
    response = await test_async_client.post(
        '/v1/files/jobs',
        headers={'Session-Id': '1234'},
        json={'project_code': 'any', 'operator': 'me', 'job_type': 'any', 'data': [{'resumable_filename': 'any'}]},
    )
    assert response.status_code == 400
    assert response.json() == {
        'code': 400,
        'error_msg': 'Invalid job type: any',
        'page': 0,
        'total': 1,
        'num_of_pages': 1,
        'result': [],
    }


async def test_files_jobs_return_404_when_project_info_not_found(test_async_client, httpx_mock):
    httpx_mock.add_response(
        method='POST',
        url='http://neo4j_service/v1/neo4j/nodes/Container/query',
        json=[],
        status_code=200,
    )

    response = await test_async_client.post(
        '/v1/files/jobs',
        headers={'Session-Id': '1234'},
        json={'project_code': 'any', 'operator': 'me', 'job_type': 'AS_FILE', 'data': [{'resumable_filename': 'any'}]},
    )
    assert response.status_code == 404
    assert response.json() == {
        'code': 404,
        'error_msg': 'Container or Dataset not found',
        'page': 0,
        'total': 1,
        'num_of_pages': 1,
        'result': {},
    }


async def test_file_with_conflict_path_should_return_409(test_async_client, httpx_mock, mock_get_geid_request):
    httpx_mock.add_response(
        method='POST',
        url='http://neo4j_service/v1/neo4j/nodes/Container/query',
        json=[{'any': 'any', 'global_entity_id': 'fake_global_entity_id'}],
        status_code=200,
    )
    httpx_mock.add_response(
        method='POST',
        url='http://neo4j_service/v1/neo4j/nodes/Core/query',
        json={
            'any': 'any',
        },
        status_code=200,
    )

    response = await test_async_client.post(
        '/v1/files/jobs',
        headers={'Session-Id': '1234'},
        json={'project_code': 'any', 'operator': 'me', 'job_type': 'AS_FILE', 'data': [{'resumable_filename': 'any'}]},
    )
    assert response.status_code == 409
    assert response.json() == {
        'code': 409,
        'error_msg': '[Invalid File] File Name has already taken by other resources(file/folder)',
        'page': 0,
        'total': 1,
        'num_of_pages': 1,
        'result': {'failed': [{'name': 'any', 'relative_path': '', 'type': 'File'}]},
    }


async def test_files_jobs_should_return_200_when_success(
    test_async_client, httpx_mock, mock_get_geid_request, create_job_folder
):
    httpx_mock.add_response(
        method='POST',
        url='http://neo4j_service/v1/neo4j/nodes/Container/query',
        json=[{'any': 'any', 'global_entity_id': 'fake_global_entity_id'}],
        status_code=200,
    )
    httpx_mock.add_response(
        method='POST',
        url='http://neo4j_service/v1/neo4j/nodes/Core/query',
        json={},
        status_code=200,
    )
    httpx_mock.add_response(
        method='POST',
        url='http://data_ops_util_service/v2/resource/lock/',
        json={},
        status_code=200,
    )
    response = await test_async_client.post(
        '/v1/files/jobs',
        headers={'Session-Id': '1234'},
        json={'project_code': 'any', 'operator': 'me', 'job_type': 'AS_FILE', 'data': [{'resumable_filename': 'any'}]},
    )
    assert response.status_code == 200
    result = response.json()['result'][0]
    assert result['session_id'] == '1234'
    assert result['job_id'] == 'fake_global_entity_id'
    assert result['source'] == 'any'
    assert result['action'] == 'data_upload'
    assert result['status'] == 'PRE_UPLOADED'
    assert result['operator'] == 'me'
    assert result['payload']['task_id'] == 'fake_global_entity_id'
    assert result['payload']['resumable_identifier'] == 'fake_global_entity_id'


async def test_files_jobs_type_AS_FOLDER_should_return_200_when_success(
    test_async_client, httpx_mock, mock_get_geid_request, create_job_folder
):
    httpx_mock.add_response(
        method='POST',
        url='http://neo4j_service/v1/neo4j/nodes/Container/query',
        json=[{'any': 'any', 'global_entity_id': 'fake_global_entity_id'}],
        status_code=200,
    )
    httpx_mock.add_response(
        method='POST',
        url='http://neo4j_service/v1/neo4j/nodes/Core/query',
        json={},
        status_code=200,
    )
    httpx_mock.add_response(
        method='POST',
        url='http://data_ops_util_service/v2/resource/lock/',
        json={},
        status_code=200,
    )
    response = await test_async_client.post(
        '/v1/files/jobs',
        headers={'Session-Id': '1234'},
        json={
            'project_code': 'any',
            'operator': 'me',
            'job_type': 'AS_FOLDER',
            'data': [{'resumable_filename': 'any'}],
        },
    )
    assert response.status_code == 200
    result = response.json()['result'][0]
    assert result['session_id'] == '1234'
    assert result['job_id'] == 'fake_global_entity_id'
    assert result['source'] == 'any'
    assert result['action'] == 'data_upload'
    assert result['status'] == 'PRE_UPLOADED'
    assert result['operator'] == 'me'
    assert result['payload']['task_id'] == 'fake_global_entity_id'
    assert result['payload']['resumable_identifier'] == 'fake_global_entity_id'


async def test_files_jobs_adds_folder_should_return_200_when_success(
    test_async_client, httpx_mock, mock_get_geid_request, create_job_folder
):
    httpx_mock.add_response(
        method='POST',
        url='http://neo4j_service/v1/neo4j/nodes/Container/query',
        json=[{'any': 'any', 'global_entity_id': 'fake_global_entity_id'}],
        status_code=200,
    )
    httpx_mock.add_response(
        method='POST',
        url='http://neo4j_service/v1/neo4j/nodes/Core/query',
        json={},
        status_code=200,
    )
    httpx_mock.add_response(
        method='POST',
        url='http://data_ops_util_service/v2/resource/lock/',
        json={},
        status_code=200,
    )
    httpx_mock.add_response(
        method='POST',
        url='http://neo4j_service/v2/neo4j/nodes/query',
        json={'result': {}},
        status_code=200,
    )
    httpx_mock.add_response(
        method='POST',
        url='http://entityinfo_service/v1/folders/batch',
        json={'result': {'name': 'any'}},
        status_code=200,
    )
    httpx_mock.add_response(
        method='POST',
        url='http://neo4j_service/v1/neo4j/relations/own/batch',
        json={'result': {'name': 'any'}},
        status_code=200,
    )
    httpx_mock.add_response(
        method='DELETE',
        url='http://data_ops_util_service/v2/resource/lock/',
        json={},
        status_code=200,
    )

    response = await test_async_client.post(
        '/v1/files/jobs',
        headers={'Session-Id': '1234'},
        json={
            'project_code': 'any',
            'operator': 'me',
            'job_type': 'AS_FOLDER',
            'data': [{'resumable_filename': 'any', 'resumable_relative_path': 'tests/tmp/'}],
        },
    )
    assert response.status_code == 200
    result = response.json()['result'][0]
    assert result['session_id'] == '1234'
    assert result['job_id'] == 'fake_global_entity_id'
    assert result['source'] == 'tests/tmp/any'
    assert result['action'] == 'data_upload'
    assert result['status'] == 'PRE_UPLOADED'
    assert result['operator'] == 'me'
    assert result['payload']['task_id'] == 'fake_global_entity_id'
    assert result['payload']['resumable_identifier'] == 'fake_global_entity_id'


async def test_files_jobs_adds_folder_should_return_error_when_creates_fails(
    test_async_client, httpx_mock, mock_get_geid_request, create_job_folder
):
    httpx_mock.add_response(
        method='POST',
        url='http://neo4j_service/v1/neo4j/nodes/Container/query',
        json=[{'any': 'any', 'global_entity_id': 'fake_global_entity_id'}],
        status_code=200,
    )
    httpx_mock.add_response(
        method='POST',
        url='http://neo4j_service/v1/neo4j/nodes/Core/query',
        json={},
        status_code=200,
    )
    httpx_mock.add_response(
        method='POST',
        url='http://data_ops_util_service/v2/resource/lock/',
        json={},
        status_code=200,
    )
    httpx_mock.add_response(
        method='POST',
        url='http://neo4j_service/v2/neo4j/nodes/query',
        json={'result': {}},
        status_code=200,
    )
    httpx_mock.add_response(
        method='POST',
        url='http://entityinfo_service/v1/folders/batch',
        json={'result': {'name': 'any'}},
        status_code=200,
    )
    httpx_mock.add_response(
        method='POST',
        url='http://neo4j_service/v1/neo4j/relations/own/batch',
        json={},
        status_code=500,
    )
    httpx_mock.add_response(
        method='DELETE',
        url='http://data_ops_util_service/v2/resource/lock/',
        json={},
        status_code=200,
    )

    response = await test_async_client.post(
        '/v1/files/jobs',
        headers={'Session-Id': '1234'},
        json={
            'project_code': 'any',
            'operator': 'me',
            'job_type': 'AS_FOLDER',
            'data': [{'resumable_filename': 'any', 'resumable_relative_path': 'tests/tmp/'}],
        },
    )
    assert response.status_code == 409
    assert response.json() == {
        'code': 409,
        'error_msg': '',
        'page': 0,
        'total': 1,
        'num_of_pages': 1,
        'result': '[bulk_link_project Error] 500 {}',
    }


async def test_files_jobs_should_return_error_when_lock_fails(
    test_async_client, httpx_mock, mock_get_geid_request, create_job_folder
):
    httpx_mock.add_response(
        method='POST',
        url='http://neo4j_service/v1/neo4j/nodes/Container/query',
        json=[{'any': 'any', 'global_entity_id': 'fake_global_entity_id'}],
        status_code=200,
    )
    httpx_mock.add_response(
        method='POST',
        url='http://neo4j_service/v1/neo4j/nodes/Core/query',
        json={},
        status_code=200,
    )
    httpx_mock.add_response(
        method='POST',
        url='http://data_ops_util_service/v2/resource/lock/',
        json={},
        status_code=500,
    )
    response = await test_async_client.post(
        '/v1/files/jobs',
        headers={'Session-Id': '1234'},
        json={
            'project_code': 'any',
            'operator': 'me',
            'job_type': 'AS_FOLDER',
            'data': [{'resumable_filename': 'any'}],
        },
    )
    assert response.status_code == 200
    assert response.json() == {
        'code': 409,
        'error_msg': 'resource core-any/any already in used',
        'page': 0,
        'total': 1,
        'num_of_pages': 1,
        'result': {},
    }


@mock.patch.object(FolderMgr, 'create')
@pytest.mark.parametrize(
    'exception_raised,error_msg,status_code', [(FileExistsError, 'file already exist error', 409), (Exception, '', 200)]
)
async def test_files_jobs_should_return_error_when_file_error(
    fake_create,
    test_async_client,
    httpx_mock,
    mock_get_geid_request,
    create_job_folder,
    exception_raised,
    error_msg,
    status_code,
):
    httpx_mock.add_response(
        method='POST',
        url='http://neo4j_service/v1/neo4j/nodes/Container/query',
        json=[{'any': 'any', 'global_entity_id': 'fake_global_entity_id'}],
        status_code=200,
    )
    httpx_mock.add_response(
        method='POST',
        url='http://neo4j_service/v1/neo4j/nodes/Core/query',
        json={},
        status_code=200,
    )
    httpx_mock.add_response(
        method='POST',
        url='http://data_ops_util_service/v2/resource/lock/',
        json={},
        status_code=200,
    )
    httpx_mock.add_response(
        method='DELETE',
        url='http://data_ops_util_service/v2/resource/lock/',
        json={},
        status_code=200,
    )
    fake_create.side_effect = exception_raised(error_msg)
    response = await test_async_client.post(
        '/v1/files/jobs',
        headers={'Session-Id': '1234'},
        json={
            'project_code': 'any',
            'operator': 'me',
            'job_type': 'AS_FOLDER',
            'data': [{'resumable_filename': 'any'}],
        },
    )
    assert response.status_code == status_code
    assert response.json() == {
        'code': status_code,
        'error_msg': error_msg,
        'page': 0,
        'total': 1,
        'num_of_pages': 1,
        'result': [],
    }


@mock.patch.object(FsmMgrUpload, 'get_kv_entity')
async def test_files_jobs_should_return_error_when_FsmMgrUpload_raise_exception(
    fake_get_kv_entity, test_async_client, httpx_mock, mock_get_geid_request, create_job_folder
):
    httpx_mock.add_response(
        method='POST',
        url='http://neo4j_service/v1/neo4j/nodes/Container/query',
        json=[{'any': 'any', 'global_entity_id': 'fake_global_entity_id'}],
        status_code=200,
    )
    httpx_mock.add_response(
        method='POST',
        url='http://neo4j_service/v1/neo4j/nodes/Core/query',
        json={},
        status_code=200,
    )
    httpx_mock.add_response(
        method='POST',
        url='http://data_ops_util_service/v2/resource/lock/',
        json={},
        status_code=200,
    )
    fake_get_kv_entity.side_effect = Exception()
    response = await test_async_client.post(
        '/v1/files/jobs',
        headers={'Session-Id': '1234'},
        json={'project_code': 'any', 'operator': 'me', 'job_type': 'AS_FILE', 'data': [{'resumable_filename': 'any'}]},
    )
    assert response.status_code == 500
    assert response.json() == {
        'code': 500,
        'error_msg': '[Internal] api_data_upload ',
        'page': 0,
        'total': 1,
        'num_of_pages': 1,
        'result': None,
    }
