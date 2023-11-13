FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    net-tools \
    iputils-ping \
    iproute2 \
    curl 

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /app

COPY . /app

RUN pip install --upgrade pip
RUN pip install -r requirements.txt