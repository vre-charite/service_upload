import os
import requests
from requests.models import HTTPError
from pydantic import BaseSettings, Extra
from typing import Dict, Set, List, Any
from functools import lru_cache

SRV_NAMESPACE = os.environ.get("APP_NAME", "service_upload")
CONFIG_CENTER_ENABLED = os.environ.get("CONFIG_CENTER_ENABLED", "false")
CONFIG_CENTER_BASE_URL = os.environ.get("CONFIG_CENTER_BASE_URL", "NOT_SET")

def load_vault_settings(settings: BaseSettings) -> Dict[str, Any]:
    if CONFIG_CENTER_ENABLED == "false":
        return {}
    else:
        return vault_factory(CONFIG_CENTER_BASE_URL)

def vault_factory(config_center) -> dict:
    url = f"{config_center}/v1/utility/config/{SRV_NAMESPACE}"
    config_center_respon = requests.get(url)
    if config_center_respon.status_code != 200:
        raise HTTPError(config_center_respon.text)
    return config_center_respon.json()['result']


class Settings(BaseSettings):
    port: int = 5079
    host: str = "127.0.0.1"
    env: str = ""
    namespace: str = ""
    
    # disk mounts
    NFS_ROOT_PATH: str = "./"
    VRE_ROOT_PATH: str = "/vre-data"
    ROOT_PATH: str = {
        "vre": "/vre-data"
    }.get(os.environ.get('namespace'), "/data/vre-storage")

    # microservices
    NEO4J_SERVICE: str
    ENTITYINFO_SERVICE: str
    QUEUE_SERVICE: str
    DATA_OPS_GR: str
    DATA_OPS_UTIL: str
    PROVENANCE_SERVICE: str
    UTILITY_SERVICE: str
    KEYCLOAK_MINIO_SECRET: str

    KEYCLOAK_VRE_SECRET: str

    # minio
    MINIO_OPENID_CLIENT: str
    MINIO_ENDPOINT: str
    MINIO_HTTPS: bool = False
    KEYCLOAK_URL: str
    MINIO_TEST_PASS: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str

    # download secret
    DOWNLOAD_KEY: str = "indoc101"
    DOWNLOAD_TOKEN_EXPIRE_AT: int = 5
    # Redis Service
    REDIS_HOST: str
    REDIS_PORT: str
    REDIS_DB: str
    REDIS_PASSWORD: str
    
    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        extra = Extra.allow

        @classmethod
        def customise_sources(
            cls,
            init_settings,
            env_settings,
            file_secret_settings,
        ):
            return (
                load_vault_settings,
                env_settings,
                init_settings,
                file_secret_settings,
            )
    

@lru_cache(1)
def get_settings():
    settings =  Settings()
    return settings

class ConfigClass(object):
    settings = get_settings()

    version = "0.2.3"
    env = settings.env
    disk_namespace = settings.namespace
    
    # disk mounts
    NFS_ROOT_PATH = settings.NFS_ROOT_PATH
    VRE_ROOT_PATH = settings.VRE_ROOT_PATH
    ROOT_PATH = settings.ROOT_PATH

    # microservices
    NEO4J_SERVICE = settings.NEO4J_SERVICE + "/v1/neo4j/"
    NEO4J_SERVICE_V2 = settings.NEO4J_SERVICE + "/v2/neo4j/"
    ENTITYINFO_SERVICE = settings.ENTITYINFO_SERVICE + "/v1/"
    QUEUE_SERVICE = settings.QUEUE_SERVICE + "/v1/"
    DATA_OPS_GR = settings.DATA_OPS_GR + "/v1/"
    DATA_OPS_UTIL = settings.DATA_OPS_UTIL + "/v1/"
    DATA_OPS_UT_V2 = settings.DATA_OPS_UTIL + "/v2/"
    PROVENANCE_SERVICE = settings.PROVENANCE_SERVICE + "/v1/"
    UTILITY_SERVICE = settings.UTILITY_SERVICE + "/v1/"
    
    KEYCLOAK_MINIO_SECRET = settings.KEYCLOAK_MINIO_SECRET
    KEYCLOAK_VRE_SECRET = settings.KEYCLOAK_VRE_SECRET

    # minio
    MINIO_OPENID_CLIENT = settings.MINIO_OPENID_CLIENT
    MINIO_ENDPOINT = settings.MINIO_ENDPOINT
    MINIO_HTTPS = settings.MINIO_HTTPS
    KEYCLOAK_URL = settings.KEYCLOAK_URL
    MINIO_TEST_PASS = settings.MINIO_TEST_PASS
    MINIO_ACCESS_KEY = settings.MINIO_ACCESS_KEY
    MINIO_SECRET_KEY = settings.MINIO_SECRET_KEY

    MINIO_TMP_PATH = ROOT_PATH + '/tmp/'

    # temp path mount
    TEMP_BASE = ROOT_PATH + "/tmp/upload"

    # download secret
    DOWNLOAD_KEY = settings.DOWNLOAD_KEY
    DOWNLOAD_TOKEN_EXPIRE_AT = settings.DOWNLOAD_TOKEN_EXPIRE_AT
    # Redis Service
    REDIS_HOST = settings.REDIS_HOST
    REDIS_PORT = int(settings.REDIS_PORT)
    REDIS_DB = int(settings.REDIS_DB)
    REDIS_PASSWORD = settings.REDIS_PASSWORD
    