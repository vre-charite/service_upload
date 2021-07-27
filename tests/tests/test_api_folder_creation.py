import unittest
from tests.prepare_test import SetupTest
from tests.logger import Logger
import shutil
from app.config import ConfigClass
import os


class TestFolderCreationAPI(unittest.TestCase):
    log = Logger(name='test_folder_creation_api.log')
    test = SetupTest(log)
    project_code = "test_folder_creation1"
    container = ""
    # folder_path = os.path.join(
    #     ConfigClass.ROOT_PATH, project_code)
    # # since we now remove the raw so the raw file path is same
    # # as folder path
    # raw_folder_path = os.path.join(
    #     ConfigClass.ROOT_PATH, project_code)

    
    # if not os.path.exists(raw_folder_path):
    #     # cls.log.info("Creating folder path if not exists")
    #     os.makedirs(raw_folder_path)
    # else:
    #     shutil.rmtree(raw_folder_path)
    #     os.makedirs(raw_folder_path)

    # if not os.path.exists(folder_path):
    #     # cls.log.info("Creating raw folder path if not exists")
    #     os.makedirs(folder_path)
    # else:
    #     shutil.rmtree(folder_path)
    #     os.makedirs(folder_path)

    # # also clean up 

    @classmethod
    def setUpClass(cls):
        cls.log = cls.test.log
        cls.app = cls.test.app
        cls.container = cls.test.create_project(cls.project_code)


    @classmethod
    def tearDownClass(cls):
        cls.log.info("\n")
        cls.log.info("START TEAR DOWN PROCESS")
        try:
            cls.test.delete_project(cls.container["id"])

            # if os.path.exists(cls.raw_folder_path): 
            #     shutil.rmtree(cls.raw_folder_path)
            # if os.path.exists(cls.folder_path): 
            #     shutil.rmtree(cls.folder_path)
            cls.log.info("Deleting folder path on tear down")
        except Exception as e:
            cls.log.error("Please manual delete node and entity")
            cls.log.error(e)
            raise e

    def test_01_create_new_folder_vre(self):
        folder_name = "test_vrecore3"
        payload = {
            "folder_name": folder_name,
            "zone": "vrecore",
            "project_code": self.project_code,
            "uploader": "admin",
            "tags": []
        }

        result = self.app.post("v1/folder", json=payload)
        res = result.json()
        self.log.info("test_01 response: {}".format(res))
        self.assertEqual(result.status_code, 200)
        self.assertEqual(res["result"]["name"], folder_name)
        self.log.info(res["result"]["id"])
        self.test.delete_folder_node(res["result"]["id"])
        # folder_full_path = os.path.join(self.raw_folder_path, folder_name)
        # os.remove(folder_full_path)

    def test_02_create_new_folder_greenroom(self):
        folder_name = "test_greenroom3"
        payload = {
            "folder_name": folder_name,
            "zone": "greenroom",
            "project_code": self.project_code,
            "uploader": "admin",
            "tags": []
        }
        result = self.app.post("v1/folder", json=payload)
        res = result.json()
        self.log.info("test_02 response: {}".format(res))
        self.assertEqual(result.status_code, 200)
        self.assertEqual(res["result"]["name"], folder_name)
        self.test.delete_folder_node(res["result"]["id"])
        # folder_full_path = os.path.join(self.raw_folder_path, "raw",folder_name)
        # folder_full_path = os.path.join(self.raw_folder_path, folder_name)
        # os.remove(folder_full_path)

    def test_03_create_sub_folder(self):
        folder_name = f"sub_folder03"
        payload = {
            "folder_name": folder_name,
            "zone": "greenroom",
            "project_code": self.project_code,
            "uploader": "admin",
            "tags": [],
            "destination_geid": self.container['global_entity_id']
        }
        result = self.app.post("v1/folder", json=payload)
        res = result.json()
        self.log.info("test_03 response: {}".format(res))
        self.log.info(result)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(res["result"]["name"], folder_name)
        self.test.delete_folder_node(res["result"]["id"])
        # folder_full_path = os.path.join(self.raw_folder_path, "raw", folder_name)
        # folder_full_path = os.path.join(self.raw_folder_path, folder_name)
        # os.remove(folder_full_path)

    def test_04_folder_already_exists(self):
        folder_name = "test_vrecore3"
        payload = {
            "folder_name": folder_name,
            "zone": "vrecore",
            "project_code": self.project_code,
            "uploader": "admin",
            "tags": []
        }
        temp = self.app.post("v1/folder", json=payload)
        result = self.app.post("v1/folder", json=payload)
        self.log.info(result)
        self.assertEqual(result.status_code, 409)
        res = result.json()
        self.assertEqual(res["error_msg"], "[Invalid File] File Name has already taken by other resources(file/folder)")

        # finally delete the folder
        self.test.delete_folder_node(temp.json()["result"]["id"])

