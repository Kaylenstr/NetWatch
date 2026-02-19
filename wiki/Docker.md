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

Server configuration is automatically persisted via a Docker named volume (`netwatch-data`).

On first start, the default `servers.json` is copied to the volume. Changes made via the Settings UI are saved to the volume and survive container rebuilds.

To reset to default configuration:

```bash
docker compose down -v
docker compose up -d
```

The `-v` flag removes the data volume, so the next start copies the default config again.
