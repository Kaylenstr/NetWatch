"""
NetWatch — Server Monitor Backend
Pings servers, computes latency & jitter, serves API and frontend.
Servers loaded from servers.json (auto-detect path).
"""

from flask import Flask, jsonify, send_from_directory, request, session
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import subprocess
import threading
import platform
import time
import re
import os
import json
import statistics
from datetime import datetime, timedelta
from functools import wraps
import secrets
import hmac
import random
import bcrypt

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_ENV_FILE = os.path.join(SCRIPT_DIR, "data", ".env")


def load_env_file(path):
    if not os.path.isfile(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if key:
                    os.environ[key] = value
    except Exception as e:
        print(f"  Could not load env file {path}: {e}")


# Load persisted setup env (Docker volume) before reading auth config.
load_env_file(DATA_ENV_FILE)


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
        os.path.join(SCRIPT_DIR,   "data", "servers.json"),
        os.path.join(PROJECT_ROOT, "data", "servers.json"),
        os.path.join(SCRIPT_DIR,   "servers.json"),
        os.path.join(PROJECT_ROOT, "servers.json"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return candidates[0]

SERVERS_FILE = find_servers_file()


def resolve_env_file():
    project_candidate = os.path.join(PROJECT_ROOT, ".env")
    script_candidate = os.path.join(SCRIPT_DIR, ".env")
    data_candidate = DATA_ENV_FILE

    for candidate in (data_candidate, script_candidate, project_candidate):
        if os.path.isfile(candidate):
            return candidate

    def can_create(candidate):
        parent = os.path.dirname(candidate) or "."
        return os.path.isdir(parent) and os.access(parent, os.W_OK) and not os.path.isdir(candidate)

    for candidate in (data_candidate, script_candidate, project_candidate):
        if can_create(candidate):
            return candidate

    return data_candidate


ENV_FILE = resolve_env_file()

app = Flask(__name__, static_folder=None)

SETUP_REQUIRED = not bool(os.getenv("ADMIN_PASSWORD_HASH"))
_secret_key = os.getenv("SECRET_KEY", "")
if len(_secret_key) < 32 and not SETUP_REQUIRED:
    raise RuntimeError("SECRET_KEY must be set and contain at least 32 characters")
if len(_secret_key) < 32 and SETUP_REQUIRED:
    _secret_key = secrets.token_hex(32)

ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "")

_session_hours = int(os.getenv("SESSION_LIFETIME_HOURS", "8"))
_inactivity_minutes = int(os.getenv("INACTIVITY_TIMEOUT_MINUTES", "15"))
_inactivity_seconds = max(60, _inactivity_minutes * 60)
_session_secure_default = "true" if os.getenv("FLASK_ENV", "production") == "production" else "false"
_session_secure = os.getenv("SESSION_COOKIE_SECURE", _session_secure_default).lower() == "true"

app.config.update(
    SECRET_KEY=_secret_key,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Strict",
    SESSION_COOKIE_SECURE=_session_secure,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=_session_hours),
)

# CORS: restrict origins (same-origin + localhost by default; override via CORS_ORIGINS env)
_cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5000,http://127.0.0.1:5000")
CORS(
    app,
    origins=[o.strip() for o in _cors_origins.split(",") if o.strip()],
    supports_credentials=True,
)

limiter = Limiter(app=app, key_func=get_remote_address, default_limits=["200 per minute"])


class RateLimiter:
    def __init__(self, max_attempts=5, window_seconds=900):
        self.attempts = {}
        self.lock = threading.Lock()
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds

    def is_allowed(self, ip):
        with self.lock:
            now = time.time()
            recent = [t for t in self.attempts.get(ip, []) if now - t < self.window_seconds]
            if len(recent) >= self.max_attempts:
                self.attempts[ip] = recent
                return False
            recent.append(now)
            self.attempts[ip] = recent
            return True

    def retry_after_seconds(self, ip):
        with self.lock:
            now = time.time()
            recent = [t for t in self.attempts.get(ip, []) if now - t < self.window_seconds]
            if len(recent) < self.max_attempts:
                return 0
            oldest = min(recent)
            return max(1, int(self.window_seconds - (now - oldest)))


login_rate_limiter = RateLimiter(max_attempts=5, window_seconds=900)


def upsert_env_values(file_path, updates):
    if os.path.isdir(file_path):
        raise OSError(f"Env path points to directory: {file_path}")
    existing = {}
    lines = []
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            existing[key.strip()] = value.strip()

    existing.update(updates)

    handled = set()
    output = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in updates:
                output.append(f"{key}={existing[key]}\n")
                handled.add(key)
                continue
        output.append(line)

    for key in updates:
        if key not in handled:
            output.append(f"{key}={existing[key]}\n")

    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(output)

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

