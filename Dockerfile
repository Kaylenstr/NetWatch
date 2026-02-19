FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends iputils-ping && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app.py .
COPY frontend/ ./frontend/
COPY servers.json ./servers.json.default
COPY entrypoint.sh .

RUN chmod +x entrypoint.sh && \
    mkdir -p /app/data && \
    useradd -m -s /bin/false netwatch && \
    chown -R netwatch:netwatch /app

USER netwatch

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/api/health')"

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "app.py"]
