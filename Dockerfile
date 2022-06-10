FROM python:2.7
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8

WORKDIR /
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN rm requirements.txt
RUN mkdir -p /evok
COPY evok /evok
RUN mkdir -p /evok/tornadorpc_evok
COPY tornadorpc_evok /evok/tornadorpc_evok

RUN mkdir -p /etc//hw_definitions
COPY etc/hw_definitions /etc//hw_definitions

RUN mkdir -p /var/evok
COPY var/evok-alias.yaml /var/evok

WORKDIR /evok
CMD python evok.py

#docker build . -t evok-test:devel
#docker run -it --rm --volume `pwd`/docker.evok.iris:/etc/evok.conf  evok-test:devel
