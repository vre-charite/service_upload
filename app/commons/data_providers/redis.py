from redis import StrictRedis
from ...config import ConfigClass
from enum import Enum
from ..logger_services.logger_factory_service import SrvLoggerFactory

_logger = SrvLoggerFactory('SrvRedisSingleton').get_logger()

REDIS_INSTANCE = {}

class SrvRedisSingleton():

    def __init__(self):
        self.host = ConfigClass.REDIS_HOST
        self.port = ConfigClass.REDIS_PORT
        self.db = ConfigClass.REDIS_DB
        self.pwd = ConfigClass.REDIS_PASSWORD
        self.connect()

    def connect(self):
        global REDIS_INSTANCE
        if REDIS_INSTANCE:
            self.__instance = REDIS_INSTANCE
            # _logger.info("[SUCCEED] SrvRedisSingleton Connection found, no need for connecting")
            pass
        else:
            REDIS_INSTANCE = StrictRedis(host=self.host,
                                          port=self.port,
                                          db=self.db,
                                          password=self.pwd)
            self.__instance = REDIS_INSTANCE
            _logger.info("[SUCCEED] SrvRedisSingleton Connection initialized.")

    def get_pipeline(self):
        return self.__instance.pipeline()

    def get_by_key(self, key: str):
        return self.__instance.get(key)

    def set_by_key(self, key: str, content: str):
        res = self.__instance.set(key, content)
        # _logger.debug(key + ":  " + content)

    def mget_by_prefix(self, prefix: str):
        # _logger.debug(prefix)
        query = '{}:*'.format(prefix)
        keys = self.__instance.keys(query)
        return self.__instance.mget(keys)

    def check_by_key(self, key: str):
        return self.__instance.exists(key)

    def delete_by_key(self, key: str):
        return self.__instance.delete(key)

    def mdelete_by_prefix(self, prefix: str):
        _logger.debug(prefix)
        query = '{}:*'.format(prefix)
        keys = self.__instance.keys(query)
        for key in keys:
            self.__instance.delete(key)

    def get_by_pattern(self, key: str, pattern: str):
        query_string = '{}:*{}*'.format(key, pattern)
        keys = self.__instance.keys(query_string)
        return self.__instance.mget(keys)

    def publish(self, channel, data):
        res = self.__instance.publish(channel, data)
        return res

    def subscriber(self, channel):
        p = self.__instance.pubsub()
        p.subscribe(channel)
        return p


class ERedisChannels(Enum):
    pipeline_process_start = 0
