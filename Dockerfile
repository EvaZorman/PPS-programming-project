FROM ubuntu:focal
ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /usr/src/app

COPY *.py ./
COPY requirements.txt ./

RUN apt-get update && \
    apt-get install -y  \
    python3 \
    pip

RUN which python3

RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install -r requirements.txt

CMD ["python3", "./main.py", "--run-preset"]
