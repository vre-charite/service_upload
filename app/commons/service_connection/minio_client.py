import requests
import xmltodict
from minio import Minio
import os
import time
import datetime
from ...config import ConfigClass

from minio.credentials.providers import ClientGrantsProvider


class Minio_Client():

    def __init__(self):
        # retrieve credential provide with tokens
        # c = self.get_provider()

        # self.client = Minio(
        #     ConfigClass.MINIO_ENDPOINT, 
        #     credentials=c,
        #     secure=ConfigClass.MINIO_HTTPS)

        # Temperary use the credential
        self.client = Minio(
            ConfigClass.MINIO_ENDPOINT, 
            access_key=ConfigClass.MINIO_ACCESS_KEY,
            secret_key=ConfigClass.MINIO_SECRET_KEY,
            secure=ConfigClass.MINIO_HTTPS)


    # function helps to get new token/refresh the token
    def _get_jwt(self):
        username = "admin"
        password = ConfigClass.MINIO_TEST_PASS
        payload = {
            "grant_type":"password",
            "username":username,
            "password":password, 
            "client_id":ConfigClass.MINIO_OPENID_CLIENT,
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        # use http request to fetch from keycloak
        result = requests.post(ConfigClass.KEYCLOAK_URL+"/vre/auth/realms/vre/protocol/openid-connect/token", data=payload, headers=headers)
        keycloak_access_token = result.json().get("access_token")
        return result.json()

    # use the function above to create a credential object in minio
    # it will use the jwt function to refresh token if token expired
    def get_provider(self):
        minio_http = ("https://" if ConfigClass.MINIO_HTTPS else "http://") + ConfigClass.MINIO_ENDPOINT
        # print(minio_http)
        provider = ClientGrantsProvider(
            self._get_jwt,
            minio_http,
        )

        return provider