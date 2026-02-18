# Docker

## Run with Docker Compose

```bash
docker compose up -d
```

Port 5000 is exposed. The dashboard runs at http://localhost:5000

## Build manually

```bash
docker build -t netwatch .
docker run -p 5000:5000 netwatch
```

## Push to Docker Hub

```bash
docker build -t yourusername/netwatch:latest .
docker push yourusername/netwatch:latest
```

Others can run:

```bash
docker run -p 5000:5000 yourusername/netwatch:latest
```

## Persisting servers.json

By default, `servers.json` lives inside the container. Changes made via the UI are lost when the container is recreated.

To persist:

1. Add a volume to `docker-compose.yml`:

```yaml
services:
  netwatch:
    volumes:
      - ./servers.json:/app/servers.json
```

2. Ensure `servers.json` exists on the host before starting.

Note: On Windows with Docker Desktop, volume paths can sometimes cause issues. If the container fails to start, remove the volume and use the built-in config.
