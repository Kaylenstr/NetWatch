# Installation

## Docker (recommended)

```bash
git clone <repo-url>
cd netwatch
docker compose up -d
```

Open http://localhost:5000

## Local (Python)

Requires Python 3.12+.

```bash
git clone <repo-url>
cd netwatch
pip install -r backend/requirements.txt
python backend/app.py
```

Open http://localhost:5000

## Linux: ping permissions

On Linux, the container needs `NET_RAW` and `NET_ADMIN` capabilities to run ping. These are included in the default `docker-compose.yml`. For bare-metal runs, the process needs to run as root or have `cap_net_raw` set.
