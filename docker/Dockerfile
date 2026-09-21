FROM python:3.12-slim

RUN apt-get update \
    && apt-get install --no-install-recommends -y bash git patch \
    && python -m pip install --no-cache-dir pytest==8.4.2 \
    && rm -rf /var/lib/apt/lists/*

ENV HOME=/tmp \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /workspace
