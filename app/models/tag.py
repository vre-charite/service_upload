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

import json

from app.commons.data_providers.redis import SrvAioRedisSingleton


class SrvTagsMgr:
    def __init__(self):
        self.redis_mgr = SrvAioRedisSingleton()

    def decode_binary(self, payload: str):
        json_str = payload.decode('utf-8')
        return json.loads(json_str)

    async def add_freq(self, container_id, tag):
        key = '{}:{}'.format(container_id, tag)
        if await self.redis_mgr.check_by_key(key):
            freq = self.decode_binary(await self.redis_mgr.get_by_key(key)).get('freq')
            await self.redis_mgr.set_by_key(key, json.dumps({'freq': freq + 1, 'name': tag}))
        else:
            await self.redis_mgr.set_by_key(key, json.dumps({'freq': 1, 'name': tag}))

    async def reduce_freq(self, container_id, tag):
        key = '{}:{}'.format(container_id, tag)
        if await self.redis_mgr.check_by_key(key):
            freq = self.decode_binary(await self.redis_mgr.get_by_key(key)).get('freq')
            if freq > 1:
                await self.redis_mgr.set_by_key(key, json.dumps({'freq': freq - 1, 'name': tag}))
            else:
                await self.redis_mgr.delete_by_key(key)

    async def list_freq_by_project(self, project_id, length):
        tags = await self.redis_mgr.mget_by_prefix(str(project_id))
        tags = [self.decode_binary(tag) for tag in tags]
        sorted_res = sorted(tags, key=lambda i: i['freq'], reverse=True)
        return sorted_res[: int(length)]

    async def list_freq_by_pattern(self, project_id, pattern, length):
        tags = await self.redis_mgr.get_by_pattern(project_id, pattern)
        tags = [self.decode_binary(tag) for tag in tags]
        sorted_tags = sorted(tags, key=lambda k: k['name'])
        return sorted_tags[: int(length)]
