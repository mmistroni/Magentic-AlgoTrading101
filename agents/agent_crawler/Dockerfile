FROM python:3.13-slim

# 1. Install system dependencies (needed for Playwright browsers)
# We include the fix for libasound2t64 here
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    libasound2t64 \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. Install UV and project dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir uv && \
    uv pip install --system --no-cache -r requirements.txt

# 3. Install Playwright Browsers (baked into the image)
# We use --with-deps to ensure the Linux libs are mapped
RUN playwright install chromium
RUN playwright install-deps chromium

# 4. Security: Run as non-root user
RUN adduser --disabled-password --gecos "" myuser && \
    chown -R myuser:myuser /app
USER myuser

COPY . .

# Cloud Run uses the PORT environment variable
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]