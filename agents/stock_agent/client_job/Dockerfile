FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt-get/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- FORCE CACHE INVALIDATION ---
# Updating this string guarantees Docker rebuilds from here down
ENV CODE_VERSION="v1.0.1"

COPY stock_agent_job.py .

RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

ENTRYPOINT ["python", "stock_agent_job.py"]