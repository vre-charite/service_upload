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

from app.resources.helpers import async_get_geid
from app.resources.helpers import get_geid


def test_get_id_should_return_global_entity_id_in_result_when_200(httpx_mock, mock_get_geid_request):
    result = get_geid()
    assert result == 'fake_global_entity_id'


def test_get_id_should_raise_exception_when_not_200(httpx_mock):
    httpx_mock.add_response(
        method='GET',
        url='http://UTILITY_SERVICE/v1/utility/id',
        status_code=404,
    )
    with pytest.raises(Exception) as excinfo:
        get_geid()
    assert str(excinfo.value) == '404: http://UTILITY_SERVICE/v1/utility/id'


@pytest.mark.asyncio
async def test_async_get_geid_should_return_200(httpx_mock, mock_get_geid_request):
    result = await async_get_geid()
    assert result == 'fake_global_entity_id'
