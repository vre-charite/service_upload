<!--
 Copyright 2022 Indoc Research
 
 Licensed under the EUPL, Version 1.2 or – as soon they
 will be approved by the European Commission - subsequent
 versions of the EUPL (the "Licence");
 You may not use this work except in compliance with the
 Licence.
 You may obtain a copy of the Licence at:
 
 https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12
 
 Unless required by applicable law or agreed to in
 writing, software distributed under the Licence is
 distributed on an "AS IS" basis,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
 express or implied.
 See the Licence for the specific language governing
 permissions and limitations under the Licence.
 
-->

# Upload Service
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg?style=for-the-badge)](https://www.gnu.org/licenses/agpl-3.0)
[![Python 3.7](https://img.shields.io/badge/python-3.7-green?style=for-the-badge)](https://www.python.org/)


This service is built for file data uploading purpose. It's built using the FastAPI python framework.

# About The Project

The upload service is one of the component for PILOT project. The main responsibility is to handle the file upload(especially large file). The main machanism for uploading is to chunk up the large file(>2MB). It has three main api for pre-uploading, uploading chunks and combining the chunks. After combining the chunks, the api will upload the file to [Minio](https://min.io/) as the Object Storage.

## Built With

 - [Minio](https://min.io/): The Object Storage to save the data

 - [Fastapi](https://fastapi.tiangolo.com): The async api framework for backend

 - [poetry](https://python-poetry.org/): python package management

# Getting Started


## Prerequisites

 1. The project is using poetry to handle the package. **Note here the poetry must install globally not in the anaconda virtual environment**

```
pip install poetry
```

 2. create the `.env` file from `.env.schema`

## Installation

 1. git clone the project:
 ```
git clone https://github.com/PilotDataPlatform/upload.git
 ```

 2. install the package:
 ```
poetry install
 ```

 3. run it locally:
 ```
poetry run python run.py
 ```

## Docker

To package up the service into docker pod, running following command:

```
docker build --build-arg pip_username=<pip_username> --build-arg pip_password=<pip_password>
```

## API Documents

REST API documentation in the form of Swagger/OpenAPI can be found here: [Api Document](https://pilotdataplatform.github.io/api-docs/)

## Helm Charts

Components of the Pilot Platform are available as helm charts for installation on Kubernetes: [Upload Service Helm Charts](https://github.com/PilotDataPlatform/helm-charts/tree/main/upload-service)
