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

import mock
import pytest

pytestmark = pytest.mark.asyncio  # set the mark to all tests in this file.


async def test_on_success_return_400_when_session_id_header_is_missing(test_async_client, httpx_mock):
    response = await test_async_client.post(
        '/v1/files',
        json={
            'project_code': 'any',
            'operator': 'me',
            'resumable_identifier': 'fake_global_entity_id',
            'resumable_filename': 'any',
            'resumable_relative_path': './',
            'resumable_total_chunks': 1,
            'resumable_total_size': 10,
        },
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


@mock.patch('os.remove')
async def test_on_success_return_200_when_success(
    fake_remove, test_async_client, httpx_mock, create_job_folder, create_fake_job, mock_minio
):
    httpx_mock.add_response(
        method='DELETE',
        url='http://data_ops_util_service/v2/resource/lock/',
        json={},
        status_code=200,
    )
    httpx_mock.add_response(
        method='POST',
        url='http://data_ops_util_service/v1/filedata/',
        json={'result': {'global_entity_id': 'fake_global_entity_id'}},
        status_code=200,
    )
    httpx_mock.add_response(
        method='POST',
        url='http://provenance_service/v1/audit-logs',
        json={},
        status_code=200,
    )
    httpx_mock.add_response(
        method='POST',
        url='http://queue_service/v1/send_message',
        json={},
        status_code=200,
    )

    response = await test_async_client.post(
        '/v1/files',
        headers={'Session-Id': '1234', 'Authorization': 'token', 'Refresh-Token': 'refresh_token'},
        json={
            'project_code': 'any',
            'operator': 'me',
            'resumable_identifier': 'fake_global_entity_id',
            'resumable_filename': 'any',
            'resumable_relative_path': './',
            'resumable_total_chunks': 1,
            'resumable_total_size': 10,
        },
    )
    assert response.status_code == 200
    result = response.json()['result']
    assert result['session_id'] == '1234'
    assert result['job_id'] == 'fake_global_entity_id'
    assert result['source'] == 'any'
    assert result['action'] == 'data_upload'
    assert result['status'] == 'CHUNK_UPLOADED'
    assert result['operator'] == 'me'
    assert result['payload']['task_id'] == 'fake_global_entity_id'
    assert result['payload']['resumable_identifier'] == 'fake_global_entity_id'
