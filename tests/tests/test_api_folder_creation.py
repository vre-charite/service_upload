# import unittest
# from tests.prepare_test import SetupTest
# from tests.logger import Logger
# import shutil
# from app.config import ConfigClass
# import os
# # # os.makedirs("./test_project/test_folder_creation1/raw")
# # shutil.rmtree("./test_project/test_folder_creation1/test_vrecore2")
# #
# # shutil.rmtree("./test_project/test_folder_creation1/raw/test_greenroom1")
#
#
# class TestFolderCreationAPI(unittest.TestCase):
#     log = Logger(name='test_folder_creation_api.log')
#     test = SetupTest(log)
#     project_code = "test_folder_creation1"
#     container = ""
#     raw_folder_path = os.path.join(
#         ConfigClass.ROOT_PATH, project_code)
#
#     @classmethod
#     def setUpClass(cls):
#         cls.log = cls.test.log
#         cls.app = cls.test.app
#         cls.container = cls.test.create_project(cls.project_code)
#
#     @classmethod
#     def tearDownClass(cls):
#         cls.log.info("\n")
#         cls.log.info("START TEAR DOWN PROCESS")
#         try:
#             cls.test.delete_project(cls.container["id"])
#         except Exception as e:
#             cls.log.error("Please manual delete node and entity")
#             cls.log.error(e)
#             raise e
#
#     def test_01_create_new_folder_vre(self):
#         folder_name = "test_vrecore2"
#         payload = {
#             "folder_name": folder_name,
#             "zone": "vrecore",
#             "project_code": self.project_code,
#             "uploader": "admin",
#             "tags": []
#         }
#
#         result = self.app.post("v1/folder", json=payload)
#         self.log.info(result)
#         self.assertEqual(result.status_code, 200)
#         res = result.json()
#         self.assertEqual(res["result"]["name"], folder_name)
#         self.test.delete_folder_node(res["result"]["id"])
#         folder_full_path = os.path.join(self.raw_folder_path,folder_name)
#         shutil.rmtree(folder_full_path)
#
#     def test_02_create_new_folder_greenroom(self):
#         folder_name = "test_greenroom1"
#         payload = {
#             "folder_name": folder_name,
#             "zone": "greenroom",
#             "project_code": self.project_code,
#             "uploader": "admin",
#             "tags": []
#         }
#         result = self.app.post("v1/folder", json=payload)
#         self.log.info(result)
#         self.assertEqual(result.status_code, 200)
#         res = result.json()
#         self.assertEqual(res["result"]["name"], folder_name)
#         self.test.delete_folder_node(res["result"]["id"])
#         folder_full_path = os.path.join(self.raw_folder_path, "raw",folder_name)
#         shutil.rmtree(folder_full_path)
#
#     def test_03_create_sub_folder(self):
#         folder_name = f"test_sub_folder:{self.container['global_entity_id']}"
#         payload = {
#             "folder_name": folder_name,
#             "zone": "greenroom",
#             "project_code": self.project_code,
#             "uploader": "admin",
#             "tags": [],
#             "destination_geid": self.container['global_entity_id']
#         }
#         result = self.app.post("v1/folder", json=payload)
#         self.log.info(result)
#         self.assertEqual(result.status_code, 200)
#         res = result.json()
#         self.assertEqual(res["result"]["name"], folder_name)
#         self.test.delete_folder_node(res["result"]["id"])
#
#     def test_04_folder_already_exists(self):
#         folder_name = "test_vrecore"
#         payload = {
#             "folder_name": folder_name,
#             "zone": "vrecore",
#             "project_code": self.project_code,
#             "uploader": "admin",
#             "tags": []
#         }
#         self.app.post("v1/folder", json=payload)
#         result = self.app.post("v1/folder", json=payload)
#         self.log.info(result)
#         self.assertEqual(result.status_code, 409)
#         res = result.json()
#         self.assertEqual(res["error_msg"], "[Invalid File] File Name has already taken by other resources(file/folder)")
#
