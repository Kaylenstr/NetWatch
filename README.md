# NetWatch

Network monitoring dashboard. Pings servers, displays latency and jitter on a map and in charts. Add or edit servers via the built-in settings UI.
<img width="1916" height="991" alt="example" src="https://github.com/user-attachments/assets/e793409a-5c55-42bf-a5fc-1445e9ae5cfb" />



## Requirements

- Docker and Docker Compose, or Python 3.12+

## Quick start

**Docker**

```bash
docker compose up -d
```

Open http://localhost:5000

**Local**

```bash
pip install -r backend/requirements.txt
python backend/app.py
```

Open http://localhost:5000

## Configuration

Servers are defined in `servers.json` or via Settings in the web UI. Each server needs:

- `name` – display name
- `host` – IP or hostname to ping
- `location` – optional label (e.g. "Amsterdam, NL")
- `lat`, `lon` – optional coordinates for map markers
- `role` – optional label (e.g. "Gateway")

See `wiki/` for detailed documentation.

## License

MIT
