FROM 10.32.42.225:5000/python:3.7-buster
USER root
WORKDIR /usr/src/app

RUN http_proxy="http://proxy.charite.de:8080/" apt-get update
RUN http_proxy="http://proxy.charite.de:8080/" apt-get install -y vim
RUN http_proxy="http://proxy.charite.de:8080/" apt-get install -y less
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt --proxy="http://proxy.charite.de:8080/"
COPY . .
RUN chmod +x gunicorn_starter.sh
CMD ["./gunicorn_starter.sh"]

