FROM python:3.12-slim

WORKDIR /app

# tzdata for correct local time; curl to fetch Supercronic below
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata curl \
    && rm -rf /var/lib/apt/lists/*

ENV TZ=Pacific/Auckland
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Supercronic — a cron replacement built for containers. Unlike traditional
# cron, it does NOT strip the environment before running jobs (so .env
# secrets and PATH are simply inherited, no workarounds needed), and it
# logs job output straight to stdout/stderr instead of trying to email it
# or write to syslog. This avoids an entire class of "works when I run it
# manually, silently fails on schedule" bugs that plain cron has in Docker.
ARG TARGETARCH
ENV SUPERCRONIC_VERSION=0.2.45
RUN case "${TARGETARCH}" in \
      amd64) SUPERCRONIC_SHA1SUM=e894b193bea75a5ee644e700c59e30eedc804cf7 ;; \
      arm64) SUPERCRONIC_SHA1SUM=20ce6dace414a64f0632f4092d6d3745db6085ad ;; \
      *) echo "Unsupported architecture: ${TARGETARCH}" >&2 && exit 1 ;; \
    esac \
    && curl -fsSLO "https://github.com/aptible/supercronic/releases/download/v${SUPERCRONIC_VERSION}/supercronic-linux-${TARGETARCH}" \
    && echo "${SUPERCRONIC_SHA1SUM}  supercronic-linux-${TARGETARCH}" | sha1sum -c - \
    && chmod +x "supercronic-linux-${TARGETARCH}" \
    && mv "supercronic-linux-${TARGETARCH}" /usr/local/bin/supercronic

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

COPY config/ ./defaults/

COPY crontab /app/crontab
RUN sed -i 's/\r$//' /app/crontab

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

RUN mkdir -p /app/data /app/config

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["supercronic", "/app/crontab"]