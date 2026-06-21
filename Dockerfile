# HPL AI Dispatching & Routing Engine v3.0
FROM python:3.11-slim

WORKDIR /app

# Cài system dependencies cho ortools
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data && \
    echo "[]" > data/incident_log.json || true

EXPOSE 8000

ENV PYTHONUNBUFFERED=1 \
    FLASK_ENV=production

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120", "--access-logfile", "-"]
