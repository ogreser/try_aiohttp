FROM python:3.6.6-alpine

RUN mkdir /usr/src/app
WORKDIR /usr/src/app

COPY . .
RUN pip install -r requirements.txt
