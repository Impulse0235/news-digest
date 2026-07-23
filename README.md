# news-digest

Self-hosted RSS -> AI digest + breaking news alerts. Runs as a portable Docker
bundle: pull a prebuilt image, mount a data folder, done.

## One-time setup (do this once, on GitHub)

1. Push this repo to GitHub.
2. The `.github/workflows/build.yml` workflow builds and publishes
   `ghcr.io/<you>/news-digest:latest` automatically on every push to `main`.
3. Go to your GitHub profile -> Packages -> `news-digest` -> Package settings,
   and set visibility to **Public**. This lets any device pull the image with
   a plain `docker pull`, no login needed. (Keep it private if you'd rather
   `docker login ghcr.io` on each device instead.)
4. Edit `docker-compose.yml` and replace `OWNER` with your GitHub username.

## Running the bundle (on the Pi, or anywhere with Docker)

```bash
cp .env.example .env      # fill in your Groq/OpenRouter/Brevo keys
docker compose up -d
```

First run with an empty `data/` folder will self-initialize the database and
copy in default `feeds.yaml`/`alerts.yaml`. After that, your edits to those
files are never overwritten.

Dashboard: http://<device-ip>:8080

## Moving the bundle

Everything that makes this *yours* is in this folder: `docker-compose.yml`,
`.env`, `config/`, `data/`. Copy the whole folder to a USB drive or another
machine, run `docker compose up -d` there — no rebuild, no re-entering keys.

## Status

- [x] Fetcher (`src/fetch.py`) — pulls new RSS items every 15 min
- [x] Database + self-init (`src/db.py`, `entrypoint.sh`)
- [x] Minimal dashboard stub (`src/web.py`)
- [ ] Dedup/clustering (`src/dedup.py`)
- [ ] AI ranking + summarizing (`src/summarize.py`)
- [ ] Digest email (`src/email_digest.py`)
- [ ] Keyword/breaking alert pass (`src/alert_check.py`)
- [ ] Full dashboard (feed/keyword editor, digest archive, run-now buttons)
