# NetWatch

Network monitoring dashboard. Pings servers, displays latency and jitter on a map and in charts. Add or edit servers via the built-in settings UI.
<img width="1916" height="991" alt="example" src="https://github.com/user-attachments/assets/e793409a-5c55-42bf-a5fc-1445e9ae5cfb" />

---

## Installatie

### Stap 1 — Eénmalig: image builden & pushen

Op je eigen machine (waar de bronbestanden staan):

```bash
# Inloggen op Docker Hub (gratis account: hub.docker.com)
docker login

# Build & push (vervang 'jouwnaam' door je Docker Hub gebruikersnaam)
bash publish.sh jouwnaam
```

Dit bouwt het image en pushed het naar `jouwnaam/netwatch` op Docker Hub.

---

### Stap 2 — Op elke server: één commando

```bash
NETWATCH_IMAGE=jouwnaam/netwatch curl -fsSL http://jouw-server/docker-install.sh | bash
```

Dat is alles. Docker is vereist op de server:
```bash
# Docker installeren (als nog niet aanwezig):
curl -fsSL https://get.docker.com | bash
```

---

## Servers aanpassen

```bash
nano /opt/netwatch/servers.json
docker restart netwatch
```

---

## Beheer

```bash
docker logs -f netwatch        # live logs
docker restart netwatch        # herstarten
docker stats netwatch          # CPU/RAM gebruik
docker rm -f netwatch          # verwijderen
```

---

## Lokaal draaien (zonder Docker)

```bash
pip install flask flask-cors
python backend/app.py
# → open http://localhost:5000
```

---

## TV kiosk (Chromium)

```bash
chromium-browser --kiosk --noerrdialogs http://localhost:5000
```

---

## Quick Secure Setup

Minimale stappen om de settings veilig af te schermen.

### 1) Genereer secrets

```bash
# bcrypt hash voor admin password
python -c "import bcrypt; print(bcrypt.hashpw(b'jouw-sterk-wachtwoord', bcrypt.gensalt()).decode())"

# random SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"
```

### 2) Zet env variabelen

Maak of update je `.env` (bijvoorbeeld in `/opt/netwatch/.env`):

```dotenv
ADMIN_PASSWORD_HASH=<bcrypt-hash>
SECRET_KEY=<random-hex-64>
SESSION_LIFETIME_HOURS=8
SESSION_COOKIE_SECURE=true
FLASK_ENV=production
CORS_ORIGINS=http://localhost:5000
TRUST_PROXY=false
```

Belangrijk:
- Zet `SESSION_COOKIE_SECURE=true` alleen uit als je lokaal zonder HTTPS test.
- De app start niet als `SECRET_KEY` of `ADMIN_PASSWORD_HASH` ontbreekt.

### 3) Herbouw/herstart container

```bash
docker compose up -d --build
```

### 4) Snelle smoke-check

```bash
# 1) Publieke metrics moeten host maskeren
curl -s http://localhost:5000/api/metrics

# 2) Config zonder login moet 401 geven
curl -i http://localhost:5000/api/config
```

Meer security details: zie `docs/SECURITY.md` en `docs/CONFIGURATION.md`.
