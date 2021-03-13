import os


class ConfigClass(object):
    env = os.environ.get('env')

    version = "0.1.1"

    # microservices
    NEO4J_SERVICE = "http://neo4j.utility:5062/v1/neo4j/"
    NEO4J_HOST = "http://neo4j.utility:5062"
    FILEINFO_HOST = "http://entityinfo.utility:5066"
    METADATA_API = "http://cataloguing.utility:5064"
    SEND_MESSAGE_URL = "http://queue-producer.greenroom:6060/v1/send_message"
    DATA_OPS_GR = "http://dataops-gr.greenroom:5063"
    # BFF_PORTAL = "http://10.3.7.226:5060"
    BFF_PORTAL = "http://bff.utility:5060"
    DATA_OPS_UTIL = "http://dataops-ut.utility:5063"
    UTILITY_SERVICE = "http://common.utility:5062"
    PROVENANCE_SERVICE = "http://provenance.utility:5077"

    # disk mounts
    ROOT_PATH = {
        "vre": "/vre-data",
        "greenroom": "/data/vre-storage"
    }.get(os.environ.get('namespace'), "./test_project")

    # temp path mount
    TEMP_BASE = ROOT_PATH + "/tmp/upload"

    # download secret
    DOWNLOAD_KEY = "indoc101"
    DOWNLOAD_TOKEN_EXPIRE_AT = 5

    # Redis Service
    # REDIS_HOST = "10.3.7.233"
    REDIS_HOST = "redis-master.utility"
    REDIS_PORT = 6379
    REDIS_DB = 0
    REDIS_PASSWORD = {
        'staging': '8EH6QmEYJN',
        'charite': 'o2x7vGQx6m'
    }.get(env, "5wCCMMC1Lk")

# trigger CICD
