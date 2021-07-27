import requests
from app.config import ConfigClass
from fastapi.testclient import TestClient
from app.resources.helpers import get_geid
from run import app


class SetupException(Exception):
    "Failed setup test"



class SetupTest:

    def __init__(self, log):
        self.log = log
        self.app = self.create_test_client()

    def create_test_client(self):
        client = TestClient(app)
        return client

    def create_project(self, code, discoverable='true'):
        self.log.info("\n")
        self.log.info("Preparing testing project".ljust(80, '-'))
        testing_api = ConfigClass.NEO4J_SERVICE + "nodes/Container"
        params = {"name": "UploadUnitTest",
                  "path": code,
                  "code": code,
                  "description": "Project created by unit test, will be deleted soon...",
                  "discoverable": discoverable,
                  "type": "Usecase",
                  "tags": ['test'],
                  "global_entity_id": get_geid()
                  }
        self.log.info(f"POST API: {testing_api}")
        self.log.info(f"POST params: {params}")
        try:
            res = requests.post(testing_api, json=params)
            self.log.info(f"RESPONSE PROJECT CREATION DATA: {res.text}")
            self.log.info(f"RESPONSE PROJECT CREATION STATUS: {res.status_code}")
            assert res.status_code == 200
            node = res.json()[0]
            return node
        except Exception as e:
            self.log.error(f"ERROR CREATING PROJECT: {e}")
            raise e

    def delete_project(self, node_id):
        self.log.info("\n")
        self.log.info("Preparing delete project".ljust(80, '-'))
        delete_api = ConfigClass.NEO4J_SERVICE + "nodes/Container/node/%s" % str(node_id)
        try:
            self.log.info(f"DELETE Project: {node_id}")
            delete_res = requests.delete(delete_api)
            self.log.info(f"DELETE STATUS: {delete_res.status_code}")
            self.log.info(f"DELETE RESPONSE: {delete_res.text}")
        except Exception as e:
            self.log.info(f"ERROR DELETING PROJECT: {e}")
            self.log.info(f"PLEASE DELETE THE PROJECT MANUALLY WITH ID: {node_id}")
            raise e

    def delete_folder_node(self, node_id):
        self.log.info("\n")
        self.log.info("Preparing delete folder node".ljust(80, '-'))
        delete_api = ConfigClass.NEO4J_SERVICE + "nodes/Folder/node/%s" % str(node_id)
        try:
            delete_res = requests.delete(delete_api)
            self.log.info(f"DELETE STATUS: {delete_res.status_code}")
            self.log.info(f"DELETE RESPONSE: {delete_res.text}")
        except Exception as e:
            self.log.info(f"ERROR DELETING FILE: {e}")
            self.log.info(f"PLEASE DELETE THE FILE MANUALLY WITH ID: {node_id}")
            raise e