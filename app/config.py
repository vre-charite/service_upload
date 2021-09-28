import os

import requests
from requests.models import HTTPError


srv_namespace = "service_upload"
CONFIG_CENTER = "http://10.3.7.222:5062" \
    if os.environ.get('env', "test") == "test" \
    else "http://common.utility:5062"


def vault_factory() -> dict:
    url = CONFIG_CENTER + \
          "/v1/utility/config/{}".format(srv_namespace)
    config_center_respon = requests.get(url)
    if config_center_respon.status_code != 200:
        raise HTTPError(config_center_respon.text)
    return config_center_respon.json()['result']


class ConfigClass(object):
    vault = vault_factory()
    env = os.environ.get('env')
    disk_namespace = os.environ.get('namespace')
    version = "0.2.3"

    # disk mounts
    NFS_ROOT_PATH = "./"
    VRE_ROOT_PATH = "/vre-data"
    ROOT_PATH = {
        "vre": "/vre-data"
    }.get(os.environ.get('namespace'), "/data/vre-storage")

    # microservices
    NEO4J_SERVICE = vault['NEO4J_SERVICE'] + "/v1/neo4j/"
    NEO4J_SERVICE_V2 = vault['NEO4J_SERVICE'] + "/v2/neo4j/"
    ENTITYINFO_SERVICE = vault['ENTITYINFO_SERVICE'] + "/v1/"
    QUEUE_SERVICE = vault['QUEUE_SERVICE'] + "/v1/"
    DATA_OPS_GR = vault['DATA_OPS_GR'] + "/v1/"
    DATA_OPS_UTIL = vault['DATA_OPS_UTIL'] + "/v1/"
    PROVENANCE_SERVICE = vault['PROVENANCE_SERVICE'] + "/v1/"
    UTILITY_SERVICE = vault['UTILITY_SERVICE'] + "/v1/"

    KEYCLOAK_VRE_SECRET = vault['KEYCLOAK_VRE_SECRET']

    # minio
    MINIO_OPENID_CLIENT = vault['MINIO_OPENID_CLIENT']
    MINIO_ENDPOINT = vault['MINIO_ENDPOINT']
    MINIO_HTTPS = False
    KEYCLOAK_URL = vault['KEYCLOAK_URL']
    MINIO_TEST_PASS = vault['MINIO_TEST_PASS']
    MINIO_ACCESS_KEY = vault['MINIO_ACCESS_KEY']
    MINIO_SECRET_KEY = vault['MINIO_SECRET_KEY']

    MINIO_TMP_PATH = ROOT_PATH + '/tmp/'

    # temp path mount
    TEMP_BASE = ROOT_PATH + "/tmp/upload"

    # download secret
    DOWNLOAD_KEY = "indoc101"
    DOWNLOAD_TOKEN_EXPIRE_AT = 5
    # Redis Service
    REDIS_HOST = vault['REDIS_HOST']
    REDIS_PORT = int(vault['REDIS_PORT'])
    REDIS_DB = int(vault['REDIS_DB'])
    REDIS_PASSWORD = vault['REDIS_PASSWORD']

