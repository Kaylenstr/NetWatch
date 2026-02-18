"""
NetWatch — Server Monitor Backend
Pings servers, computes latency & jitter, serves API and frontend.
Servers loaded from servers.json (auto-detect path).
"""

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import subprocess
import threading
import platform
import time
import re
import os
import json
import statistics
from datetime import datetime

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)


def find_frontend_dir():
    candidates = [
        os.path.join(SCRIPT_DIR,   "frontend"),
        os.path.join(PROJECT_ROOT, "frontend"),
    ]
    for path in candidates:
        if os.path.isdir(path):
            return path
    return candidates[0]

FRONTEND_DIR = find_frontend_dir()


def find_servers_file():
    candidates = [
        os.path.join(SCRIPT_DIR,   "servers.json"),
        os.path.join(PROJECT_ROOT, "servers.json"),
        os.path.join(os.getcwd(),  "servers.json"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return candidates[1]

SERVERS_FILE = find_servers_file()

app = Flask(__name__, static_folder=None)
CORS(app)

@app.route("/")
@app.route("/settings")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")

def load_config():
    try:
        with open(SERVERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        servers     = {s["name"]: s for s in data.get("servers", [])}
        connections = data.get("connections", [])
        print(f"  {len(servers)} server(s) loaded: {', '.join(servers.keys())}")
        if connections:
            print(f"  {len(connections)} connection(s): {connections}")
        return servers, connections
    except FileNotFoundError:
        print(f"  servers.json not found ({SERVERS_FILE})")
        return {}, []
    except Exception as e:
        print(f"  Error loading servers.json: {e}")
        return {}, []

SERVERS = {}
CONNECTIONS = []

def reload_config():
    global SERVERS, CONNECTIONS, metrics, history
    new_servers, new_connections = load_config()
    with lock:
        old_names = set(SERVERS.keys())
        new_names = set(new_servers.keys())
        SERVERS.clear()
        SERVERS.update(new_servers)
        CONNECTIONS.clear()
        CONNECTIONS.extend(new_connections)
        for name in new_names - old_names:
            metrics[name] = {"online": False, "latency_ms": None, "jitter_ms": None, "last_checked": None}
            history[name] = {"timestamps": [], "latency": [], "jitter": []}
        for name in old_names - new_names:
            metrics.pop(name, None)
            history.pop(name, None)
    print(f"  Config reloaded: {len(SERVERS)} servers, {len(CONNECTIONS)} connections")

SERVERS, CONNECTIONS = load_config()
PING_COUNT = 4
IS_WINDOWS = platform.system() == "Windows"

metrics = {}
history = {}
lock    = threading.Lock()

for name in SERVERS:
    metrics[name] = {"online": False, "latency_ms": None, "jitter_ms": None, "last_checked": None}
    history[name] = {"timestamps": [], "latency": [], "jitter": []}

def ping_server(host, count=PING_COUNT):
    try:
        if IS_WINDOWS:
            cmd = ["ping", "-n", str(count), "-w", "2000", host]
        else:
            cmd = ["ping", "-c", str(count), "-W", "2", host]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        output = result.stdout

        if IS_WINDOWS:
            times_raw = re.findall(r"time[=<](\d+)ms", output)
        else:
            times_raw = re.findall(r"time=(\d+\.?\d*)\s*ms", output)

        times = [float(t) for t in times_raw]
        if not times:
            return False, None, None

        avg    = statistics.mean(times)
        jitter = statistics.stdev(times) if len(times) > 1 else 0.0
        return True, round(avg, 2), round(jitter, 2)

    except Exception as e:
        print(f"  ping error ({host}): {e}")
        return False, None, None

def monitor_loop():
    while True:
        items = list(SERVERS.items())
        for name, cfg in items:
            online, latency, jitter = ping_server(cfg["host"])
            now = datetime.now().strftime("%H:%M")
            with lock:
                if name not in metrics:
                    metrics[name] = {"online": False, "latency_ms": None, "jitter_ms": None, "last_checked": None}
                if name not in history:
                    history[name] = {"timestamps": [], "latency": [], "jitter": []}
                metrics[name] = {
                    "online":       online,
                    "latency_ms":   latency,
                    "jitter_ms":    jitter,
                    "last_checked": now,
                }
                h = history[name]
                h["timestamps"].append(now)
                h["latency"].append(latency if latency is not None else 0)
                h["jitter"].append(jitter  if jitter  is not None else 0)
                if len(h["timestamps"]) > 60:
                    h["timestamps"].pop(0)
                    h["latency"].pop(0)
                    h["jitter"].pop(0)
        time.sleep(10)

@app.route("/api/metrics")
def get_metrics():
    with lock:
        result = {}
        for name, cfg in SERVERS.items():
            result[name] = {
                **metrics[name],
                "lat":      cfg.get("lat"),
                "lon":      cfg.get("lon"),
                "location": cfg.get("location", ""),
                "host":     cfg.get("host", ""),
                "role":     cfg.get("role", ""),
            }
    return jsonify(result)

@app.route("/api/history")
def get_history():
    with lock:
        return jsonify(history)

@app.route("/api/servers")
def get_servers():
    return jsonify({
        "servers": {
            name: {k: cfg.get(k) for k in ("lat", "lon", "location", "host", "role")}
            for name, cfg in SERVERS.items()
        },
        "connections": CONNECTIONS,
    })

@app.route("/api/health")
def health():
    online = sum(1 for m in metrics.values() if m.get("online"))
    return jsonify({"status": "ok", "servers": len(SERVERS), "online": online})

@app.route("/api/config", methods=["GET", "POST"])
def api_config():
    from flask import request
    if request.method == "GET":
        servers_list = [
            {"name": name, "host": cfg.get("host", ""), "location": cfg.get("location", ""),
             "lat": cfg.get("lat"), "lon": cfg.get("lon"), "role": cfg.get("role", "")}
            for name, cfg in SERVERS.items()
        ]
        return jsonify({"servers": servers_list, "connections": list(CONNECTIONS)})
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data"}), 400
        servers = data.get("servers", [])
        connections = data.get("connections", [])
        if not isinstance(servers, list) or not isinstance(connections, list):
            return jsonify({"error": "Invalid data"}), 400
        for s in servers:
            if not isinstance(s.get("name"), str) or not s.get("name").strip():
                return jsonify({"error": "Each server must have a name"}), 400
        with open(SERVERS_FILE, "w", encoding="utf-8") as f:
            json.dump({"servers": servers, "connections": connections}, f, indent=2, ensure_ascii=False)
        reload_config()
        return jsonify({"status": "ok", "message": "Config saved"})
    except Exception as e:
        print(f"  Config save failed: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    t = threading.Thread(target=monitor_loop, daemon=True)
    t.start()
    print("NetWatch running on port 5000")
    print("Open: http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
