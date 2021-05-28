import os

# os.environ['env'] = 'test'

class ConfigClass(object):
    env = os.environ.get('env')

    version = "0.2.3"

    # microservices
    NEO4J_SERVICE = "http://neo4j.utility:5062/v1/neo4j/"
    NEO4J_SERVICE_V2  = "http://neo4j.utility:5062/v2/neo4j/"
    ENTITYINFO_SERVICE = "http://entityinfo.utility:5066/v1/"
    QUEUE_SERVICE = "http://queue-producer.greenroom:6060/v1/"
    DATA_OPS_GR = "http://dataops-gr.greenroom:5063/v1/"
    DATA_OPS_UTIL = "http://dataops-ut.utility:5063/v1/"
    PROVENANCE_SERVICE = "http://provenance.utility:5077/v1/"
    UTILITY_SERVICE = "http://common.utility:5062/v1/"

    if env == "test":
        NEO4J_SERVICE = "http://10.3.7.216:5062/v1/neo4j/"
        NEO4J_SERVICE_V2 = "http://10.3.7.216:5062/v2/neo4j/"
        ENTITYINFO_SERVICE = "http://10.3.7.228:5066/v1/"
        DATA_UTILITY_SERVICE = "http://10.3.7.239:5063/v1/"
        PROVENANCE_SERVICE = "http://10.3.7.202:5077/v1/"
        UTILITY_SERVICE = "http://10.3.7.222:5062/v1/"

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
