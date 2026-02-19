#!/bin/sh
# Copy default config to persistent volume if not present
if [ ! -f /app/data/servers.json ]; then
  cp /app/servers.json.default /app/data/servers.json
  echo "  Initialized /app/data/servers.json from default config"
fi
exec "$@"
