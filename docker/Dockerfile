FROM alpine:3.15

# This hack is widely applied to avoid python printing issues in docker containers.
# See: https://github.com/Docker-Hub-frolvlad/docker-alpine-python3/pull/13
ENV PYTHONUNBUFFERED=1

RUN apk add --no-cache python2 && \
    python -m ensurepip && \
    rm -r /usr/lib/python*/ensurepip && \
    pip install --upgrade pip setuptools && \
    rm -r /root/.cache

ENV LANG=C.UTF-8 LC_ALL=C.UTF-8

WORKDIR /
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    rm requirements.txt && \
    mkdir -p /evok && \
    mkdir -p /etc/hw_definitions && \
    mkdir -p /var/evok

COPY evok /evok
COPY etc/hw_definitions /etc/hw_definitions
COPY var/evok-alias.yaml /var/evok

WORKDIR /evok
CMD python evok.py

#docker build . -t evok-test:devel
#docker run -it --rm --volume `pwd`/docker.evok.iris:/etc/evok.conf  evok-test:devel
