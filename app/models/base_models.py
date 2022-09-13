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

from enum import Enum

from fastapi.responses import JSONResponse
from pydantic import BaseModel


class EAPIResponseCode(Enum):
    # fastapi.status implements something like this already
    success = 200
    internal_error = 500
    bad_request = 400
    not_found = 404
    forbidden = 403
    unauthorized = 401
    conflict = 409


class APIResponse(BaseModel):
    code: EAPIResponseCode = EAPIResponseCode.success
    error_msg: str = ''
    page: int = 0
    total: int = 1
    num_of_pages: int = 1
    result = []

    def json_response(self):
        data = self.dict()
        data['code'] = self.code.value
        return JSONResponse(status_code=self.code.value, content=data)


class PaginationRequest(BaseModel):
    page: int = 0
    page_size: int = 25
    order: str = 'asc'
    sorting: str = 'createTime'
