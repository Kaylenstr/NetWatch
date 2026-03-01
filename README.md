# NetWatch

Modern network monitoring dashboard. Pings servers and displays latency/jitter on maps and charts.
<img width="1916" height="991" alt="example" src="https://github.com/user-attachments/assets/bc49ff93-5d32-44c7-8195-d3d60f37a763" />


---

## Installation

### Step 1 — One-time: build and push image

On your own machine (where the source files are):

```bash
# Sign in to Docker Hub (free account: hub.docker.com)
docker login

# Build and push (replace `yourname` with your Docker Hub username)
bash publish.sh yourname
```

This builds the image and pushes it to `yourname/netwatch` on Docker Hub.

---

### Step 2 — On each server: one command

```bash
NETWATCH_IMAGE=yourname/netwatch curl -fsSL http://your-server/docker-install.sh | bash
```

That is all. Docker is required on the server:
```bash
# Install Docker (if not already installed):
curl -fsSL https://get.docker.com | bash
```

---

## Edit servers

```bash
nano /opt/netwatch/servers.json
docker restart netwatch
```

---

## Operations

```bash
docker logs -f netwatch        # live logs
docker restart netwatch        # restart
docker stats netwatch          # CPU/RAM usage
docker rm -f netwatch          # remove
```

---

## Run locally (without Docker)

```bash
pip install flask flask-cors
python backend/app.py
# -> open http://localhost:5000
```

---

## TV kiosk (Chromium)

```bash
chromium-browser --kiosk --noerrdialogs http://localhost:5000
```

---

## Quick Secure Setup

Minimal steps to secure access to the settings page.

### 1) Generate secrets

```bash
# bcrypt hash for admin password
python -c "import bcrypt; print(bcrypt.hashpw(b'your-strong-password', bcrypt.gensalt()).decode())"

# random SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"
```

### 2) Set environment variables

Create or update your `.env` (for example in `/opt/netwatch/.env`):

```dotenv
ADMIN_PASSWORD_HASH=<bcrypt-hash>
SECRET_KEY=<random-hex-64>
SESSION_LIFETIME_HOURS=8
SESSION_COOKIE_SECURE=false
FLASK_ENV=production
CORS_ORIGINS=http://localhost:5000,http://127.0.0.1:5000
TRUST_PROXY=false
```

Important:
- Keep `SESSION_COOKIE_SECURE=false` for HTTP/LAN installs.
- Set `SESSION_COOKIE_SECURE=true` only when serving NetWatch over HTTPS.
- Add your LAN URL to `CORS_ORIGINS` when needed, for example `http://192.168.1.231:5000`.
- If `ADMIN_PASSWORD_HASH` is empty on first boot, NetWatch starts in setup mode and lets you create credentials.

### 3) Rebuild/restart container

```bash
docker compose up -d --build
```

### 4) Quick smoke-check

```bash
# 1) Public metrics must mask host/IP details
curl -s http://localhost:5000/api/metrics

# 2) Config without login must return 401
curl -i http://localhost:5000/api/config
```

More security details: see `docs/SECURITY.md` and `docs/CONFIGURATION.md`.
