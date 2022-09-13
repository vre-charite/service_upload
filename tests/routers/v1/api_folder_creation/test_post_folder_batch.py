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

def test_batch_create_folder_should_return_200(test_client, httpx_mock):
    httpx_mock.add_response(
        method='GET',
        url='http://utility_service/v1/utility/id/batch?number=1',
        json={'result': ['any_id']},
        status_code=200,
    )
    httpx_mock.add_response(
        method='POST',
        url='http://entityinfo_service/v1/folders/batch',
        json={'result': {'name': 'folder_name'}},
        status_code=200,
    )
    result = test_client.post(
        'v1/folder/batch',
        json={
            'zone': 'us-east-1',
            'folder_name': 'folder_name',
            'project_code_list': ['test_folder_creation'],
            'uploader': 'admin',
            'destination_geid': 'any',
            'tags': [],
        },
    )
    res = result.json()
    assert res['result']['name'] == 'folder_name'
    assert result.status_code == 200


def test_batch_should_return_error_when_file_name_is_not_valid(test_client, httpx_mock):
    httpx_mock.add_response(
        method='GET',
        url='http://utility_service/v1/utility/id/batch?number=1',
        json={'result': ['any_id']},
        status_code=200,
    )
    httpx_mock.add_response(
        method='POST',
        url='http://entityinfo_service/v1/folders/batch',
        status_code=500,
    )

    result = test_client.post(
        'v1/folder/batch',
        json={
            'zone': 'us-east-1',
            'folder_name': 'folder_name',
            'project_code_list': ['test_folder_creation'],
            'uploader': 'admin',
            'destination_geid': 'any',
            'tags': [],
        },
    )
    assert result.status_code == 500
    assert result.json() == {
        'code': 500,
        'error_msg': '[Internal] api_folder_creation Error while bulk creating folder ',
        'page': 0,
        'total': 1,
        'num_of_pages': 1,
        'result': None,
    }


def test_batch_should_return_error_when_folder_name_is_not_valid(test_client, httpx_mock):
    result = test_client.post(
        'v1/folder/batch',
        json={
            'zone': 'us-east-1',
            'folder_name': 'folder_name_must_to_be_too_long_for_this',
            'project_code_list': ['test_folder_creation'],
            'uploader': 'admin',
            'destination_geid': 'any',
            'tags': [],
        },
    )
    assert result.status_code == 400
    assert result.json() == {
        'code': 400,
        'error_msg': ['Folder name should not contain : ', "(\\/:?*<>|”') and must contain 1 to 20 characters"],
        'page': 0,
        'total': 1,
        'num_of_pages': 1,
        'result': {'failed': "Folder should not contain : (\\/:?*<>|”') and must contain 1 to 20 characters"},
    }
