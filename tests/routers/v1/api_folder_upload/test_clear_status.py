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


async def test_get_status_return_400_when_session_id_header_is_missing(test_async_client, httpx_mock):
    response = await test_async_client.delete(
        '/v1/files/jobs',
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


async def test_get_status_return_200_when_success(test_async_client, httpx_mock):
    response = await test_async_client.delete(
        '/v1/files/jobs',
        headers={'Session-Id': '1234'},
    )
    assert response.status_code == 200
    assert response.json() == {
        'code': 200,
        'error_msg': '',
        'page': 0,
        'total': 1,
        'num_of_pages': 1,
        'result': {'message': 'Success'},
    }
