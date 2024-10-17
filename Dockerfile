# FROM python:3.8-slim-buster

# COPY . /app

# WORKDIR /app
# RUN pip install -r requirements.txt

# CMD ["python", "gourgandin.py"]

# DISTROLESS

# Build a virtualenv using the appropriate Debian release
# * Install python3-venv for the built-in Python3 venv module (not installed by default)
# * Install gcc libpython3-dev to compile C Python modules
# * In the virtualenv: Update pip setuputils and wheel to support building new packages
# FROM debian:11-slim AS build
# RUN apt-get update && \
#     apt-get install --no-install-suggests --no-install-recommends --yes python3-venv gcc libpython3-dev && \
#     python3 -m venv /venv && \
#     /venv/bin/pip install --upgrade pip setuptools wheel

# # Build the virtualenv as a separate step: Only re-execute this step when requirements.txt changes
# FROM build AS build-venv
# COPY requirements.txt /requirements.txt
# RUN /venv/bin/pip install --disable-pip-version-check -r /requirements.txt

# # Copy the virtualenv into a distroless image
# FROM gcr.io/distroless/python3-debian11
# COPY --from=build-venv /venv /venv
# COPY . /app
# WORKDIR /app
# ENTRYPOINT ["/venv/bin/python3", "barmanbot.py"]

# FROM python:3.10-slim-buster
FROM surnet/alpine-python-wkhtmltopdf:3.12.2-0.12.6-full
LABEL maintainer="sergei.leduc@gmail.com"
# LABEL image="https://hub.docker.com/r/..."
# LABEL source="https://github.com/..."
# RUN apt-get update && apt-get upgrade -y && apt-get autoremove -y
# RUN apt-get install -y ffmpeg git curl
# COPY requirements.txt ./

# RUN pip install -U pip
# RUN pip install -r requirements.txt

# WORKDIR /app
# COPY ./tts tts
# COPY ./libs libs
# COPY ./assets assets
# COPY ./utils utils
# COPY ./config config
# COPY ./models models
# COPY ./cogs cogs
# COPY  __main__.py LICENSE ./

# ENV DISCORD_BOT_HOST 0.0.0.0
# ENV DISCORD_BOT_PORT 8000
# HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 CMD curl -f http://localhost:8000/live || exit 1

COPY . /app

WORKDIR /app
RUN pip install -r requirements.txt

# CMD ["python", "barmanbot.py"]

ENTRYPOINT ["python", "gourgandin.py"]
