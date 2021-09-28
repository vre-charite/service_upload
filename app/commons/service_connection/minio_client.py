import requests
import xmltodict
from minio import Minio
import os
import time
import datetime
import jwt
from ...config import ConfigClass

from minio.commonconfig import REPLACE, CopySource

from minio.credentials.providers import ClientGrantsProvider

class Minio_Client_():
    def __init__(self, access_token, refresh_token):
        # preset the tokens for refreshing
        self.access_token = access_token
        self.refresh_token = refresh_token
        
        # retrieve credential provide with tokens
        c = self.get_provider()

        self.client = Minio(
            ConfigClass.MINIO_ENDPOINT, 
            credentials=c,
            secure=ConfigClass.MINIO_HTTPS)


    # function helps to get new token/refresh the token
    def _get_jwt(self):
        # print("refresh token")

        payload = {
            "grant_type" : "refresh_token",
            "refresh_token": self.refresh_token,
            # "client_id":ConfigClass.MINIO_OPENID_CLIENT,
        }

        # some note here since the upload api will be used by the vre cli
        # the keycloak clients are kind of different. the portal use `react-app`
        # the cli use the `kong` so we need to use the `azp` attribute in token
        # then we can refresh token to update the at
        at = self.access_token.replace("Bearer ", "") # remove the bearer key for decoding
        decode_at = jwt.decode(at, verify=False)
        payload.update({"client_id": decode_at.get("azp")})
        if decode_at.get("azp") == "kong":
            payload.update({"client_secret": ConfigClass.KEYCLOAK_VRE_SECRET})

        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        # use http request to fetch from keycloak
        result = requests.post(ConfigClass.KEYCLOAK_URL+"/vre/auth/realms/vre/protocol/openid-connect/token", data=payload, headers=headers)
        if result.status_code != 200:
            raise Exception("Token refresh failed with "+str(result.json()))

        self.access_token = result.json().get("access_token")
        self.refresh_token = result.json().get("refresh_token")

        jwt_object = result.json()
        # print(jwt_object)

        return jwt_object

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




class Minio_Client():

    def __init__(self):

        # Temperary use the credential
        self.client = Minio(
            ConfigClass.MINIO_ENDPOINT, 
            access_key=ConfigClass.MINIO_ACCESS_KEY,
            secret_key=ConfigClass.MINIO_SECRET_KEY,
            secure=ConfigClass.MINIO_HTTPS)
    
