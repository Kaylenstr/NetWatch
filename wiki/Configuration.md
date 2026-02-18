# Configuration

## servers.json

Located in the project root. Format:

```json
{
  "connections": [],
  "servers": [
    {
      "name": "gateway",
      "host": "192.168.1.1",
      "location": "Amsterdam, NL",
      "lat": 52.37,
      "lon": 4.89,
      "role": "Gateway"
    }
  ]
}
```

| Field     | Required | Description                          |
|----------|----------|--------------------------------------|
| name     | yes      | Unique display name                  |
| host     | yes      | IP or hostname to ping               |
| location | no       | Label shown in sidebar and popup     |
| lat      | no       | Latitude for map marker              |
| lon      | no       | Longitude for map marker             |
| role     | no       | Label (e.g. Gateway, Server)         |

Without `lat` and `lon`, a server will not appear on the map but will still show in the sidebar and charts.

## Web UI

Settings (gear icon) lets you add, edit and remove servers without touching the file. Changes are written to `servers.json` and applied immediately.
