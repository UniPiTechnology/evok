FROM alpine:3.15

# This hack is widely applied to avoid python printing issues in docker containers.
# See: https://github.com/Docker-Hub-frolvlad/docker-alpine-python3/pull/13
ENV PYTHONUNBUFFERED=1

RUN apk add --no-cache python3 git
RUN python3 -m ensurepip
RUN rm -r /usr/lib/python*/ensurepip
RUN pip3 install --upgrade --break-system-packages pip setuptools
RUN rm -r /root/.cache

ENV LANG=C.UTF-8 LC_ALL=C.UTF-8

WORKDIR /
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN rm requirements.txt
RUN mkdir -p /evok
RUN mkdir -p /etc/evok/hw_definitions
RUN mkdir -p /var/lib/evok

COPY evok /evok
COPY files/etc /etc
COPY docker/entrypoint.sh /
RUN mv /etc/evok/config.yaml /evok.default
RUN sed -i 's/autogen: true/autogen: false/g' /evok.default
RUN chmod +x /entrypoint.sh

WORKDIR /
ENTRYPOINT /entrypoint.sh

#docker build . -t evok-test:devel
#docker run -it --rm --volume `pwd`/docker.evok.iris:/etc/evok.conf  evok-test:devel
