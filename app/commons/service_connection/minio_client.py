# Copyright 2022 Indoc Research
# 
# Licensed under the EUPL, Version 1.2 or – as soon they
# will be approved by the European Commission - subsequent
# versions of the EUPL (the "Licence");
# You may not use this work except in compliance with the
# Licence.
# You may obtain a copy of the Licence at:
# 
# https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12
# 
# Unless required by applicable law or agreed to in
# writing, software distributed under the Licence is
# distributed on an "AS IS" basis,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied.
# See the Licence for the specific language governing
# permissions and limitations under the Licence.
# 

import httpx
from minio import Minio
from minio.credentials.providers import ClientGrantsProvider

from app.config import ConfigClass


class Minio_Client_:
    def __init__(self, access_token, refresh_token):
        # preset the tokens for refreshing
        self.access_token = access_token
        self.refresh_token = refresh_token

        # retrieve credential provide with tokens
        c = self.get_provider()

        self.client = Minio(ConfigClass.MINIO_ENDPOINT, credentials=c, secure=ConfigClass.MINIO_HTTPS)

        # add a sanity check for the token to see if the token
        # is expired
        self.client.list_buckets()

    # function helps to get new token/refresh the token
    def _get_jwt(self):
        # print("refresh token")
        # enable the token exchange with different azp
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        payload = {
            'grant_type': 'urn:ietf:params:oauth:grant-type:token-exchange',
            'subject_token': self.access_token.replace('Bearer ', ''),
            'subject_token_type': 'urn:ietf:params:oauth:token-type:access_token',
            'requested_token_type': 'urn:ietf:params:oauth:token-type:refresh_token',
            'client_id': 'minio',
            'client_secret': ConfigClass.KEYCLOAK_MINIO_SECRET,
        }

        # use http httpx to fetch from keycloak
        with httpx.Client() as client:
            result = client.post(ConfigClass.KEYCLOAK_URL, data=payload, headers=headers)
        if result.status_code != 200:
            raise Exception('Token refresh failed with ' + str(result.json()))

        self.access_token = result.json().get('access_token')
        self.refresh_token = result.json().get('refresh_token')

        jwt_object = result.json()
        # print(jwt_object)

        return jwt_object

    # use the function above to create a credential object in minio
    # it will use the jwt function to refresh token if token expired
    def get_provider(self):
        minio_http = ('https://' if ConfigClass.MINIO_HTTPS else 'http://') + ConfigClass.MINIO_ENDPOINT
        # print(minio_http)
        provider = ClientGrantsProvider(
            self._get_jwt,
            minio_http,
        )

        return provider


class Minio_Client:
    def __init__(self):

        # Temperary use the credential
        self.client = Minio(
            ConfigClass.MINIO_ENDPOINT,
            access_key=ConfigClass.MINIO_ACCESS_KEY,
            secret_key=ConfigClass.MINIO_SECRET_KEY,
            secure=ConfigClass.MINIO_HTTPS,
        )
