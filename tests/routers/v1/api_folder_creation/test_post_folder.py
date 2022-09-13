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

def test_create_new_folder_in_entity_service_return_200(mock_get_geid_request, test_client, httpx_mock):
    folder_name = 'test_core3'

    httpx_mock.add_response(
        method='POST',
        url='http://neo4j_service/v1/neo4j/nodes/Container/query',
        json={'any': 'any'},
        status_code=200,
    )
    httpx_mock.add_response(
        method='POST',
        url='http://neo4j_service/v1/neo4j/nodes/Folder/query',
        json=[
            {
                'name': 'any_name',
                'global_entity_id': 'any_hash',
                'folder_level': 1,
                'labels': ['any_label'],
                'folder_relative_path': './folder',
            }
        ],
        status_code=200,
    )
    httpx_mock.add_response(
        method='POST',
        url='http://neo4j_service/v1/neo4j/nodes/Greenroom/query',
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

    # entity service call
    httpx_mock.add_response(
        method='POST',
        url='http://entityinfo_service/v1/folders',
        json={'result': {'name': folder_name}},
        status_code=200,
    )

    result = test_client.post(
        'v1/folder',
        json={
            'folder_name': folder_name,
            'project_code': 'test_folder_creation',
            'uploader': 'admin',
            'destination_geid': 'any',
            'tags': [],
        },
    )
    res = result.json()
    assert result.status_code == 200
    assert res['result']['name'] == folder_name


def test_add_a_subfolder_when_request_body_has_destination_geid(mock_get_geid_request, test_client, httpx_mock):
    """I couldn't find anything specific for a sub folder besides this destination_geid.

    If it confirms that it's only that, we could remove this test and add a parameter to the previous test to cover this
    scenario.
    """
    folder_name = 'sub_folder03'
    httpx_mock.add_response(
        method='POST',
        url='http://neo4j_service/v1/neo4j/nodes/Container/query',
        json={'any': 'any'},
        status_code=200,
    )
    httpx_mock.add_response(
        method='POST',
        url='http://neo4j_service/v1/neo4j/nodes/Folder/query',
        json={},
        status_code=200,
    )
    httpx_mock.add_response(
        method='POST',
        url='http://neo4j_service/v1/neo4j/nodes/Greenroom/query',
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
    httpx_mock.add_response(
        method='POST',
        url='http://entityinfo_service/v1/folders',
        json={'result': {'name': folder_name}},
        status_code=200,
    )

    result = test_client.post(
        'v1/folder',
        json={
            'folder_name': folder_name,
            'project_code': 'test_folder_creation',
            'uploader': 'admin',
            'tags': [],
            'destination_geid': 'any_container_unique_id',
        },
    )
    res = result.json()
    assert result.status_code == 200
    assert res['result']['name'] == folder_name
