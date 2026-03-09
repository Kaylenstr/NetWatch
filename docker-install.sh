#!/bin/bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  NetWatch — Docker installer
#  Usage: curl -fsSL https://raw.githubusercontent.com/Kaylenstr/NetWatch/main/docker-install.sh | bash
#  With custom image:
#    NETWATCH_IMAGE=kaystr/netwatch curl -fsSL ... | bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
set -e

IMAGE="${NETWATCH_IMAGE:-}"
DIR="/opt/netwatch"

echo ""
echo "  NetWatch — Docker Installer"
echo ""

# ── Docker check ─────────────────────────────────
if ! command -v docker &>/dev/null; then
    echo "✗  Docker not found. Install Docker first:"
    echo "   curl -fsSL https://get.docker.com | bash"
    exit 1
fi
echo "✓  Docker found: $(docker --version | cut -d' ' -f3 | tr -d ',')"

# ── Directory + data (servers.json + .env persistent across updates) ─
mkdir -p "$DIR/data"

if [ ! -f "$DIR/data/servers.json" ]; then
  if [ -f "$DIR/servers.json" ]; then
    cp "$DIR/servers.json" "$DIR/data/servers.json"
    echo "✓  Migrated servers.json to $DIR/data/"
  else
cat > "$DIR/data/servers.json" << 'SERVERS_END'
{
  "connections": [["gateway", "storage"], ["gateway", "proxy"]],
  "servers": [
    {"name": "gateway", "host": "192.0.2.1", "location": "Example", "lat": 37.75, "lon": -122.42, "role": "Gateway"},
    {"name": "storage", "host": "192.0.2.2", "location": "Example", "lat": 37.80, "lon": -122.40, "role": "Storage"},
    {"name": "proxy", "host": "192.0.2.3", "location": "Example", "lat": 37.70, "lon": -122.38, "role": "Proxy"}
  ]
}
SERVERS_END
    echo "✓  Created default servers.json in $DIR/data/"
  fi
else
    echo "✓  Existing data preserved ($DIR/data/)"
fi

# ── Container start ──────────────────────────────
if docker ps -a --format '{{.Names}}' | grep -q '^netwatch$'; then
    echo "→  Removing existing container..."
    docker rm -f netwatch
fi

if [ -n "$IMAGE" ]; then
    echo "→  Pulling image: $IMAGE"
    docker pull "$IMAGE"
    RUN_IMAGE="$IMAGE"
else
    echo "✗  No image specified. Set NETWATCH_IMAGE:"
    echo "   NETWATCH_IMAGE=kaystr/netwatch curl -fsSL ... | bash"
    exit 1
fi

echo "→  Starting container..."
docker run -d \
    --name netwatch \
    --restart unless-stopped \
    -p 5000:5000 \
    --cap-add NET_RAW \
    -v "$DIR/data:/app/data" \
    "$RUN_IMAGE"

# ── Done ─────────────────────────────────────────
IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅  NetWatch is running!"
echo ""
echo "  Dashboard:  http://$IP:5000"
echo ""
echo "  Manage:"
echo "    docker logs -f netwatch"
echo "    docker restart netwatch"
echo "    docker rm -f netwatch"
echo ""
echo "  Edit config (persists across updates):"
echo "    nano $DIR/data/servers.json"
echo "    docker restart netwatch"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
