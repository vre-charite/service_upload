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

import pytest

pytestmark = pytest.mark.asyncio  # set the mark to all tests in this file.


async def test_upload_chunks_return_400_when_session_id_header_is_missing(test_async_client, httpx_mock):
    response = await test_async_client.post(
        '/v1/files/chunks',
        files={
            'project_code': 'any',
            'operator': 'me',
            'resumable_identifier': 'fake_global_entity_id',
            'resumable_filename': 'any',
            'resumable_chunk_number': str(1),
            'resumable_total_chunks': str(1),
            'resumable_total_size': str(10),
            'chunk_data': ('chunk.txt', open('tests/routers/v1/api_folder_upload/chunk.txt', 'rb'), 'text/plain'),
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


async def test_upload_chunks_return_200_when_when_success(
    test_async_client, httpx_mock, create_job_folder, create_fake_job
):
    response = await test_async_client.post(
        '/v1/files/chunks',
        headers={'Session-Id': '1234'},
        files={
            'project_code': 'any',
            'operator': 'me',
            'resumable_identifier': 'fake_global_entity_id',
            'resumable_filename': 'any',
            'resumable_chunk_number': str(1),
            'resumable_total_chunks': str(1),
            'resumable_total_size': str(10),
            'chunk_data': ('chunk.txt', open('tests/routers/v1/api_folder_upload/chunk.txt', 'rb'), 'text/plain'),
        },
    )
    assert response.status_code == 200
    assert response.json() == {
        'code': 200,
        'error_msg': '',
        'page': 0,
        'total': 1,
        'num_of_pages': 1,
        'result': {'msg': 'Succeed'},
    }


async def test_upload_chunks_return_error_when_when_fails(test_async_client, httpx_mock, create_fake_job):
    response = await test_async_client.post(
        '/v1/files/chunks',
        headers={'Session-Id': '1234'},
        files={
            'project_code': 'any',
            'operator': 'me',
            'resumable_identifier': 'any',
            'resumable_filename': 'any',
            'resumable_chunk_number': str(1),
            'resumable_total_chunks': str(1),
            'resumable_total_size': str(10),
            'chunk_data': ('chunk.txt', open('tests/routers/v1/api_folder_upload/chunk.txt', 'rb'), 'text/plain'),
        },
    )
    assert response.status_code == 500
    assert response.json() == {
        'code': 500,
        'error_msg': "[Internal] api_data_upload [Errno 2] No such file or directory: './tests/any/any_part_001'",
        'page': 0,
        'total': 1,
        'num_of_pages': 1,
        'result': None,
    }
