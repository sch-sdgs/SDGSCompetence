
FROM tiangolo/uwsgi-nginx-flask:python3.6

RUN apt-get update
RUN apt-get -y install apt-utils
RUN apt-get -y install default-jdk
RUN apt-get -y install ca-certificates
RUN apt-get -y install build-essential python-dev libssl-dev libffi-dev
RUN apt-get -y install python-mysqldb

RUN mkdir /uploads

COPY requirements.txt /tmp/

COPY . /tmp/SDGSCompetence/

RUN pip install -U pip
RUN pip install urllib3 pyasn1 ndg-httpsclient pyOpenSSL
RUN pip install -r /tmp/requirements.txt --upgrade

COPY ./app /app

WORKDIR /tmp/SDGSCompetence

RUN python setup.py install

WORKDIR /app

COPY /app/competencedb.conf /etc/nginx/conf.d/competencedb.conf

ENV MESSAGE "SDGSCompetence is running..."