# Host validation: alleen geldige hostnames/IPs (geen spaties, newlines, shell chars)
HOST_PATTERN = re.compile(r"^[a-zA-Z0-9.\-]{1,253}$")


def validate_host(host):
    if not host or not isinstance(host, str):
        return False
    host = host.strip()
    return bool(host and HOST_PATTERN.match(host))


def get_client_ip():
    # Only trust forwarded headers when explicitly enabled behind a trusted proxy.
    if os.getenv("TRUST_PROXY", "false").lower() == "true":
        forwarded = request.headers.get("X-Forwarded-For", "").strip()
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"


def security_log(event_name):
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    ip = get_client_ip()
    ua = (request.headers.get("User-Agent", "") or "").strip()
    print(f"[SECURITY] {ts} | {event_name} | ip={ip} | ua={ua}")


def is_authenticated():
    if not (session.get("authenticated") and session.get("session_id")):
        return False
    last_activity = session.get("last_activity")
    now = int(time.time())
    if isinstance(last_activity, int) and now - last_activity > _inactivity_seconds:
        session.clear()
        return False
    return True


def touch_session_activity():
    session["last_activity"] = int(time.time())


def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_authenticated():
            return jsonify({"error": "Unauthorized"}), 401
        touch_session_activity()
        return f(*args, **kwargs)
    return decorated


def ensure_csrf_token():
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_hex(32)
        session["csrf_token"] = token
    return token


def csrf_is_valid():
    header_token = request.headers.get("X-CSRF-Token", "")
    session_token = session.get("csrf_token", "")
    return bool(header_token and session_token and hmac.compare_digest(header_token, session_token))


def mask_host(host):
    if not host:
        return "••••••••"
    if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", host):
        return "••••••••"
    if ":" in host:
        return "••••:••••:••••"
    return "••••••••"


def sanitize_public_server(cfg):
    return {
        "lat": None,
        "lon": None,
        "location": "",
        "host": "••••••••",
        "role": cfg.get("role", ""),
    }


def sanitize_public_metric(metric_row, cfg):
    return {
        **metric_row,
        "lat": None,
        "lon": None,
        "location": "",
        "host": mask_host(cfg.get("host", "")),
        "role": cfg.get("role", ""),
    }


metrics = {}
history = {}
lock    = threading.Lock()

for name in SERVERS:
    metrics[name] = {"online": False, "latency_ms": None, "jitter_ms": None, "last_checked": None}
    history[name] = {"timestamps": [], "latency": [], "jitter": []}

def ping_server(host, count=PING_COUNT):
    if not validate_host(host):
        return False, None, None
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
    authenticated = is_authenticated()
    with lock:
        result = {}
        for name, cfg in SERVERS.items():
            full_row = {
                **metrics[name],
                "lat": cfg.get("lat"),
                "lon": cfg.get("lon"),
                "location": cfg.get("location", ""),
                "host": cfg.get("host", ""),
                "role": cfg.get("role", ""),
            }
            result[name] = full_row if authenticated else sanitize_public_metric(metrics[name], cfg)
    return jsonify(result)

@app.route("/api/history")
def get_history():
    with lock:
        return jsonify(history)

@app.route("/api/servers")
def get_servers():
    authenticated = is_authenticated()
    return jsonify({
        "servers": {
            name: (
                {k: cfg.get(k) for k in ("lat", "lon", "location", "host", "role")}
                if authenticated else sanitize_public_server(cfg)
            )
            for name, cfg in SERVERS.items()
        },
        "connections": CONNECTIONS,
    })

@app.route("/api/health")
def health():
    online = sum(1 for m in metrics.values() if m.get("online"))
    return jsonify({"status": "ok", "servers": len(SERVERS), "online": online})


@app.before_request
def setup_gate():
    if not SETUP_REQUIRED:
        return None
    if not request.path.startswith("/api/"):
        return None
    if request.path in ("/api/setup", "/api/setup/status"):
        return None
    return jsonify({"error": "Setup required", "setup_required": True}), 503


@app.route("/api/setup/status")
def setup_status():
    return jsonify({"setup_required": SETUP_REQUIRED})


