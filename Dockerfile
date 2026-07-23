FROM python:3.12-slim

WORKDIR /app

# cron is needed to run the fetch/dedup/digest schedule inside the container
RUN apt-get update \
    && apt-get install -y --no-install-recommends cron \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

# The repo's config/ folder ships as "factory defaults" baked into the image.
# The runtime /app/config (mounted from the host) starts empty on a fresh
# bundle — entrypoint.sh copies these defaults in on first run only.
COPY config/ ./defaults/

COPY crontab /etc/cron.d/news-digest
RUN chmod 0644 /etc/cron.d/news-digest && crontab /etc/cron.d/news-digest

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

RUN mkdir -p /app/data /app/config

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["cron", "-f"]
