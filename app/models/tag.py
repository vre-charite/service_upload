from ..commons.data_providers.redis import SrvRedisSingleton
import json


class SrvTagsMgr():
    def __init__(self):
        self.redis_mgr = SrvRedisSingleton()

    def decode_binary(self, payload: str):
        json_str = payload.decode("utf-8")
        return json.loads(json_str)

    def add_freq(self, container_id, tag):
        key = '{}:{}'.format(container_id, tag)
        if self.redis_mgr.check_by_key(key):
            freq = self.decode_binary(
                self.redis_mgr.get_by_key(key)).get('freq')
            self.redis_mgr.set_by_key(key,
                                      json.dumps({'freq': freq+1,
                                                  'name': tag}))
        else:
            self.redis_mgr.set_by_key(
                key, json.dumps({'freq': 1, 'name': tag}))

    def reduce_freq(self, container_id, tag):
        key = '{}:{}'.format(container_id, tag)
        if self.redis_mgr.check_by_key(key):
            freq = self.decode_binary(
                self.redis_mgr.get_by_key(key)).get('freq')
            if freq > 1:
                self.redis_mgr.set_by_key(key,
                                          json.dumps({'freq': freq-1,
                                                      'name': tag}))
            else:
                self.redis_mgr.delete_by_key(key)

    def list_freq_by_project(self, project_id, length):
        tags = self.redis_mgr.mget_by_prefix(str(project_id))
        tags = [self.decode_binary(tag) for tag in tags]
        sorted_res = sorted(tags, key=lambda i: i['freq'], reverse=True)
        return sorted_res[:int(length)]

    def list_freq_by_pattern(self, project_id, pattern, length):
        tags = self.redis_mgr.get_by_pattern(project_id, pattern)
        tags = [self.decode_binary(tag) for tag in tags]
        sorted_tags = sorted(tags, key=lambda k: k['name'])
        return sorted_tags[:int(length)]