@app.route("/api/setup", methods=["POST"])
def run_setup():
    global SETUP_REQUIRED, ADMIN_PASSWORD_HASH

    if not SETUP_REQUIRED:
        return jsonify({"error": "Not found"}), 404

    data = request.get_json(silent=True) or {}
    password = (data.get("password") or "").strip()
    confirm = (data.get("confirm") or "").strip()

    if not password:
        return jsonify({"error": "Password is required"}), 400
    if len(password) < 12:
        return jsonify({"error": "Password must be at least 12 characters"}), 400
    if password != confirm:
        return jsonify({"error": "Passwords do not match"}), 400

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")
    secret_key = os.getenv("SECRET_KEY", "").strip()
    if len(secret_key) < 32:
        secret_key = secrets.token_hex(32)

    try:
        upsert_env_values(ENV_FILE, {
            "ADMIN_PASSWORD_HASH": password_hash,
            "SECRET_KEY": secret_key,
            "FLASK_ENV": "production",
        })
    except Exception as e:
        print(f"  Setup write failed: {e}")
        return jsonify({"error": "Could not persist setup configuration"}), 500

    os.environ["ADMIN_PASSWORD_HASH"] = password_hash
    os.environ["SECRET_KEY"] = secret_key
    os.environ["FLASK_ENV"] = "production"
    ADMIN_PASSWORD_HASH = password_hash
    app.config["SECRET_KEY"] = secret_key
    SETUP_REQUIRED = False
    session.clear()
    return jsonify({"status": "ok"})

@app.route("/api/config", methods=["GET", "POST"])
@limiter.limit("10 per minute")
@auth_required
def api_config():
    if request.method == "GET":
        servers_list = [
            {"name": name, "host": cfg.get("host", ""), "location": cfg.get("location", ""),
             "lat": cfg.get("lat"), "lon": cfg.get("lon"), "role": cfg.get("role", "")}
            for name, cfg in SERVERS.items()
        ]
        return jsonify({"servers": servers_list, "connections": list(CONNECTIONS)})
    try:
        if not csrf_is_valid():
            return jsonify({"error": "CSRF token missing or invalid"}), 403
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
            if not validate_host(s.get("host", "")):
                return jsonify({"error": f"Invalid host for server '{s.get('name', '')}'"}), 400
        with open(SERVERS_FILE, "w", encoding="utf-8") as f:
            json.dump({"servers": servers, "connections": connections}, f, indent=2, ensure_ascii=False)
        reload_config()
        security_log("CONFIG_CHANGED")
        return jsonify({"status": "ok", "message": "Config saved"})
    except Exception as e:
        print(f"  Config save failed: {e}")
        return jsonify({"error": "Configuration save failed"}), 500


@app.route("/api/csrf-token")
def get_csrf_token():
    token = ensure_csrf_token()
    response = jsonify({"token": token})
    response.set_cookie(
        "csrf_token",
        token,
        httponly=False,
        samesite="Strict",
        secure=app.config["SESSION_COOKIE_SECURE"],
    )
    return response


@app.route("/api/login", methods=["POST"])
@limiter.limit("20 per minute")
def login():
    # Always add jitter before any auth checks to reduce timing side-channels.
    time.sleep(random.uniform(0.2, 0.4))

    ip = get_client_ip()
    if not login_rate_limiter.is_allowed(ip):
        security_log("LOGIN_RATE_LIMIT")
        response = jsonify({"error": "Too many attempts, try again later"})
        retry_after = login_rate_limiter.retry_after_seconds(ip)
        response.headers["Retry-After"] = str(retry_after)
        return response, 429

    if not csrf_is_valid():
        return jsonify({"error": "CSRF token missing or invalid"}), 403

    data = request.get_json(silent=True) or {}
    password = data.get("password", "")

    try:
        valid_password = bcrypt.checkpw(password.encode("utf-8"), ADMIN_PASSWORD_HASH.encode("utf-8"))
    except Exception:
        valid_password = False

    if not valid_password:
        security_log("LOGIN_FAILED")
        return jsonify({"error": "Invalid credentials"}), 401

    session.clear()
    session["authenticated"] = True
    session["session_id"] = secrets.token_hex(16)
    touch_session_activity()
    session.permanent = True
    ensure_csrf_token()
    security_log("LOGIN_SUCCESS")
    return jsonify({"status": "ok"})


@app.route("/api/auth/status")
def auth_status():
    if is_authenticated():
        touch_session_activity()
    return jsonify({"authenticated": is_authenticated()})


@app.route("/api/logout", methods=["POST"])
@auth_required
def logout():
    if not csrf_is_valid():
        return jsonify({"error": "CSRF token missing or invalid"}), 403
    session.clear()
    return jsonify({"status": "ok"})


@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    elif request.path in ("/", "/settings") or request.path.endswith(".html"):
        # Avoid stale inline JS/CSS being served from browser cache.
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://unpkg.com https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https://*.arcgisonline.com https://*.openstreetmap.org; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    )
    return response

if __name__ == "__main__":
    t = threading.Thread(target=monitor_loop, daemon=True)
    t.start()
    print("NetWatch running on port 5000")
    print("Open: http://localhost:5000")
    if SETUP_REQUIRED:
        print("First run detected. Open http://localhost:5000 to complete setup.")
    else:
        print("Auth enabled. Login required for settings.")
    app.run(host="0.0.0.0", port=5000, debug=False)
